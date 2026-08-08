# Telegram Sticker Bot

A Telegram bot for storing, managing, and retrieving stickers with ease. Built using the `python-telegram-bot` library.

## Features

- **Store stickers**: Send stickers to the bot and assign keywords for easy retrieval.
- **Auto-tagging**: New stickers are automatically tagged in the background using two models — one for anime art, one for furry art — improving fuzzy search without touching your own keywords.
- **Inline retrieval**: Use the bot inline in any chat to search and send stickers.
- **Fuzzy search**: Search stickers using partial or approximate keywords.
- **Pack management**: Organize stickers into packs for better organization.

## Commands

| Command         | Description                                                                 |
|-----------------|-----------------------------------------------------------------------------|
| `/start`        | Start interacting with the bot.                                              |
| `/help`         | Get help information.                                                        |
| `/pack`         | Set the active pack.                                                         |
| `/packs`        | List all your packs.                                                         |
| `/newpack`      | Create a new pack.                                                           |
| `/delpack`      | Delete a pack.                                                               |
| `/delete_sticker` | Delete a sticker from the current pack.                                    |
| `/cancel`       | Cancel the current action.                                                   |

## Setup

### Prerequisites

- Python 3.12 (pinned via `.python-version` — the auto-tagging stack (`torch`/`onnxruntime`) doesn't yet support the newest CPython releases)
- A Telegram bot token (obtain from [@BotFather](https://t.me/BotFather))

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository_url>
   cd telegram_sticker_bot
   ```

2. **Configure the bot**:
   - Copy `config.py.example` to `config/config.py`.
   - Edit `config/config.py` with your Telegram bot token and other settings:
     
     | Variable        | Description                                                                 |
     |-----------------|-----------------------------------------------------------------------------|
     | `token`         | Telegram Bot Token (required).                                               |
     | `db`            | Path to the SQLite database (default: `stickers.db`).                       |
     | `owner_id`      | Bot owner's Telegram ID (optional, for troubleshooting).                    |
     | `default_user_id` | Fallback user ID (optional).                                               |
     | `botname`       | Name of the bot (optional).                                                 |

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the bot**:
   ```bash
   python main.py
   ```

   > **Note**: Always run the bot from the repository root.
   > The bot uses relative paths for `stickers.db`, `config/config.py`, and `./data`.
   > If running as a service (e.g., systemd), ensure the working directory is set to the repository root.
   > The auto-tagging models (~1-2GB total) download on first use into the standard Hugging Face cache (`~/.cache/huggingface/hub`), not into the repo.
   > If you hit Hugging Face's anonymous-download rate limit, set the `HF_TOKEN` environment variable to an [access token](https://huggingface.co/settings/tokens) before running the bot or `tagger.py`. Without it, downloads fall back to unauthenticated.

## Optional Features

- **Development dependencies**: Install `requirements-dev.txt` for testing and development tools.

## Backfilling tags

`tagger.py` runs the same auto-tagging used on new stickers against any existing sticker still missing a tag (e.g. ones saved before this feature existed):

```bash
python tagger.py
```