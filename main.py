from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
)
from config.config import token
from pprint import pprint
from bot_functions import *
from global_functions import c


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


def main() -> None:
    application = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Sticker.ALL, sticker)],
        states={
            KEYWORDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, keywords)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(InlineQueryHandler(inline_query))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("packs", get_packs))
    application.add_handler(ChosenInlineResultHandler(chosen_inline_result))
    application.run_polling()


if __name__ == "__main__":
    init_db()
    main()
