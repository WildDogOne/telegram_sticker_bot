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
        "pack_id"  INT NOT NULL,
        "sticker_id"  TEXT NOT NULL,
        "keywords"  TEXT,
        "emojies"  TEXT,
        "frequency" INT DEFAULT 0,
        PRIMARY KEY("user_id","sticker_id","pack_id")
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
    application.run_polling()


if __name__ == "__main__":
    init_db()
    main()
