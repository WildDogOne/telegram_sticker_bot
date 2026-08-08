from collections import Counter

from telegram import (
    Update,
    InlineQueryResultCachedSticker,
)
from telegram.ext import (
    ContextTypes,
)
from thefuzz import fuzz

from config.config import default_user_id
from functions.global_functions import *
from functions.pack_functions import get_current_pack

# Auto-generated CLIP tags that are true for most of a pack's stickers (e.g. a pack
# that's almost entirely anthro canines will have "fur"/"mammal"/"canine" on nearly
# every sticker) add no discriminating power to fuzzy search, even though they're
# accurate. Rather than hardcoding a stoplist - which would wrongly drop a tag like
# "canine" the moment the pack becomes more diverse - frequency is computed fresh per
# query against the exact pack being searched, so it adapts as the pack's content mix
# changes. Only applied to CLIP (auto-generated); user-written `keywords` are never
# filtered. Skipped below CLIP_FREQUENCY_MIN_POOL since "common" is meaningless noise
# on a handful of stickers.
CLIP_FREQUENCY_THRESHOLD = 0.5
CLIP_FREQUENCY_MIN_POOL = 10


def _ubiquitous_clip_tags(clip_values) -> set:
    tag_counts = Counter()
    pool_size = 0
    for clip in clip_values:
        if not clip:
            continue
        pool_size += 1
        tag_counts.update(set(clip.split()))
    if pool_size < CLIP_FREQUENCY_MIN_POOL:
        return set()
    return {tag for tag, count in tag_counts.items() if count / pool_size > CLIP_FREQUENCY_THRESHOLD}


def _strip_tags(text, tags_to_strip: set) -> str:
    if not text or not tags_to_strip:
        return text
    return " ".join(tag for tag in text.split() if tag not in tags_to_strip)


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.inline_query.query
    user_id = update.inline_query.from_user.id
    logger.debug(f"Inline query from user {user_id}: {query!r}")
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
    ubiquitous_tags = _ubiquitous_clip_tags(result[4] for result in results)
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
        if not query:
            # No query typed yet (Telegram sends "" here, never None) - browse everything.
            favourites.append(x)
        elif emojies and query.strip() in emojies:
            # emojies can be NULL for a sticker saved without one - Telegram always sends an
            # emoji in practice, but guard against it anyway rather than crash on `in None`.
            favourites.append(x)
        elif fuzz.token_set_ratio(query, keywords) > 70:
            favourites.append(x)
        elif fuzz.token_set_ratio(query, _strip_tags(clip, ubiquitous_tags)) > 70:
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
        """
        Update stickers
        Set frequency = frequency + 1
        Where user_id = ? AND file_unique_id = ?
        """,
        (user_id, file_unique_id),
    )
    conn.commit()
