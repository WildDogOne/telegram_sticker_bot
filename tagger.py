from telegram import Bot
from config.config import token, db
from functions.global_functions import logger
import sqlite3
from pprint import pprint
import os
import requests
import numpy as np
import deepdanbooru as dd
import tensorflow as tf
from PIL import Image
import asyncio



async def download_sticker(bot_token, file_id, filename):
    bot = Bot(bot_token)
    file = await bot.get_file(file_id)
    await file.download_to_drive(filename)

def get_stickers():
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute(
        "SELECT file_id, CLIP FROM stickers WHERE CLIP IS NULL",
    )
    results = c.fetchall()
    conn.close()
    stickers = []
    for x in results:
        stickers.append(x[0])
    print(results)
    return stickers




def download_model(model_url, model_zip):
    r = requests.get(model_url, allow_redirects=True)
    with open(model_zip, 'wb') as f:
        f.write(r.content)


def extract_model(model_zip, project):
    import zipfile

    with zipfile.ZipFile(model_zip, 'r') as zip_ref:
        zip_ref.extractall(project)


def prepare_image(input_image, model):
    #pil_image = Image.open(input_image)
    pil_image = Image.open(input_image).convert('RGB')  # Convert image to RGB

    width = model.input_shape[2]
    height = model.input_shape[1]
    image = np.array(pil_image)
    image = tf.image.resize(
        image,
        size=(height, width),
        method=tf.image.ResizeMethod.AREA,
        preserve_aspect_ratio=True,
    )
    image = image.numpy()  # EagerTensor to np.array
    image = dd.image.transform_and_pad_image(image, width, height)
    image = image / 255.0
    image_shape = image.shape
    image = image.reshape((1, image_shape[0], image_shape[1], image_shape[2]))
    return image


def evaluate_image(input_image: str = None, model_url: str = None, project: str = None, threshold: float = None):
    if model_url is None:
        model_url = "https://github.com/KichangKim/DeepDanbooru/releases/download/v3-20211112-sgd-e28/deepdanbooru-v3-20211112-sgd-e28.zip"
    if project is None:
        project = "./deepbooru"
    if threshold is None:
        threshold = 0.5
    model_zip = os.path.join(project, "model.zip")

    if not os.path.exists(project):
        os.makedirs(project)
    if not os.path.exists(model_zip):
        download_model(model_url, model_zip)
    if not os.path.exists(os.path.join(project, "project.json")):
        extract_model(model_zip, project)

    tags = dd.project.load_tags_from_project(project)
    model = dd.project.load_model_from_project(project, compile_model=False)

    image = prepare_image(input_image, model)
    y = model.predict(image)[0]

    result_dict = {}

    for i, tag in enumerate(tags):
        result_dict[tag] = y[i]

    result_tags_out = []
    result_tags = []
    rating = "s"

    for tag in tags:
        if result_dict[tag] >= threshold:
            if tag.startswith("rating:"):
                rating = tag
                continue
            result_tags_out.append(tag.replace('_', ' ').replace(':', ' '))
            result_tags.append({tag.replace('_', ' ').replace(':', ' '): result_dict[tag]})

    return result_tags_out, rating

def convert_webp_to_png(input_path, output_path):
    img = Image.open(input_path)
    img.save(output_path, 'PNG')

async def clipit():
    print("Function executed")
    stickers = get_stickers()
    pprint(stickers)
    for sticker in stickers:
        await download_sticker(token, sticker, f'./data/{sticker}.webp')

        #quit()

def main():
    # Your code here
    # Create a new event loop
    loop = asyncio.new_event_loop()

    # Set the event loop for the current thread
    asyncio.set_event_loop(loop)

    try:
        # Run the coroutine in the event loop
        loop.run_until_complete(clipit())
    finally:
        # Close the event loop
        loop.close()

    conn = sqlite3.connect(db)
    c = conn.cursor()
    stickers = get_stickers()
    for sticker in stickers:
        convert_webp_to_png(f'./data/{sticker}.webp', f'./data/{sticker}.png')
        tags, rating = evaluate_image(f'./data/{sticker}.png')
        print(tags, rating)
        CLIP = ' '.join(tags)
        c.execute(
            """
            Update stickers
            Set CLIP = ?
            Where file_id = ?
            """,
            (CLIP, sticker),
        )
        conn.commit()
    conn.close()


if __name__ == "__main__":
    main()


