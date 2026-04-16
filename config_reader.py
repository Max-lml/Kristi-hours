import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
    # Путь к ключу Google
    GOOGLE_KEY_PATH = "service_account.json"

config = Config()