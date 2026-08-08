from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    InlineQueryHandler,
    ChosenInlineResultHandler,
)
from config.config import token
from functions.bot_functions import start, cancel, help, error_handler
from functions.pack_functions import (
    pack,
    newpack,
    newpackname,
    get_packs,
    selectpack,
    deletepack,
    delpack,
)
from functions.sticker_functions import sticker, keywords, delete_sticker, deletesticker
from functions.inline_functions import chosen_inline_result, inline_query
from functions.tagging_functions import retag
from functions.global_functions import (
    c,
    KEYWORDS,
    NEWPACKNAME,
    SELECTPACK,
    DELETEPACK,
    DELETESTICKER,
)


def init_db():
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS "stickers" (
        "user_id"  INTEGER NOT NULL,
        "pack_id"  TEXT NOT NULL,
        "file_unique_id"  TEXT NOT NULL,
        "file_id"  TEXT NOT NULL,
        "keywords"  TEXT,
        "emojies"  TEXT,
        "CLIP" TEXT,
        "frequency" INT DEFAULT 0,
        PRIMARY KEY("user_id","file_unique_id","pack_id")
        );
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS "users" (
        "user_id"  INTEGER NOT NULL,
        "current_pack"  TEXT NOT NULL,
        PRIMARY KEY("user_id")
        );
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS "user_packs" (
        "user_id"  INTEGER NOT NULL,
        "pack"  TEXT NOT NULL,
        PRIMARY KEY("user_id", "pack")
        );
        """
    )


def build_application() -> Application:
    """Wires up all handlers and returns the built Application, without starting polling.

    Split out from main() so tests can inspect the handler configuration
    without triggering a real Telegram connection.
    """
    application = Application.builder().token(token).build()

    # All five multi-step flows (add sticker, new/select/delete pack, delete sticker)
    # are combined into a single ConversationHandler, so there is exactly one
    # conversation state per user at a time. Each flow's trigger is also registered
    # as a fallback: if a user is mid-flow and triggers a *different* one (e.g. sends
    # a sticker while /newpack is still waiting for a pack name), that fallback fires
    # and cleanly switches flows, instead of the two independent state machines
    # racing and having the wrong one silently swallow the next message. See
    # ISSUES.md #2 for the bug this replaces.
    entry_points = [
        MessageHandler(filters.Sticker.ALL, sticker),
        CommandHandler("newpack", newpack),
        CommandHandler("pack", pack),
        CommandHandler("delpack", delpack),
        CommandHandler("delete_sticker", delete_sticker),
    ]

    conversation_handler = ConversationHandler(
        entry_points=entry_points,
        states={
            KEYWORDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, keywords)],
            NEWPACKNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, newpackname)],
            SELECTPACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, selectpack)],
            DELETEPACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, deletepack)],
            DELETESTICKER: [MessageHandler(filters.Sticker.ALL, deletesticker)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            *entry_points,
        ],
    )

    application.add_handler(conversation_handler)
    application.add_handler(InlineQueryHandler(inline_query))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("packs", get_packs))
    application.add_handler(CommandHandler("retag", retag))
    application.add_handler(ChosenInlineResultHandler(chosen_inline_result))
    application.add_error_handler(error_handler)
    return application


def main() -> None:
    application = build_application()
    application.run_polling()


if __name__ == "__main__":
    init_db()
    main()
