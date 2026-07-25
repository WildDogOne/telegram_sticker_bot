from telegram.ext import CommandHandler, ConversationHandler, MessageHandler

from conftest import make_context, make_real_sticker, make_real_update
from functions.global_functions import (
    DELETEPACK,
    DELETESTICKER,
    KEYWORDS,
    NEWPACKNAME,
    SELECTPACK,
    c,
)
from main import build_application


def _the_conversation_handler(application):
    handlers = [h for h in application.handlers[0] if isinstance(h, ConversationHandler)]
    assert len(handlers) == 1, "expected exactly one consolidated ConversationHandler"
    return handlers[0]


def test_single_conversation_handler_covers_all_five_flows():
    """All five flows must share one state machine, or a user can end up "inside"
    more than one at once - see ISSUES.md #2."""
    application = build_application()
    handler = _the_conversation_handler(application)

    assert len(handler.entry_points) == 5
    assert {KEYWORDS, NEWPACKNAME, SELECTPACK, DELETEPACK, DELETESTICKER} == set(handler.states)

    # Every entry point must also be a fallback, so triggering a different flow
    # mid-conversation interrupts the pending one instead of being silently
    # dropped or misrouted to the wrong flow.
    assert len(handler.fallbacks) == 1 + len(handler.entry_points)
    assert any(isinstance(f, CommandHandler) and "cancel" in f.commands for f in handler.fallbacks)
    for entry_point in handler.entry_points:
        assert entry_point in handler.fallbacks


async def test_starting_a_different_flow_interrupts_the_pending_one():
    """Regression test for the exact bug in ISSUES.md #2: a user starts /newpack,
    then sends a sticker instead of a pack name. That must switch cleanly to the
    add-sticker flow - not leave /newpack's conversation dangling to steal the
    next unrelated text message the user sends (which used to silently create an
    unwanted pack instead of saving the sticker's keywords)."""
    application = build_application()
    handler = _the_conversation_handler(application)
    context = make_context()

    newpack_update = make_real_update(user_id=1, text="/newpack")
    check = handler.check_update(newpack_update)
    assert check is not None
    await handler.handle_update(newpack_update, application, check, context)
    key = handler._get_key(newpack_update)
    assert handler._conversations[key] == NEWPACKNAME

    # Instead of typing a pack name, the user sends a sticker.
    sticker_update = make_real_update(user_id=1, sticker=make_real_sticker())
    check = handler.check_update(sticker_update)
    assert check is not None
    await handler.handle_update(sticker_update, application, check, context)

    # The sticker fallback (not newpackname()) must have handled it: state moves
    # to KEYWORDS, not stuck in NEWPACKNAME.
    assert handler._conversations[key] == KEYWORDS

    # The user now sends the keywords for that sticker.
    keywords_update = make_real_update(user_id=1, text="cute cat")
    check = handler.check_update(keywords_update)
    assert check is not None
    await handler.handle_update(keywords_update, application, check, context)

    # The text must have been saved as sticker keywords, not misrouted into
    # newpackname() and turned into an unwanted new pack.
    c.execute("SELECT keywords FROM stickers WHERE user_id = ?", (1,))
    assert c.fetchall() == [("cute cat",)]
    c.execute("SELECT pack FROM user_packs WHERE user_id = ? AND pack = ?", (1, "cute cat"))
    assert c.fetchall() == []
