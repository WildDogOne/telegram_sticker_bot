from telegram.ext import ConversationHandler

from conftest import make_context, make_message_update
from functions.bot_functions import cancel, error_handler, initialize_user, start
from functions.global_functions import c


async def test_initialize_user_creates_user_and_default_pack():
    is_new_user = await initialize_user(user_id=7)

    assert is_new_user is True
    c.execute("SELECT current_pack FROM users WHERE user_id = ?", (7,))
    assert c.fetchall() == [("default",)]
    c.execute("SELECT pack FROM user_packs WHERE user_id = ?", (7,))
    assert c.fetchall() == [("default",)]


async def test_initialize_user_is_idempotent(no_admin_dm):
    assert await initialize_user(user_id=7) is True
    assert await initialize_user(user_id=7) is False  # must not raise on the duplicate INSERT

    c.execute("SELECT * FROM users WHERE user_id = ?", (7,))
    assert len(c.fetchall()) == 1
    no_admin_dm.assert_not_awaited()


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


async def test_error_handler_notifies_admin(no_admin_dm):
    context = make_context()
    context.error = ValueError("boom")

    await error_handler("some update", context)

    no_admin_dm.assert_awaited_once()
    assert "ValueError" in no_admin_dm.await_args.args[0]
    assert "boom" in no_admin_dm.await_args.args[0]


async def test_error_handler_rate_limits_repeated_same_type(no_admin_dm):
    context = make_context()
    context.error = ValueError("first")

    await error_handler("update-1", context)
    context.error = ValueError("second")
    await error_handler("update-2", context)  # same exception type, should be throttled

    no_admin_dm.assert_awaited_once()


async def test_error_handler_does_not_throttle_different_exception_types(no_admin_dm):
    context = make_context()
    context.error = ValueError("first")
    await error_handler("update-1", context)

    context.error = KeyError("second")
    await error_handler("update-2", context)

    assert no_admin_dm.await_count == 2
