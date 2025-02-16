import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

BOT_COMMANDS = [
    {'command': 'start', 'description': '🚀Початок роботи / Get started🔥'},
]
