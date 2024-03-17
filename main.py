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
from pprint import pprint
from functions.bot_functions import start, cancel
from functions.pack_functions import pack, newpack, packname, get_packs, selectpack
from functions.sticker_functions import sticker, keywords
from functions.inline_functions import chosen_inline_result, inline_query
from functions.global_functions import c, KEYWORDS, PACKNAME, SELECTPACK


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

    add_sticker_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Sticker.ALL, sticker)],
        states={
            KEYWORDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, keywords)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    add_pack_handler = ConversationHandler(
        entry_points=[CommandHandler("newpack", newpack)],
        states={
            PACKNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, packname)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    select_pack_handler = ConversationHandler(
        entry_points=[CommandHandler("pack", pack)],
        states={
            SELECTPACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, selectpack)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(add_sticker_handler)
    application.add_handler(add_pack_handler)
    application.add_handler(select_pack_handler)
    application.add_handler(InlineQueryHandler(inline_query))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("packs", get_packs))
    application.add_handler(ChosenInlineResultHandler(chosen_inline_result))
    application.run_polling()


if __name__ == "__main__":
    init_db()
    main()
