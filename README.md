# Telegram Sticker Bot

A Telegram bot for storing, managing, and retrieving stickers with ease. Built using the `python-telegram-bot` library.

## Features

- **Store stickers**: Send stickers to the bot and assign keywords for easy retrieval.
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

- Python 3.x+ (Tested on 3.13 and 3.14)
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
   > The bot uses relative paths for `stickers.db`, `config/config.py`, `./data`, and `./deepbooru`.
   > If running as a service (e.g., systemd), ensure the working directory is set to the repository root.

## Optional Features

- **Advanced tagging**: Install `requirements_tagger.txt` to enable optional tagging features (e.g., `tagger.py`).
- **Development dependencies**: Install `requirements-dev.txt` for testing and development tools.