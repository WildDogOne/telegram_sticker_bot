from unittest.mock import MagicMock

from telegram.ext import ConversationHandler

from conftest import (
    insert_sticker,
    insert_user,
    insert_user_pack,
    make_context,
    make_message_update,
    make_sticker,
)
from functions.global_functions import c
from functions.sticker_functions import deletesticker, keywords, sticker


async def test_sticker_new_sticker_asks_for_keywords():
    update = make_message_update(user_id=1, sticker=make_sticker())
    context = make_context()

    result = await sticker(update, context)

    assert result == 1  # KEYWORDS state
    assert context.user_data["sticker"][4] is False  # exists=False
    update.message.reply_text.assert_any_await(
        "What keywords do you want to attach to this sticker?"
    )


async def test_sticker_existing_sticker_shows_current_keywords():
    insert_user(user_id=1)
    insert_sticker(user_id=1, file_unique_id="unique-1", keywords="cat happy")
    update = make_message_update(
        user_id=1, sticker=make_sticker(file_unique_id="unique-1")
    )
    context = make_context()

    await sticker(update, context)

    assert context.user_data["sticker"][4] is True  # exists=True
    first_reply = update.message.reply_text.await_args_list[0].args[0]
    assert "cat happy" in first_reply


async def test_keywords_inserts_new_sticker():
    insert_user(user_id=1, current_pack="default")
    update = make_message_update(user_id=1, text="cat happy")
    context = make_context()
    context.user_data["sticker"] = (1, "file-id-1", "unique-1", "😀", False)

    result = await keywords(update, context)

    c.execute(
        "SELECT keywords, emojies FROM stickers WHERE user_id = ? AND file_unique_id = ?",
        (1, "unique-1"),
    )
    assert c.fetchall() == [("cat happy", "😀")]
    assert result == ConversationHandler.END


async def test_keywords_schedules_auto_tagging_for_new_sticker(monkeypatch):
    insert_user(user_id=1, current_pack="default")
    update = make_message_update(user_id=1, text="cat happy")
    context = make_context()
    context.user_data["sticker"] = (1, "file-id-1", "unique-1", "😀", False)

    sentinel_coroutine = object()
    mock_tagger = MagicMock(return_value=sentinel_coroutine)
    monkeypatch.setattr("functions.sticker_functions.tag_sticker_background", mock_tagger)

    await keywords(update, context)

    mock_tagger.assert_called_once_with(context.bot, 1, "default", "file-id-1", "unique-1")
    context.application.create_task.assert_called_once_with(sentinel_coroutine, update=update)


async def test_keywords_does_not_reschedule_tagging_for_existing_sticker(monkeypatch):
    insert_user(user_id=1, current_pack="default")
    insert_sticker(user_id=1, file_unique_id="unique-1", keywords="old keywords")
    update = make_message_update(user_id=1, text="new keywords")
    context = make_context()
    context.user_data["sticker"] = (1, "file-id-1", "unique-1", "😀", True)

    mock_tagger = MagicMock()
    monkeypatch.setattr("functions.sticker_functions.tag_sticker_background", mock_tagger)

    await keywords(update, context)

    mock_tagger.assert_not_called()
    context.application.create_task.assert_not_called()


async def test_keywords_updates_existing_sticker():
    insert_user(user_id=1, current_pack="default")
    insert_sticker(user_id=1, file_unique_id="unique-1", keywords="old keywords")
    update = make_message_update(user_id=1, text="new keywords")
    context = make_context()
    context.user_data["sticker"] = (1, "file-id-1", "unique-1", "😀", True)

    await keywords(update, context)

    c.execute(
        "SELECT keywords FROM stickers WHERE user_id = ? AND file_unique_id = ?",
        (1, "unique-1"),
    )
    assert c.fetchall() == [("new keywords",)]


async def test_deletesticker_removes_row():
    insert_user(user_id=1, current_pack="default")
    insert_sticker(user_id=1, file_unique_id="unique-1")
    update = make_message_update(
        user_id=1, sticker=make_sticker(file_unique_id="unique-1")
    )
    context = make_context()

    await deletesticker(update, context)

    c.execute("SELECT * FROM stickers WHERE user_id = ? AND file_unique_id = ?", (1, "unique-1"))
    assert c.fetchall() == []
