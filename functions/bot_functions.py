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


async def set_commands():
    bot = Bot(token)

    commands = [
        BotCommand(command="/start", description="Start the bot"),
        BotCommand(command="/help", description="Get help information"),
        BotCommand(command="/packs", description="Get your packs"),
        BotCommand(command="/pack", description="Set Pack"),
        BotCommand(command="/newpack", description="New pack"),
        BotCommand(command="/cancel", description="Cancel action"),
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





async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text(
        "Canceling action", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


