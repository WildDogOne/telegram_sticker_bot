import asyncio
import csv
import json
import os
import threading

# The server this runs on has no GPU - keep torch/onnxruntime off it explicitly rather
# than have them probe for CUDA and fail to find one.
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")

from functions.global_functions import c, conn, logger

DATA_DIR = "./data"

# Two independent taggers, merged into one CLIP string: WD-EVA02 is trained on Danbooru
# (anime) tags, JTP is trained on e621 (furry) tags - neither vocabulary covers the
# other, and stickers here are a mix of both styles. Replaces the old DeepDanbooru
# pipeline, which was Danbooru-only and badly out of date (2021). Background/rationale:
# "Anime-Furry Auto-Tagger Models" note in the Obsidian vault (Areas/ML/SD).
WD_REPO = "SmilingWolf/wd-eva02-large-tagger-v3"
WD_GENERAL_THRESHOLD = 0.35
WD_CHARACTER_THRESHOLD = 0.85
WD_GENERAL_CATEGORY = 0
WD_CHARACTER_CATEGORY = 4

JTP_REPO = "RedRocket/JointTaggerProject"
JTP_SUBFOLDER = "JTP_PILOT2"
JTP_CHECKPOINT = "JTP_PILOT2-e3-vit_so400m_patch14_siglip_384.safetensors"
JTP_TAGS_FILE = "tags.json"
JTP_MODEL_NAME = "vit_so400m_patch14_siglip_384.webli"
JTP_NUM_CLASSES = 9083
# RedRocket's own docs call 0.20 just "a starting point" (recall-oriented) - for search
# relevance we want precision instead, so this is tuned higher than their default to cut
# down the long tail of weak, generic detections that make every sticker's tag set look
# alike.
JTP_THRESHOLD = 0.4

# Tags that describe the *sticker's format* rather than its content - they show up on
# almost every image regardless of what's depicted, so they add zero search value and
# just dilute fuzzy matching against tags that actually distinguish one sticker from
# another. Applied to both models' output. Extend this if new noise tags turn up.
NOISE_TAGS = frozenset(
    {
        "simple_background",
        "white_background",
        "grey_background",
        "gray_background",
        "transparent_background",
        "digital_media_(artwork)",
        "telegram_sticker",
        "sticker",
        "watermark",
        "artist_name",
        "signature",
        "web_address",
        "patreon_username",
        "third-party_watermark",
    }
)

# Both models are loaded once per process and reused across stickers, guarded by a lock
# since multiple stickers can be tagged concurrently via run_in_executor's thread pool.
_model_lock = threading.Lock()
_wd_session = None
_wd_target_size = None
_wd_tags = None  # list of (name, category) rows from selected_tags.csv

_jtp_model = None
_jtp_transform = None
_jtp_tags = None  # tag name per model output index


def _ensure_wd_loaded():
    global _wd_session, _wd_target_size, _wd_tags
    if _wd_session is not None:
        return
    with _model_lock:
        if _wd_session is not None:
            return
        import onnxruntime as ort
        from huggingface_hub import hf_hub_download

        model_path = hf_hub_download(WD_REPO, "model.onnx")
        tags_path = hf_hub_download(WD_REPO, "selected_tags.csv")
        _wd_session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        _, height, _, _ = _wd_session.get_inputs()[0].shape
        _wd_target_size = height
        with open(tags_path, newline="", encoding="utf-8") as f:
            _wd_tags = [(row["name"], int(row["category"])) for row in csv.DictReader(f)]


def _wd_prepare_image(image):
    """Matches SmilingWolf/wd-tagger's prepare_image exactly: alpha-composite onto
    white, pad to square, resize, then RGB->BGR (the model was trained on BGR)."""
    import numpy as np
    from PIL import Image

    canvas = Image.new("RGBA", image.size, (255, 255, 255))
    canvas.alpha_composite(image.convert("RGBA"))
    image = canvas.convert("RGB")
    max_dim = max(image.size)
    padded = Image.new("RGB", (max_dim, max_dim), (255, 255, 255))
    padded.paste(image, ((max_dim - image.size[0]) // 2, (max_dim - image.size[1]) // 2))
    if max_dim != _wd_target_size:
        padded = padded.resize((_wd_target_size, _wd_target_size), Image.BICUBIC)
    array = np.asarray(padded, dtype=np.float32)[:, :, ::-1]
    return np.expand_dims(array, axis=0)


def _wd_infer(image) -> list:
    _ensure_wd_loaded()
    input_name = _wd_session.get_inputs()[0].name
    output_name = _wd_session.get_outputs()[0].name
    probs = _wd_session.run([output_name], {input_name: _wd_prepare_image(image)})[0][0]
    # Tag names keep their underscores (e.g. "simple_background") rather than becoming
    # spaces - this is just the canonical Danbooru/e621 tag form and easier to read back
    # from the DB. Note it does NOT change fuzzy-match behavior: thefuzz's own
    # preprocessing (utils.full_process) converts underscores to spaces before comparing
    # either way, so multi-word tags are tokenized into their component words for
    # matching purposes regardless of how they're joined here. Actual search-noise
    # control happens via NOISE_TAGS and the confidence thresholds below.
    tags = []
    for (name, category), prob in zip(_wd_tags, probs):
        if category == WD_GENERAL_CATEGORY and prob >= WD_GENERAL_THRESHOLD:
            tags.append(name)
        elif category == WD_CHARACTER_CATEGORY and prob >= WD_CHARACTER_THRESHOLD:
            tags.append(name)
    return tags


def _build_jtp_model():
    """Verbatim (Apache 2.0) from RedRocket/JointTaggerProject's JTP_PILOT2/inference_gradio.py,
    the model's own reference inference script - the custom head and transforms are specific
    to how this checkpoint was trained and aren't safe to approximate."""
    import timm
    import torch
    from torchvision import transforms
    from torchvision.transforms import InterpolationMode
    from torchvision.transforms import functional as TF

    class GatedHead(torch.nn.Module):
        def __init__(self, num_features, num_classes):
            super().__init__()
            self.num_classes = num_classes
            self.linear = torch.nn.Linear(num_features, num_classes * 2)
            self.act = torch.nn.Sigmoid()
            self.gate = torch.nn.Sigmoid()

        def forward(self, x):
            x = self.linear(x)
            return self.act(x[:, : self.num_classes]) * self.gate(x[:, self.num_classes :])

    class Fit(torch.nn.Module):
        def __init__(self, bounds, interpolation=InterpolationMode.LANCZOS, grow=True, pad=None):
            super().__init__()
            self.bounds = (bounds, bounds) if isinstance(bounds, int) else bounds
            self.interpolation = interpolation
            self.grow = grow
            self.pad = pad

        def forward(self, img):
            wimg, himg = img.size
            hbound, wbound = self.bounds
            hscale = hbound / himg
            wscale = wbound / wimg
            if not self.grow:
                hscale = min(hscale, 1.0)
                wscale = min(wscale, 1.0)
            scale = min(hscale, wscale)
            if scale == 1.0:
                return img
            hnew = min(round(himg * scale), hbound)
            wnew = min(round(wimg * scale), wbound)
            img = TF.resize(img, (hnew, wnew), self.interpolation)
            if self.pad is None:
                return img
            hpad = hbound - hnew
            wpad = wbound - wnew
            tpad = hpad // 2
            bpad = hpad - tpad
            lpad = wpad // 2
            rpad = wpad - lpad
            return TF.pad(img, (lpad, tpad, rpad, bpad), self.pad)

    class CompositeAlpha(torch.nn.Module):
        def __init__(self, background):
            super().__init__()
            background = (background, background, background) if isinstance(background, float) else background
            self.background = torch.tensor(background).unsqueeze(1).unsqueeze(2)

        def forward(self, img):
            if img.shape[-3] == 3:
                return img
            alpha = img[..., 3, None, :, :]
            img[..., :3, :, :] *= alpha
            background = self.background.expand(-1, img.shape[-2], img.shape[-1])
            img[..., :3, :, :] += (1.0 - alpha) * background
            return img[..., :3, :, :]

    model = timm.create_model(JTP_MODEL_NAME, pretrained=False, num_classes=JTP_NUM_CLASSES)
    model.head = GatedHead(min(model.head.weight.shape), JTP_NUM_CLASSES)

    transform = transforms.Compose(
        [
            Fit((384, 384)),
            transforms.ToTensor(),
            CompositeAlpha(0.5),
            transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5], inplace=True),
            transforms.CenterCrop((384, 384)),
        ]
    )
    return model, transform


def _ensure_jtp_loaded():
    global _jtp_model, _jtp_transform, _jtp_tags
    if _jtp_model is not None:
        return
    with _model_lock:
        if _jtp_model is not None:
            return
        from huggingface_hub import hf_hub_download
        from safetensors.torch import load_model

        model, transform = _build_jtp_model()
        checkpoint_path = hf_hub_download(JTP_REPO, JTP_CHECKPOINT, subfolder=JTP_SUBFOLDER)
        load_model(model, checkpoint_path)
        model.eval()

        tags_path = hf_hub_download(JTP_REPO, JTP_TAGS_FILE, subfolder=JTP_SUBFOLDER)
        with open(tags_path, encoding="utf-8") as f:
            tag_keys = list(json.load(f).keys())

        _jtp_model = model
        _jtp_transform = transform
        # Keep underscores - see the comment in _wd_infer for why this doesn't affect
        # fuzzy-match behavior, just readability/canonical form.
        _jtp_tags = tag_keys


def _jtp_infer(image) -> list:
    import torch

    _ensure_jtp_loaded()
    tensor = _jtp_transform(image.convert("RGBA")).unsqueeze(0)
    with torch.no_grad():
        probs = _jtp_model(tensor)[0]
    return [_jtp_tags[i] for i, prob in enumerate(probs.tolist()) if prob > JTP_THRESHOLD]


def _merge_tag_lists(*tag_lists) -> str:
    seen = set()
    merged = []
    for tags in tag_lists:
        for tag in tags:
            if tag not in seen and tag not in NOISE_TAGS:
                seen.add(tag)
                merged.append(tag)
    return " ".join(merged)


def generate_tags(webp_path: str) -> str:
    """Blocking - runs both taggers. Call via loop.run_in_executor, never directly on
    the event loop."""
    from PIL import Image

    try:
        image = Image.open(webp_path)
        return _merge_tag_lists(_wd_infer(image), _jtp_infer(image))
    finally:
        if os.path.exists(webp_path):
            os.remove(webp_path)


async def tag_sticker_background(bot, user_id, pack_id, file_id, file_unique_id):
    """Downloads the sticker, runs auto-tagging, and writes the result into the
    existing CLIP column - never touching the user-supplied `keywords`. Intended to
    be scheduled fire-and-forget (e.g. via Application.create_task) right after a
    new sticker is saved; any exception here propagates to the caller's task, so it
    reaches the bot's normal error_handler/send_message_to_admin path."""
    os.makedirs(DATA_DIR, exist_ok=True)
    webp_path = os.path.join(DATA_DIR, f"{file_unique_id}.webp")
    file = await bot.get_file(file_id)
    await file.download_to_drive(webp_path)

    loop = asyncio.get_running_loop()
    tags = await loop.run_in_executor(None, generate_tags, webp_path)

    c.execute(
        "UPDATE stickers SET CLIP = ? WHERE user_id = ? AND file_unique_id = ? AND pack_id = ?",
        (tags, user_id, file_unique_id, pack_id),
    )
    conn.commit()
    logger.debug(f"Auto-tagged sticker {file_unique_id} for user {user_id}: {tags!r}")
