import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

DATA_DIR = BASE_DIR / os.getenv("DATA_DIR", "data")
TEMP_DIR = BASE_DIR / os.getenv("TEMP_DIR", "data/temp")
DB_PATH = DATA_DIR / "bot.db"
COOKIES_PATH = DATA_DIR / "cookies.txt"

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Базовый URL для прямых ссылок (Render предоставляет RENDER_EXTERNAL_URL)
WEB_BASE_URL = os.getenv("RENDER_EXTERNAL_URL", os.getenv("WEB_BASE_URL", "http://localhost:10000")).rstrip("/")

# Создаем необходимые папки
DATA_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Если задана переменная окружения YOUTUBE_COOKIES (например, в Render Dashboard), сохраняем её в data/cookies.txt
env_cookies = os.getenv("YOUTUBE_COOKIES", "").strip()
if env_cookies:
    try:
        with open(COOKIES_PATH, "w", encoding="utf-8") as f:
            f.write(env_cookies)
    except Exception:
        pass
