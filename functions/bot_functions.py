import traceback
from datetime import datetime, timedelta

from telegram import (
    Bot,
    BotCommand,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
)

from config.config import token, owner_id
from functions.global_functions import c, conn, logger


# Helper function to send a message to the admin
async def send_message_to_admin(text):
    bot = Bot(token=token)
    await bot.send_message(chat_id=owner_id, text=text)


# Global fallback error handler, registered via application.add_error_handler().
# Catches anything individual handlers don't already handle themselves, so a
# bug never fails silently. DMs to the owner are rate-limited per exception
# type so a crash loop can't spam the bot's own Telegram account.
ERROR_ALERT_COOLDOWN = timedelta(minutes=5)
_last_error_alert: dict[str, datetime] = {}


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    error = context.error
    logger.error("Unhandled exception while processing an update", exc_info=error)

    key = type(error).__name__
    now = datetime.now()
    last_sent = _last_error_alert.get(key)
    if last_sent is not None and now - last_sent < ERROR_ALERT_COOLDOWN:
        return
    _last_error_alert[key] = now

    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    message = (
        f"Unhandled exception: {type(error).__name__}: {error}\n\n"
        f"Update: {update_str}\n\n"
        f"{tb}"
    )
    if len(message) > 4000:
        message = message[:4000] + "\n... (truncated)"
    await send_message_to_admin(message)


async def set_commands():
    bot = Bot(token)

    commands = [
        BotCommand(command="/start", description="Start the bot"),
        BotCommand(command="/help", description="Get help information"),
        BotCommand(command="/pack", description="Set Pack to use"),
        BotCommand(command="/packs", description="Get your packs"),
        BotCommand(command="/delete_sticker", description="Delete a sticker from the current pack"),
        BotCommand(command="/newpack", description="New pack"),
        BotCommand(command="/delpack", description="Remove a pack"),
        BotCommand(command="/cancel", description="Cancel action"),
        # Add more commands as needed
    ]

    await bot.set_my_commands(commands)


# Telegram Bot
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Send me a sticker and I will store it for you.\n"
        "After that, you can use the inline mode to search for your stickers.\n"
        "To change keywords on a sticker, just send the same sticker again, you can use the inline mode to search for your stickers.\n"
        "Other commands:\n"
        "/pack - Set Pack to use, normaly this will be default unless you created a new pack\n"
        "/packs - Get your packs\n"
        "/newpack - Make a new pack\n"
        "/delpack - Remove a pack\n"
        "/delete_sticker - Delete a sticker from the current pack"
    )
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


