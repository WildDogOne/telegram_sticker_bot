from telegram import (
    ReplyKeyboardMarkup,
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton,
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
)

from functions.global_functions import c, conn, logger, NEWPACKNAME, SELECTPACK, DELETEPACK
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

def packkeyboard(user_id):
    c.execute(
        "SELECT pack FROM user_packs WHERE user_id = ?",
        (user_id,),
    )
    results = c.fetchall()
    keyboard = []
    for x in results:
        keyboard.append([KeyboardButton(x[0])])
    keyboard.append([KeyboardButton("/cancel")])
    reply_markup = ReplyKeyboardMarkup(
        keyboard, resize_keyboard=True, one_time_keyboard=True
    )
    return reply_markup


### New Pack
#### Step 1: Ask for the name of the pack
async def newpack(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("What is the name of the pack?")
    return NEWPACKNAME

#### Step 2: Save the pack name
async def newpackname(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    pack = update.message.text
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
    return ConversationHandler.END


### Select Pack
#### Step 1: Ask for the pack to use
async def pack(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    reply_markup = packkeyboard(user_id)

    await update.message.reply_text(
        "Which pack do you want to use?", reply_markup=reply_markup
    )
    return SELECTPACK

#### Step 2: Save the pack to use
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
    await update.message.reply_text(
        f"Selected {pack}", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END





### Delete Pack
#### Step 1: Ask for the pack to delete
async def delpack(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    print(user_id)
    reply_markup = packkeyboard(user_id)

    await update.message.reply_text(
        "Which pack do you want to delete?", reply_markup=reply_markup
    )
    return DELETEPACK

#### Step 2: Delete the pack
async def deletepack(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    pack = update.message.text
    if pack == "default":
        await update.message.reply_text(
            "You can't delete the default pack", reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    else:
        # Delete pack from user_packs
        c.execute(
            """
            DELETE FROM user_packs
            Where user_id = ? AND pack = ?;
            """,
            (user_id, pack),
        )
        # Delete stickers associated with pack
        c.execute(
            """
            DELETE FROM stickers
            Where user_id = ? AND pack_id = ?;
            """,
            (user_id, pack),
        )
        conn.commit()
        await update.message.reply_text(
            f"Removed {pack}", reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END


### Output Packs
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
