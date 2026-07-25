"""
Test setup notes:

The app connects to sqlite and reads bot credentials at import time
(functions/global_functions.py runs `sqlite3.connect(db)` as soon as it's
imported, using `db`/`token`/etc. from config.config). To keep tests from
touching the developer's real config.py/stickers.db, we inject a fake
`config.config` module into sys.modules *before* anything under `functions/`
or `main` gets imported, pointing `db` at an in-memory sqlite database.
"""
import sys
import types

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
    return context


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
