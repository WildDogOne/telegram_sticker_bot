from telegram.ext import ConversationHandler

from conftest import make_context, make_message_update
from functions.bot_functions import cancel, start
from functions.global_functions import c


async def test_start_creates_user_and_default_pack():
    update = make_message_update(user_id=1)
    context = make_context()

    await start(update, context)

    c.execute("SELECT current_pack FROM users WHERE user_id = ?", (1,))
    assert c.fetchall() == [("default",)]
    c.execute("SELECT pack FROM user_packs WHERE user_id = ?", (1,))
    assert c.fetchall() == [("default",)]


async def test_start_existing_user_gets_friendly_message(no_admin_dm):
    update = make_message_update(user_id=1)
    context = make_context()

    await start(update, context)
    await start(update, context)  # second /start must not raise

    update.message.reply_text.assert_any_await("I already know you!")
    no_admin_dm.assert_not_awaited()


async def test_cancel_ends_conversation():
    update = make_message_update(user_id=1)
    context = make_context()

    result = await cancel(update, context)

    assert result == ConversationHandler.END
    update.message.reply_text.assert_awaited_once()
