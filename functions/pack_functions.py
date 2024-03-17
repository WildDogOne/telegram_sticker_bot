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

from functions.global_functions import *
from functions.bot_functions import send_message_to_admin


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