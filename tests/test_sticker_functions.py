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
from functions.sticker_functions import (
    deletesticker,
    initialize_user,
    keywords,
    sticker,
)


async def test_initialize_user_creates_user_and_default_pack():
    await initialize_user(user_id=7)

    c.execute("SELECT current_pack FROM users WHERE user_id = ?", (7,))
    assert c.fetchall() == [("default",)]
    c.execute("SELECT pack FROM user_packs WHERE user_id = ?", (7,))
    assert c.fetchall() == [("default",)]


async def test_initialize_user_is_idempotent(no_admin_dm):
    await initialize_user(user_id=7)
    await initialize_user(user_id=7)  # must not raise on the duplicate INSERT

    c.execute("SELECT * FROM users WHERE user_id = ?", (7,))
    assert len(c.fetchall()) == 1
    no_admin_dm.assert_not_awaited()


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
