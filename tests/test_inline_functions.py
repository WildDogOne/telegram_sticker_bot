from conftest import (
    insert_sticker,
    make_chosen_inline_result_update,
    make_context,
    make_inline_query_update,
)
from functions.global_functions import c
from functions.inline_functions import chosen_inline_result, inline_query


def _returned_ids(update):
    results = update.inline_query.answer.await_args.args[0]
    return {result.id for result in results}


async def test_inline_query_matches_emoji_substring():
    insert_sticker(user_id=1, file_unique_id="u1", keywords="unrelated", emojies="😀")
    update = make_inline_query_update(user_id=1, query="😀")

    await inline_query(update, make_context())

    assert _returned_ids(update) == {"u1"}


async def test_inline_query_matches_fuzzy_keywords():
    insert_sticker(user_id=1, file_unique_id="u1", keywords="cat happy", emojies="😀")
    update = make_inline_query_update(user_id=1, query="happy cat")

    await inline_query(update, make_context())

    assert _returned_ids(update) == {"u1"}


async def test_inline_query_excludes_unrelated_stickers():
    insert_sticker(user_id=1, file_unique_id="u1", keywords="cat happy", emojies="😀")
    update = make_inline_query_update(user_id=1, query="spaceship rocket")

    await inline_query(update, make_context())

    assert _returned_ids(update) == set()


async def test_inline_query_orders_by_frequency():
    insert_sticker(user_id=1, file_unique_id="low", keywords="cat", emojies="😀", frequency=1)
    insert_sticker(user_id=1, file_unique_id="high", keywords="cat", emojies="😀", frequency=5)
    update = make_inline_query_update(user_id=1, query="cat")

    await inline_query(update, make_context())

    results = update.inline_query.answer.await_args.args[0]
    assert [r.id for r in results] == ["high", "low"]


async def test_inline_query_falls_back_to_default_pack_when_user_has_none():
    # conftest's fake config sets default_user_id=999999 and the fallback pack is
    # always "default" for that user, regardless of which pack the querying user is on.
    insert_sticker(
        user_id=999999, pack_id="default", file_unique_id="shared", keywords="cat", emojies="😀"
    )
    update = make_inline_query_update(user_id=1, query="cat")

    await inline_query(update, make_context())

    assert _returned_ids(update) == {"shared"}


async def test_inline_query_matches_sticker_without_emoji_via_keywords():
    # A sticker with a NULL emojies column (Telegram always sends an emoji in practice,
    # but the column is nullable) must not crash the emoji-substring check, and should
    # still be findable by its keywords.
    insert_sticker(user_id=1, file_unique_id="u1", keywords="cat happy", emojies=None)
    update = make_inline_query_update(user_id=1, query="cat")

    await inline_query(update, make_context())

    assert _returned_ids(update) == {"u1"}


async def test_inline_query_empty_query_returns_everything_including_no_emoji_stickers():
    insert_sticker(user_id=1, file_unique_id="with-emoji", keywords="cat", emojies="😀")
    insert_sticker(user_id=1, file_unique_id="no-emoji", keywords="dog", emojies=None)
    update = make_inline_query_update(user_id=1, query="")

    await inline_query(update, make_context())

    assert _returned_ids(update) == {"with-emoji", "no-emoji"}


async def test_inline_query_ignores_clip_tag_common_across_whole_pack():
    # "fur" appears on every sticker in this pack (>10, so the frequency filter kicks
    # in) - it should no longer be enough on its own to match, since it can't
    # distinguish any one sticker from the rest.
    for i in range(12):
        insert_sticker(
            user_id=1,
            file_unique_id=f"common-{i}",
            keywords="",
            emojies=None,
            clip="fur mammal",
        )
    insert_sticker(user_id=1, file_unique_id="distinct", keywords="", emojies=None, clip="fur mammal wolf")
    update = make_inline_query_update(user_id=1, query="fur")

    await inline_query(update, make_context())

    assert _returned_ids(update) == set()


async def test_inline_query_still_matches_distinctive_clip_tag():
    for i in range(12):
        insert_sticker(
            user_id=1,
            file_unique_id=f"common-{i}",
            keywords="",
            emojies=None,
            clip="fur mammal",
        )
    insert_sticker(user_id=1, file_unique_id="distinct", keywords="", emojies=None, clip="fur mammal wolf")
    update = make_inline_query_update(user_id=1, query="wolf")

    await inline_query(update, make_context())

    assert _returned_ids(update) == {"distinct"}


async def test_inline_query_skips_frequency_filter_on_small_pack():
    # Below CLIP_FREQUENCY_MIN_POOL, "common" isn't a meaningful signal - a shared tag
    # should still be matchable.
    insert_sticker(user_id=1, file_unique_id="u1", keywords="", emojies=None, clip="fur mammal")
    insert_sticker(user_id=1, file_unique_id="u2", keywords="", emojies=None, clip="fur mammal")
    update = make_inline_query_update(user_id=1, query="fur")

    await inline_query(update, make_context())

    assert _returned_ids(update) == {"u1", "u2"}


async def test_chosen_inline_result_increments_frequency():
    insert_sticker(user_id=1, file_unique_id="u1", frequency=0)
    update = make_chosen_inline_result_update(user_id=1, file_unique_id="u1")

    await chosen_inline_result(update, make_context())

    c.execute(
        "SELECT frequency FROM stickers WHERE user_id = ? AND file_unique_id = ?", (1, "u1")
    )
    assert c.fetchall() == [(1,)]
