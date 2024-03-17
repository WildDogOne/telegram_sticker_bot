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
    InlineKeyboardButton,
    InlineKeyboardMarkup,
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

from config.config import token, default_user_id, owner_id, botname
from functions.global_functions import *
from functions.pack_functions import get_current_pack
from functions.bot_functions import send_message_to_admin



### Add Sticker
#### Step 1: Ask for keywords for sent sticker
async def sticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    file_id = update.message.sticker.file_id
    file_unique_id = update.message.sticker.file_unique_id
    emojies = update.message.sticker.emoji
    pprint(update.message.sticker)
    # Check if sticker is already in DB
    c.execute(
        "SELECT keywords FROM stickers WHERE user_id = ? AND file_unique_id = ?",
        (user_id, file_unique_id),
    )
    results = c.fetchall()
    if len(results) > 0:
        current_keywords = results[0][0]
        await update.message.reply_text(f"This sticker is already saved!\nCurrent keywords: {current_keywords}")
        await update.message.reply_text("If you want to change the keywords, send new ones.\nOr send /cancel to cancel.")
        exists = True
    else:
        await update.message.reply_text(
            "What keywords do you want to attach to this sticker?"
        )
        exists = False
    context.user_data["sticker"] = (user_id, file_id, file_unique_id, emojies, exists)
    return KEYWORDS

#### Step 2: Save the sticker
async def keywords(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keywords = update.message.text
    user_id, file_id, file_unique_id, emojies, exists = context.user_data["sticker"]
    # pack_id = "default"
    pack_id = await get_current_pack(user_id)
    print(user_id, pack_id, file_unique_id, file_id, keywords, emojies)
    try:
        if exists:
            c.execute(
                "UPDATE stickers SET keywords = ? WHERE user_id = ? AND file_unique_id = ? AND pack_id = ?",
                (keywords, user_id, file_unique_id, pack_id),
            )
        else:
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

### Delete Sticker
#### Step 1: Give list of stickers available

async def delete_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        f"Reply with a sticker you want to delete.\nYou can use {botname} to select stickers.\nOr send /cancel to cancel."
    )
    return DELETESTICKER

#### Step 2: Delete the sticker
async def deletesticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    file_unique_id = update.message.sticker.file_unique_id
    pack_id = await get_current_pack(user_id)
    pprint(update.message.sticker)
    c.execute(
        "DELETE FROM stickers WHERE user_id = ? AND file_unique_id = ? AND pack_id = ?",
        (user_id, file_unique_id, pack_id),
    )
    conn.commit()
    await update.message.reply_text("Sticker deleted!")
    return ConversationHandler.END