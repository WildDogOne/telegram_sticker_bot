from telegram import (
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineQueryResultCachedSticker,
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
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

from config.config import token, default_user_id
from global_functions import *


# Telegram Bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hi! Send me a sticker and I will store it for you.\n"
        "After that, you can use the inline mode to search for your stickers."
    )
    user_id = update.effective_user.id
    pack_id = "default"
    pack = "default"
    try:
        c.execute(
            "INSERT INTO users (user_id, current_pack) VALUES (?, ?)",
            (user_id, pack_id),
        )
    except Exception as e:
        await update.message.reply_text("I already know you!")
        logger.error("Error while saving user")
        logger.error(e)
    try:
        c.execute(
            "INSERT INTO user_packs (user_id, pack) VALUES (?, ?)",
            (user_id, pack),
        )
        conn.commit()
    except Exception as e:
        logger.error("Error while saving user packs")
        logger.error(e)

async def get_packs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    c.execute(
        "SELECT pack FROM user_packs WHERE user_id = ?",
        (user_id,),
    )
    results = c.fetchall()
    if len(results) == 0:
        await update.message.reply_text("You don't have any packs yet!\nUse /start to create a profile")
    else:
        x  = ""
        for result in results:
            x += result[0] + "\n"
        await update.message.reply_text(x)


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
    pack_id = "default"
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
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text(
        "Canceling action", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.inline_query.query
    user_id = update.inline_query.from_user.id
    print(user_id)
    print(query)

    # Fetch favorites from the database
    c.execute(
        "SELECT file_unique_id, file_id, keywords, emojies, frequency FROM stickers WHERE user_id = ? ORDER BY frequency DESC",
        (user_id,),
    )
    results = c.fetchall()
    if len(results) == 0:
        c.execute(
            "SELECT file_unique_id, file_id, keywords, emojies, frequency FROM stickers WHERE user_id = ? ORDER BY frequency DESC",
            (default_user_id,),
        )
        results = c.fetchall()
    favourites = []
    for result in results:
        file_unique_id, file_id, keywords, emojies, frequency = result
        x = {
            "file_unique_id": file_unique_id,
            "file_id": file_id,
            "keywords": keywords,
            "emojies": emojies,
            "frequency": frequency,
        }
        if query == None:
            favourites.append(x)
        else:
            if query.strip() in emojies:
                print("test")
                favourites.append(x)
            elif fuzz.token_set_ratio(query, keywords) > 50:
                favourites.append(x)

    # Convert favorites to inline query results
    results = [
        InlineQueryResultCachedSticker(
            id=str(result["file_unique_id"]),  # id must be unique and a string
            sticker_file_id=result["file_id"],
        )
        for result in favourites
    ]

    # Answer the inline query
    await update.inline_query.answer(results, cache_time=0)

# Function to update the frequency of the sticker used
async def chosen_inline_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    file_unique_id = update.chosen_inline_result.result_id
    user_id = update.chosen_inline_result.from_user.id
    c.execute(
        "SELECT file_unique_id, file_id, keywords, emojies, frequency FROM stickers WHERE user_id = ? ORDER BY frequency DESC",
        (default_user_id,),
    )
    c.execute(
        """
        Update stickers
        Set frequency = frequency + 1
        Where user_id = ? AND file_unique_id = ?
        """, (user_id, file_unique_id)
    )
    conn.commit()
