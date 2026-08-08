from telegram import Bot
from config.config import token, db
from functions.global_functions import logger
from functions.tagging_functions import generate_tags
import argparse
import sqlite3
from pprint import pprint
import asyncio


async def download_sticker(bot_token, file_id, filename):
    bot = Bot(bot_token)
    file = await bot.get_file(file_id)
    await file.download_to_drive(filename)


def get_stickers():
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute(
        "SELECT file_id, CLIP FROM stickers WHERE CLIP IS NULL",
    )
    results = c.fetchall()
    conn.close()
    stickers = []
    for x in results:
        stickers.append(x[0])
    print(results)
    return stickers


def clear_clip_tags():
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute("UPDATE stickers SET CLIP = NULL")
    conn.commit()
    conn.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Auto-tag stickers still missing a CLIP tag")
    parser.add_argument(
        "-d",
        "--delete",
        action="store_true",
        help="Clear all existing CLIP tags first, then retag every sticker (instead of just untagged ones)",
    )
    return parser.parse_args()


async def clipit():
    print("Function executed")
    stickers = get_stickers()
    pprint(stickers)
    for sticker in stickers:
        await download_sticker(token, sticker, f"./data/{sticker}.webp")


def main():
    args = parse_args()
    if args.delete:
        clear_clip_tags()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(clipit())
    finally:
        loop.close()

    conn = sqlite3.connect(db)
    c = conn.cursor()
    stickers = get_stickers()
    for sticker in stickers:
        try:
            tags = generate_tags(f"./data/{sticker}.webp")
            print(tags)
            c.execute(
                """
                Update stickers
                Set CLIP = ?
                Where file_id = ?
                """,
                (tags, sticker),
            )
            conn.commit()
        except Exception as e:
            print(e)
    conn.close()


if __name__ == "__main__":
    main()
