from telegram import (
    Bot,
    BotCommand,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineQueryResultCachedSticker,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
    InlineQueryHandler,
    ChosenInlineResultHandler,
)

from config.config import token, default_user_id, owner_id
from functions.global_functions import *
from functions.pack_functions import get_current_pack
from functions.bot_functions import send_message_to_admin



### Sticker Handler
async def sticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    file_id = update.message.sticker.file_id
    file_unique_id = update.message.sticker.file_unique_id
    emojies = update.message.sticker.emoji
    pprint(update.message.sticker)
    context.user_data["sticker"] = (user_id, file_id, file_unique_id, emojies)
    await update.message.reply_text(
        "What keywords do you want to attach to this sticker?"
    )
    return KEYWORDS


async def keywords(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keywords = update.message.text
    user_id, file_id, file_unique_id, emojies = context.user_data["sticker"]
    # pack_id = "default"
    pack_id = await get_current_pack(user_id)
    print(user_id, pack_id, file_unique_id, file_id, keywords, emojies)
    try:
        c.execute(
            "INSERT INTO stickers (user_id, pack_id, file_unique_id, file_id, keywords, emojies) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, pack_id, file_unique_id, file_id, keywords, emojies),
        )
        conn.commit()
        await update.message.reply_text("Sticker saved!")
    except Exception as e:
        await update.message.reply_text("Error while saving!")
        logger.error("Error while saving sticker")
        logger.error(e)
        await send_message_to_admin(f"Error while saving sticker\n{e}")
    return ConversationHandler.END