import time
import uuid
import os
from pathlib import Path
from typing import Optional, Dict, Any
from bot.config import WEB_BASE_URL
from bot.services.cleaner import remove_files

class WebDownloadManager:
    """
    Управляет временными ссылками на скачивание тяжелых файлов (>50 МБ)
    через встроенный веб-сервер aiohttp.
    """
    def __init__(self, max_lifetime_seconds: int = 3600):
        # token -> dict(file_path, filename, expires_at, size_mb)
        self._downloads: Dict[str, Dict[str, Any]] = {}
        self.max_lifetime = max_lifetime_seconds

    def cleanup_expired(self):
        """Удаляет просроченные файлы (старше 1 часа)."""
        now = time.time()
        expired_tokens = [
            t for t, data in self._downloads.items()
            if now > data["expires_at"]
        ]
        for t in expired_tokens:
            data = self._downloads.pop(t, None)
            if data and data.get("file_path"):
                remove_files(data["file_path"])

    def create_download_link(self, file_path: str, filename: str) -> str:
        """Создает временную ссылку на скачивание и возвращает полный URL."""
        self.cleanup_expired()
        token = uuid.uuid4().hex
        size_mb = os.path.getsize(file_path) / (1024 * 1024) if os.path.exists(file_path) else 0

        self._downloads[token] = {
            "file_path": file_path,
            "filename": filename,
            "expires_at": time.time() + self.max_lifetime,
            "size_mb": size_mb
        }

        return f"{WEB_BASE_URL}/download/{token}"

    def get_download(self, token: str) -> Optional[Dict[str, Any]]:
        """Получает информацию о файле по токену, если ссылка действительна."""
        self.cleanup_expired()
        data = self._downloads.get(token)
        if not data:
            return None

        file_path = data.get("file_path")
        if not file_path or not os.path.exists(file_path):
            self._downloads.pop(token, None)
            return None

        return data

    def complete_download(self, token: str):
        """Удаляет файл сразу после успешного скачивания браузером."""
        data = self._downloads.pop(token, None)
        if data and data.get("file_path"):
            remove_files(data["file_path"])

web_download_manager = WebDownloadManager(max_lifetime_seconds=3600)
