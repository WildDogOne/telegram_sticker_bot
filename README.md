# README

## Telegram Sticker Bot

This Python script is for a Telegram bot that allows users to store and manage their stickers. The bot uses the `telegram-python-bot` library for interacting with the Telegram API.

## Current Features

- Store stickers by sending them to the bot, and adding keywords to them
- Retrieve stickers by using the bot inline in any chat
- Fuzzy Search on keywords during inline retrieval
- Store stickers in packs for easier use


| Command         | Description                                                                                           |
| --------------- | ----------------------------------------------------------------------------------------------------- |
| /start          | Start the bot interaction, usually this is enforced for every user when they first chat with the bot. |
| /help           | Get help information                                                                                  |
| /pack           | Set Pack to use                                                                                       |
| /packs          | Get your packs                                                                                        |
| /delete_sticker | Delete a sticker from the current pack                                                                |
| /newpack        | New pack                                                                                              |
| /delpack        | Remove a pack                                                                                         |
| /cancel         | Cancel action                                                                                         |

#### Installation

### Create Config

Copy the config.py.example to ./config/config.py  
Edit it with at least your Bot token.


| Variable        | Content                                                                                               |
| --------------- | ----------------------------------------------------------------------------------------------------- |
| token           | Telegram Bot Token                                                                                    |
| db              | Sticker DB Name/Location                                                                              |
| owner_id        | The ID of the bot owner, only really necessary for troubleshooting                                    |
| default_user_id | A default user ID which will be used if the user who is using the bot has not registered with the bot |
| botname         | The name of the bot                                                                                   |

### Install Requirements

1. Python3
2. pip install -r requirements.txt
3. You don't necessarily need the tagger requirements unless you want to run tagger.py (more advanced and not needed)

