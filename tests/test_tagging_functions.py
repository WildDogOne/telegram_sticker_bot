from unittest.mock import AsyncMock, MagicMock

from conftest import insert_sticker, insert_user
from functions.global_functions import c
from functions.tagging_functions import _merge_tag_lists, tag_sticker_background


def test_merge_tag_lists_dedupes_preserving_first_seen_order():
    wd_tags = ["1girl", "solo", "smile"]
    jtp_tags = ["solo", "canine", "smile"]

    assert _merge_tag_lists(wd_tags, jtp_tags) == "1girl solo smile canine"


def test_merge_tag_lists_handles_empty_lists():
    assert _merge_tag_lists([], ["cat"]) == "cat"
    assert _merge_tag_lists([], []) == ""


def make_bot():
    bot = MagicMock()
    file = MagicMock()
    file.download_to_drive = AsyncMock()
    bot.get_file = AsyncMock(return_value=file)
    return bot, file


async def test_tag_sticker_background_writes_clip_column(monkeypatch):
    insert_user(user_id=1, current_pack="default")
    insert_sticker(user_id=1, file_unique_id="unique-1", clip=None)
    monkeypatch.setattr(
        "functions.tagging_functions.generate_tags",
        MagicMock(return_value="cat animal"),
    )
    bot, file = make_bot()

    await tag_sticker_background(bot, 1, "default", "file-id-1", "unique-1")

    bot.get_file.assert_awaited_once_with("file-id-1")
    file.download_to_drive.assert_awaited_once()
    c.execute(
        "SELECT CLIP FROM stickers WHERE user_id = ? AND file_unique_id = ?",
        (1, "unique-1"),
    )
    assert c.fetchall() == [("cat animal",)]


async def test_tag_sticker_background_never_touches_keywords(monkeypatch):
    insert_user(user_id=1, current_pack="default")
    insert_sticker(user_id=1, file_unique_id="unique-1", keywords="my keywords", clip=None)
    monkeypatch.setattr(
        "functions.tagging_functions.generate_tags",
        MagicMock(return_value="dog animal"),
    )
    bot, _ = make_bot()

    await tag_sticker_background(bot, 1, "default", "file-id-1", "unique-1")

    c.execute(
        "SELECT keywords, CLIP FROM stickers WHERE user_id = ? AND file_unique_id = ?",
        (1, "unique-1"),
    )
    assert c.fetchall() == [("my keywords", "dog animal")]
