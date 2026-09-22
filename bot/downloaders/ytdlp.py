import asyncio
import os
import uuid
from typing import Optional
import yt_dlp
from bot.downloaders.base import BaseDownloader, MediaResult
from bot.config import TEMP_DIR, COOKIES_PATH

class YtDlpDownloader(BaseDownloader):
    def can_handle(self, url: str) -> bool:
        # Универсальный загрузчик: пытается обработать любую валидную ссылку
        lower = url.lower()
        supported = [
            "youtube.com", "youtu.be",
            "instagram.com", "instagr.am",
            "twitter.com", "x.com",
            "reddit.com", "v.redd.it",
            "pinterest.com", "pin.it",
            "vk.com", "vkvideo.ru",
            "twitch.tv",
            "likee.video", "likee.com"
        ]
        return any(domain in lower for domain in supported) or lower.startswith("http")

    def _sync_download(self, url: str, target_quality: Optional[str] = None) -> MediaResult:
        file_prefix = f"media_{uuid.uuid4().hex[:8]}"
        outtmpl = str(TEMP_DIR / f"{file_prefix}.%(ext)s")

        # Настройка формата в зависимости от запрошенного качества
        if target_quality == "480p":
            fmt = "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best[height<=480]/best"
        elif target_quality == "720p":
            fmt = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]/best"
        else:
            # По умолчанию: до 1080p, чтобы не превысить лимиты Telegram
            fmt = "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"

        ydl_opts = {
            "format": fmt,
            "outtmpl": outtmpl,
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "writethumbnail": False,
            "socket_timeout": 30,
            "postprocessors": [{
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            }],
        }

        # Если найден файл cookies.txt, используем его для обхода блокировок
        if COOKIES_PATH.exists() and COOKIES_PATH.is_file():
            ydl_opts["cookiefile"] = str(COOKIES_PATH)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise ValueError("Не удалось получить информацию о медиа.")

            title = info.get("title", "Video")
            author = info.get("uploader") or info.get("channel") or info.get("creator")
            duration = info.get("duration", 0)
            width = info.get("width")
            height = info.get("height")

            # Находим итоговый скачанный файл
            # yt-dlp может сохранить с расширением .mp4
            expected_file = str(TEMP_DIR / f"{file_prefix}.mp4")
            if not os.path.exists(expected_file):
                # Ищем среди файлов с данным префиксом
                matched = list(TEMP_DIR.glob(f"{file_prefix}.*"))
                if matched:
                    expected_file = str(matched[0])
                else:
                    raise FileNotFoundError("Файл после скачивания не найден на диске.")

            return MediaResult(
                media_type="video",
                file_paths=[expected_file],
                title=title,
                author=author,
                duration=int(duration) if duration else 0,
                original_url=url,
                width=width,
                height=height
            )

    async def download(self, url: str, target_quality: Optional[str] = None) -> MediaResult:
        """Асинхронная обертка для синхронного yt-dlp."""
        return await asyncio.to_thread(self._sync_download, url, target_quality)
