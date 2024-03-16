from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
)


from config.config import token
from global_functions import *


# Telegram Bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hi! Send me a sticker and I will store it for you."
    )


async def sticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    sticker_id = update.message.sticker.file_unique_id
    emoji = update.message.sticker.emoji
    pprint(update.message.sticker)
    context.user_data["sticker"] = (user_id, sticker_id, emoji)
    await update.message.reply_text(
        "What keywords do you want to attach to this sticker?"
    )
    return KEYWORDS


async def keywords(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keywords = update.message.text
    user_id, sticker_id, emoji = context.user_data["sticker"]
    pack_id = 0
    try:
        c.execute(
            "INSERT INTO stickers (user_id, pack_id, sticker_id, keywords, emojies) VALUES (?, ?, ?, ?, ?)", (user_id, pack_id, sticker_id, keywords, emoji),
        )
        conn.commit()
        await update.message.reply_text("Sticker saved!")
    except Exception as e:
        await update.message.reply_text("Error while saving!")
        logger.error("Error while saving sticker")
        logger.error(e)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # user = update.message.from_user
    # logger.info("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text(
        "Bye! I hope we can talk again some day.", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END
