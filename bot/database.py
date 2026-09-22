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
                watermark_text TEXT DEFAULT NULL,
                watermark_auto INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Миграция колонок, если база уже создана
        try:
            await db.execute("ALTER TABLE users ADD COLUMN watermark_text TEXT DEFAULT NULL")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN watermark_auto INTEGER DEFAULT 0")
        except Exception:
            pass

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

async def set_user_watermark(user_id: int, text: Optional[str]):
    """Устанавливает или сбрасывает текст водяного знака пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, watermark_text)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                watermark_text = excluded.watermark_text
        """, (user_id, text))
        await db.commit()

async def toggle_watermark_auto(user_id: int) -> bool:
    """Переключает автоматическое наложение водяного знака."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT watermark_auto FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            current = row[0] if row and row[0] is not None else 0
        new_val = 0 if current == 1 else 1
        await db.execute("""
            INSERT INTO users (user_id, watermark_auto)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                watermark_auto = excluded.watermark_auto
        """, (user_id, new_val))
        await db.commit()
        return new_val == 1

async def get_user_watermark(user_id: int) -> tuple[Optional[str], bool]:
    """Возвращает (watermark_text, is_auto_enabled) для пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT watermark_text, watermark_auto FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                text = row[0]
                is_auto = bool(row[1]) if row[1] is not None else False
                return text, is_auto
    return None, False
