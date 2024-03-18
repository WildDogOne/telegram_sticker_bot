import sqlite3
from rich.console import Console
from rich.traceback import install
import logging
from rich.logging import RichHandler
from config.config import db
from pprint import pprint


# SQLite Connection
conn = sqlite3.connect(db)
c = conn.cursor()


# State Definition
STICKER, KEYWORDS, NEWPACKNAME, SELECTPACK, DELETEPACK, DELETESTICKER = range(6)


# Rich Console

console = Console()

install(show_locals=True)

# Logging Handler
FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO",
    format=FORMAT,
    datefmt="[%X]",
    handlers=[
        RichHandler(
            rich_tracebacks=True,
            # locals_max_length=None,
            # locals_max_string=None,
            # tracebacks_word_wrap=False,
            # show_path=True,
        )
    ],
)

logger = logging.getLogger("rich")
