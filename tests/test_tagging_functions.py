from unittest.mock import AsyncMock, MagicMock

from conftest import insert_sticker, insert_user, make_context, make_message_update
from functions.global_functions import c
from functions.tagging_functions import (
    _merge_tag_lists,
    retag,
    retag_stickers_background,
    tag_sticker_background,
)


def test_merge_tag_lists_dedupes_preserving_first_seen_order():
    wd_tags = ["1girl", "solo", "smile"]
    jtp_tags = ["solo", "canine", "smile"]

    assert _merge_tag_lists(wd_tags, jtp_tags) == "1girl solo smile canine"


def test_merge_tag_lists_handles_empty_lists():
    assert _merge_tag_lists([], ["cat"]) == "cat"
    assert _merge_tag_lists([], []) == ""


def test_merge_tag_lists_drops_format_noise_tags():
    wd_tags = ["1girl", "simple_background", "solo"]
    jtp_tags = ["telegram_sticker", "canine", "watermark"]

    assert _merge_tag_lists(wd_tags, jtp_tags) == "1girl solo canine"


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


# conftest's fake config sets owner_id=111111.
OWNER_ID = 111111


async def test_retag_rejects_non_admin():
    update = make_message_update(user_id=1, text="/retag")
    context = make_context()

    await retag(update, context)

    update.message.reply_text.assert_awaited_once_with(
        "This command is only available to the bot admin."
    )
    context.application.create_task.assert_not_called()


async def test_retag_admin_starts_background_task():
    insert_sticker(user_id=1, file_unique_id="unique-1")
    update = make_message_update(user_id=OWNER_ID, text="/retag")
    context = make_context()

    await retag(update, context)

    update.message.reply_text.assert_awaited_once_with(
        "Re-tagging 1 stickers in the background, I'll message you when done."
    )
    context.application.create_task.assert_called_once()


async def test_retag_reports_progress_instead_of_starting_second_run(monkeypatch):
    from functions.tagging_functions import _retag_state

    monkeypatch.setattr(
        "functions.tagging_functions.time.monotonic", lambda: 100.0
    )
    _retag_state.update(running=True, total=5, tagged=2, failed=1, started_at=70.0)
    update = make_message_update(user_id=OWNER_ID, text="/retag")
    context = make_context()

    await retag(update, context)

    update.message.reply_text.assert_awaited_once_with(
        "Re-tagging is already running: 3/5 processed (2 tagged, 1 failed), "
        "started 30s ago."
    )
    context.application.create_task.assert_not_called()


async def test_retag_stickers_background_retags_all_and_reports_summary(monkeypatch):
    insert_user(user_id=1, current_pack="default")
    insert_sticker(user_id=1, file_unique_id="u1", clip="old tag")
    insert_sticker(user_id=1, file_unique_id="u2", clip=None)
    monkeypatch.setattr(
        "functions.tagging_functions.generate_tags",
        MagicMock(return_value="new tag"),
    )
    bot, _ = make_bot()
    bot.send_message = AsyncMock()

    await retag_stickers_background(bot, chat_id=OWNER_ID)

    c.execute("SELECT file_unique_id, CLIP FROM stickers ORDER BY file_unique_id")
    assert c.fetchall() == [("u1", "new tag"), ("u2", "new tag")]
    bot.send_message.assert_awaited_once_with(
        chat_id=OWNER_ID, text="Re-tagging complete: 2 tagged, 0 failed, 2 total."
    )


async def test_retag_stickers_background_counts_failures_and_continues(monkeypatch):
    insert_user(user_id=1, current_pack="default")
    insert_sticker(user_id=1, file_unique_id="u1", clip=None)
    insert_sticker(user_id=1, file_unique_id="u2", clip=None)
    monkeypatch.setattr(
        "functions.tagging_functions.generate_tags",
        MagicMock(side_effect=[Exception("boom"), "new tag"]),
    )
    bot, _ = make_bot()
    bot.send_message = AsyncMock()

    await retag_stickers_background(bot, chat_id=OWNER_ID)

    c.execute("SELECT file_unique_id, CLIP FROM stickers ORDER BY file_unique_id")
    assert c.fetchall() == [("u1", None), ("u2", "new tag")]
    bot.send_message.assert_awaited_once_with(
        chat_id=OWNER_ID, text="Re-tagging complete: 1 tagged, 1 failed, 2 total."
    )
