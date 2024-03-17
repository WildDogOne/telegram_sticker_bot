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
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

from config.config import token, default_user_id, owner_id
from functions.global_functions import *


# Helper function to send a message to the admin
async def send_message_to_admin(text):
    bot = Bot(token=token)
    await bot.send_message(chat_id=owner_id, text=text)


async def get_current_pack(user_id):
    c.execute(
        "SELECT current_pack FROM users WHERE user_id = ?",
        (user_id,),
    )
    results = c.fetchall()
    if len(results) == 0:
        return "default"
    else:
        return results[0][0]


async def set_commands():
    bot = Bot(token)

    commands = [
        BotCommand(command="/start", description="Start the bot"),
        BotCommand(command="/help", description="Get help information"),
        BotCommand(command="/packs", description="Get your packs"),
        BotCommand(command="/pack", description="Set Pack"),
        BotCommand(command="/newpack", description="New pack"),
        # Add more commands as needed
    ]

    await bot.set_my_commands(commands)


# Telegram Bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hi! Send me a sticker and I will store it for you.\n"
        "After that, you can use the inline mode to search for your stickers."
    )
    await set_commands()

    user_id = update.effective_user.id
    pack_id = "default"
    pack = "default"
    try:
        c.execute(
            "INSERT INTO users (user_id, current_pack) VALUES (?, ?)",
            (user_id, pack_id),
        )
    except Exception as e:
        if type(e).__name__ == "IntegrityError":
            await update.message.reply_text("I already know you!")
            logger.info(f"Error while saving user {user_id}, user already exists")
            logger.info(e)
        else:
            await send_message_to_admin(f"Error while saving user {user_id}\n{e}")
    try:
        c.execute(
            "INSERT INTO user_packs (user_id, pack) VALUES (?, ?)",
            (user_id, pack),
        )
        conn.commit()
    except Exception as e:
        if type(e).__name__ == "IntegrityError":
            logger.info(f"Error while adding default pack to user {user_id}")
            logger.info(e)
        else:
            await send_message_to_admin(f"Error while saving user {user_id}\n{e}")


async def get_packs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    c.execute(
        "SELECT pack FROM user_packs WHERE user_id = ?",
        (user_id,),
    )
    results = c.fetchall()
    if len(results) == 0:
        await update.message.reply_text(
            "You don't have any packs yet!\nUse /start to create a profile"
        )
    else:
        x = ""
        for result in results:
            x += result[0] + "\n"
        await update.message.reply_text(x)


### Pack Handlers
#### Add a new pack
async def newpack(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("What is the name of the pack?")
    return PACKNAME


async def packname(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    pack = update.message.text
    # context.user_data["packname"] = (user_id)
    try:
        c.execute(
            "INSERT INTO user_packs (user_id, pack) VALUES (?, ?)",
            (user_id, pack),
        )
        conn.commit()
        await update.message.reply_text("Pack added!")
    except Exception as e:
        if type(e).__name__ == "IntegrityError":
            await update.message.reply_text("You already have a pack with that name")
            logger.info(f"Error while adding duplicate pack to user {user_id}")
            logger.info(e)
        else:
            await send_message_to_admin(
                f"Error while adding pack to user {user_id}\n{e}"
            )


async def pack(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    print(user_id)
    c.execute(
        "SELECT pack FROM user_packs WHERE user_id = ?",
        (user_id,),
    )
    results = c.fetchall()
    keyboard = []
    for x in results:
        keyboard.append([KeyboardButton(x[0])])
    pprint(keyboard)
    reply_markup = ReplyKeyboardMarkup(
        keyboard, resize_keyboard=True, one_time_keyboard=True
    )

    await update.message.reply_text(
        "Which pack do you want to use?", reply_markup=reply_markup
    )
    return SELECTPACK


async def selectpack(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    pack = update.message.text
    c.execute(
        """
        Update users
        Set current_pack = ?
        Where user_id = ?
        """,
        (pack, user_id),
    )
    conn.commit()
    await update.message.reply_text(f"Selected {pack}")


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
    pack_id = await get_current_pack(user_id)

    # Fetch favorites from the database
    SQL_QUERY = "SELECT file_unique_id, file_id, keywords, emojies, frequency FROM stickers WHERE user_id = ? AND pack_id = ? ORDER BY frequency DESC"
    c.execute(
        SQL_QUERY,
        (user_id, pack_id),
    )
    results = c.fetchall()
    if len(results) == 0:
        c.execute(
            SQL_QUERY,
            (default_user_id, "default"),
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
    await update.inline_query.answer(
        results, cache_time=1, auto_pagination=True, is_personal=True
    )


# Function to update the frequency of the sticker used
async def chosen_inline_result(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
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
        """,
        (user_id, file_unique_id),
    )
    conn.commit()
