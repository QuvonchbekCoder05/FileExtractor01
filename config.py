import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)  # Vaqtinchalik fayllar uchun papka yaratish
