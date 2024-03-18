from telegram import (
    Update,
    InlineQueryResultCachedSticker,
)
from telegram.ext import (
    ContextTypes,
)
from fuzzywuzzy import fuzz

from config.config import default_user_id
from functions.global_functions import *
from functions.pack_functions import get_current_pack

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.inline_query.query
    user_id = update.inline_query.from_user.id
    print(user_id)
    print(query)
    pack_id = await get_current_pack(user_id)

    # Fetch favorites from the database
    SQL_QUERY = "SELECT file_unique_id, file_id, keywords, emojies, CLIP, frequency FROM stickers WHERE user_id = ? AND pack_id = ? ORDER BY frequency DESC"
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
        file_unique_id, file_id, keywords, emojies, clip, frequency = result
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
            elif fuzz.token_set_ratio(query, keywords) > 70:
                favourites.append(x)
            elif fuzz.token_set_ratio(query, clip) > 70:
                favourites.append(x)

    # Convert favorites to inline query results#
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
