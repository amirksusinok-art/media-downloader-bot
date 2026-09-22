import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
import aiosqlite
from bot.config import DB_PATH

def hash_url(url: str) -> str:
    """Нормализует и хэширует URL для быстрого поиска."""
    clean_url = url.strip().split("?")[0].rstrip("/")
    return hashlib.sha256(clean_url.encode("utf-8")).hexdigest()

async def init_db():
    """Инициализация таблиц базы данных."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                downloads_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS media_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url_hash TEXT NOT NULL,
                original_url TEXT NOT NULL,
                file_id TEXT NOT NULL,
                media_type TEXT NOT NULL,
                title TEXT,
                file_size INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("CREATE INDEX IF NOT EXISTS idx_url_hash ON media_cache(url_hash)")
        await db.commit()

async def register_user(user_id: int, username: Optional[str], first_name: Optional[str]):
    """Регистрирует или обновляет активность пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, first_name, last_active)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_active = CURRENT_TIMESTAMP
        """, (user_id, username, first_name))
        await db.commit()

async def increment_user_downloads(user_id: int):
    """Увеличивает счетчик загрузок пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users SET downloads_count = downloads_count + 1 WHERE user_id = ?
        """, (user_id,))
        await db.commit()

async def get_cached_media(url: str, media_type: str = "video") -> Optional[Dict[str, Any]]:
    """Получает закэшированный file_id по URL."""
    url_h = hash_url(url)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT file_id, media_type, title, file_size
            FROM media_cache
            WHERE url_hash = ? AND media_type = ?
            ORDER BY id DESC LIMIT 1
        """, (url_h, media_type)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
    return None

async def save_cached_media(url: str, file_id: str, media_type: str, title: Optional[str] = None, file_size: int = 0):
    """Сохраняет file_id в кэш."""
    url_h = hash_url(url)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO media_cache (url_hash, original_url, file_id, media_type, title, file_size)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (url_h, url, file_id, media_type, title, file_size))
        await db.commit()
