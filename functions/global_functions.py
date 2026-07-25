import sqlite3
from rich.console import Console
from rich.traceback import install
import logging
from rich.logging import RichHandler
from config.config import db


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
        )
    ],
)

logger = logging.getLogger("rich")
