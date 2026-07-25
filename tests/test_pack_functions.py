from telegram.ext import ConversationHandler

from conftest import (
    insert_sticker,
    insert_user,
    insert_user_pack,
    make_context,
    make_message_update,
)
from functions.global_functions import c
from functions.pack_functions import (
    deletepack,
    get_current_pack,
    get_packs,
    newpackname,
    selectpack,
)


async def test_get_current_pack_defaults_when_user_unknown():
    assert await get_current_pack(user_id=42) == "default"


async def test_get_current_pack_returns_stored_value():
    insert_user(user_id=1, current_pack="memes")
    assert await get_current_pack(user_id=1) == "memes"


async def test_newpackname_creates_pack():
    update = make_message_update(user_id=1, text="memes")
    context = make_context()

    result = await newpackname(update, context)

    c.execute("SELECT pack FROM user_packs WHERE user_id = ?", (1,))
    assert c.fetchall() == [("memes",)]
    update.message.reply_text.assert_awaited_once_with("Pack added!")
    assert result == ConversationHandler.END


async def test_newpackname_duplicate_shows_friendly_message(no_admin_dm):
    insert_user_pack(user_id=1, pack="memes")
    update = make_message_update(user_id=1, text="memes")
    context = make_context()

    await newpackname(update, context)

    update.message.reply_text.assert_awaited_once_with(
        "You already have a pack with that name"
    )
    no_admin_dm.assert_not_awaited()


async def test_selectpack_updates_current_pack():
    insert_user(user_id=1, current_pack="default")
    update = make_message_update(user_id=1, text="memes")
    context = make_context()

    await selectpack(update, context)

    assert await get_current_pack(user_id=1) == "memes"


async def test_deletepack_refuses_to_remove_default():
    update = make_message_update(user_id=1, text="default")
    context = make_context()

    result = await deletepack(update, context)

    update.message.reply_text.assert_awaited_once()
    assert "can't delete" in update.message.reply_text.await_args.args[0]
    assert result == ConversationHandler.END


async def test_deletepack_removes_pack_and_its_stickers():
    insert_user_pack(user_id=1, pack="memes")
    insert_sticker(user_id=1, pack_id="memes", file_unique_id="u1")
    update = make_message_update(user_id=1, text="memes")
    context = make_context()

    await deletepack(update, context)

    c.execute("SELECT * FROM user_packs WHERE user_id = ? AND pack = ?", (1, "memes"))
    assert c.fetchall() == []
    c.execute("SELECT * FROM stickers WHERE user_id = ? AND pack_id = ?", (1, "memes"))
    assert c.fetchall() == []


async def test_get_packs_lists_packs():
    insert_user_pack(user_id=1, pack="default")
    insert_user_pack(user_id=1, pack="memes")
    update = make_message_update(user_id=1)
    context = make_context()

    await get_packs(update, context)

    reply = update.message.reply_text.await_args.args[0]
    assert "default" in reply
    assert "memes" in reply


async def test_get_packs_empty_prompts_start():
    update = make_message_update(user_id=1)
    context = make_context()

    await get_packs(update, context)

    update.message.reply_text.assert_awaited_once_with(
        "You don't have any packs yet!\nUse /start to create a profile"
    )
