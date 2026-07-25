import pytest

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


@pytest.mark.xfail(
    reason="known bug: stickers saved with no emoji store NULL, and "
    "`query.strip() in emojies` crashes on None for any non-empty query",
    strict=True,
)
async def test_inline_query_does_not_crash_on_sticker_without_emoji():
    insert_sticker(user_id=1, file_unique_id="u1", keywords="cat happy", emojies=None)
    update = make_inline_query_update(user_id=1, query="cat")

    await inline_query(update, make_context())


async def test_chosen_inline_result_increments_frequency():
    insert_sticker(user_id=1, file_unique_id="u1", frequency=0)
    update = make_chosen_inline_result_update(user_id=1, file_unique_id="u1")

    await chosen_inline_result(update, make_context())

    c.execute(
        "SELECT frequency FROM stickers WHERE user_id = ? AND file_unique_id = ?", (1, "u1")
    )
    assert c.fetchall() == [(1,)]
