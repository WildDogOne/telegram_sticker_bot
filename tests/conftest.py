"""
Test setup notes:

The app connects to sqlite and reads bot credentials at import time
(functions/global_functions.py runs `sqlite3.connect(db)` as soon as it's
imported, using `db`/`token`/etc. from config.config). To keep tests from
touching the developer's real config.py/stickers.db, we inject a fake
`config.config` module into sys.modules *before* anything under `functions/`
or `main` gets imported, pointing `db` at an in-memory sqlite database.
"""
import itertools
import sys
import types
from datetime import datetime

TEST_DEFAULT_USER_ID = 999999


def _install_fake_config():
    config_pkg = types.ModuleType("config")
    config_module = types.ModuleType("config.config")
    config_module.token = "TEST:TOKEN"  # noqa: S105 - not a real secret
    config_module.db = ":memory:"
    config_module.owner_id = 111111
    config_module.default_user_id = TEST_DEFAULT_USER_ID
    config_module.botname = "@TestStickerBot"
    config_pkg.config = config_module
    sys.modules["config"] = config_pkg
    sys.modules["config.config"] = config_module


_install_fake_config()

import pytest
from unittest.mock import AsyncMock, MagicMock

from main import init_db
from functions.global_functions import c, conn


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    init_db()
    conn.commit()


@pytest.fixture(autouse=True)
def clean_db():
    """Every test starts from empty tables, regardless of what earlier tests wrote."""
    for table in ("stickers", "users", "user_packs"):
        c.execute(f"DELETE FROM {table}")
    conn.commit()
    yield


@pytest.fixture(autouse=True)
def no_admin_dm(monkeypatch):
    """Never let a test actually hit the Telegram API to DM the bot owner."""
    mock = AsyncMock()
    for target in (
        "functions.bot_functions.send_message_to_admin",
        "functions.pack_functions.send_message_to_admin",
        "functions.sticker_functions.send_message_to_admin",
    ):
        monkeypatch.setattr(target, mock)
    return mock


@pytest.fixture(autouse=True)
def no_telegram_api_calls(monkeypatch):
    """`start()` calls set_commands(), which hits the real Bot API - stub it out."""
    monkeypatch.setattr("functions.bot_functions.set_commands", AsyncMock())


@pytest.fixture(autouse=True)
def no_real_message_network_calls(monkeypatch):
    """telegram.Message is a frozen TelegramObject - real instances built by
    make_real_update() can't have reply_text stubbed per-instance, so stub it
    at the class level instead (reverted by monkeypatch after each test)."""
    from telegram import Message

    monkeypatch.setattr(Message, "reply_text", AsyncMock())


@pytest.fixture(autouse=True)
def reset_error_alert_cooldown():
    """error_handler()'s per-exception-type rate limit is module-level state - clear it
    between tests so one test's alert doesn't suppress another's."""
    import functions.bot_functions as bot_functions

    bot_functions._last_error_alert.clear()
    yield


def make_user(user_id=1, first_name="Test"):
    user = MagicMock()
    user.id = user_id
    user.first_name = first_name
    return user


def make_sticker(file_id="file-id-1", file_unique_id="unique-1", emoji="😀"):
    sticker = MagicMock()
    sticker.file_id = file_id
    sticker.file_unique_id = file_unique_id
    sticker.emoji = emoji
    return sticker


def make_message_update(user_id=1, text=None, sticker=None):
    update = MagicMock()
    message = MagicMock()
    message.reply_text = AsyncMock()
    user = make_user(user_id)
    message.from_user = user
    message.text = text
    message.sticker = sticker
    update.message = message
    update.effective_user = user
    return update


def make_inline_query_update(user_id=1, query=""):
    update = MagicMock()
    update.inline_query = MagicMock()
    update.inline_query.query = query
    update.inline_query.from_user = make_user(user_id)
    update.inline_query.answer = AsyncMock()
    return update


def make_chosen_inline_result_update(user_id=1, file_unique_id="unique-1"):
    update = MagicMock()
    update.chosen_inline_result = MagicMock()
    update.chosen_inline_result.result_id = file_unique_id
    update.chosen_inline_result.from_user = make_user(user_id)
    return update


def make_context():
    context = MagicMock()
    context.user_data = {}
    # Real fire-and-forget calls hand a live coroutine to application.create_task();
    # a bare MagicMock would never await/close it, leaking a "coroutine was never
    # awaited" warning into every test that reaches that code path. Closing it here
    # keeps the default context usable as a no-op while still recording the call
    # (call_args etc.) for tests that want to assert on it.
    context.application.create_task = MagicMock(
        side_effect=lambda coro, **kwargs: coro.close() if hasattr(coro, "close") else None
    )
    return context


# --- Real (non-Mock) Update/Message helpers ---
#
# ConversationHandler.check_update() does `isinstance(update, Update)` and reads
# update.effective_chat/effective_user - a plain MagicMock can't satisfy that. These
# helpers build real telegram objects so tests can drive the actual routing logic
# (check_update/handle_update), e.g. to verify that starting one flow correctly
# interrupts another rather than the two conversations racing.
from telegram import Chat, Message, MessageEntity, Sticker as TgSticker, Update, User

_FAKE_TELEGRAM_BOT = types.SimpleNamespace(username="TestStickerBot")
_next_id = itertools.count(1)


def make_real_sticker(file_id="file-id-1", file_unique_id="unique-1", emoji="😀"):
    return TgSticker(
        file_id=file_id,
        file_unique_id=file_unique_id,
        width=512,
        height=512,
        is_animated=False,
        is_video=False,
        type=TgSticker.REGULAR,
        emoji=emoji,
    )


def make_real_update(user_id=1, text=None, sticker=None):
    """A real Update/Message pair. `Message.reply_text` is stubbed at the class
    level by the `no_real_message_network_calls` autouse fixture, since Message
    is a frozen TelegramObject and can't have per-instance attributes set.
    `chat.id == user_id` mirrors how Telegram private chats work."""
    chat = Chat(id=user_id, type=Chat.PRIVATE)
    user = User(id=user_id, is_bot=False, first_name="Test")
    entities = None
    if text and text.startswith("/"):
        command = text.split()[0]
        entities = [MessageEntity(type=MessageEntity.BOT_COMMAND, offset=0, length=len(command))]
    message = Message(
        message_id=next(_next_id),
        date=datetime.now(),
        chat=chat,
        from_user=user,
        text=text,
        entities=entities,
        sticker=sticker,
    )
    message.set_bot(_FAKE_TELEGRAM_BOT)
    return Update(update_id=next(_next_id), message=message)


def insert_sticker(
    user_id=1,
    pack_id="default",
    file_unique_id="unique-1",
    file_id="file-id-1",
    keywords="cat happy",
    emojies="😀",
    clip=None,
    frequency=0,
):
    c.execute(
        "INSERT INTO stickers (user_id, pack_id, file_unique_id, file_id, keywords, emojies, CLIP, frequency) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, pack_id, file_unique_id, file_id, keywords, emojies, clip, frequency),
    )
    conn.commit()


def insert_user(user_id=1, current_pack="default"):
    c.execute(
        "INSERT INTO users (user_id, current_pack) VALUES (?, ?)",
        (user_id, current_pack),
    )
    conn.commit()


def insert_user_pack(user_id=1, pack="default"):
    c.execute(
        "INSERT INTO user_packs (user_id, pack) VALUES (?, ?)",
        (user_id, pack),
    )
    conn.commit()
