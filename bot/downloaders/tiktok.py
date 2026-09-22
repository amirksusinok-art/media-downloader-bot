import os
import uuid
import aiohttp
import asyncio
from typing import Optional, List
from bot.downloaders.base import BaseDownloader, MediaResult
from bot.config import TEMP_DIR

class TikTokDownloader(BaseDownloader):
    def can_handle(self, url: str) -> bool:
        lower = url.lower()
        return any(domain in lower for domain in ["tiktok.com", "vt.tiktok.com", "vm.tiktok.com"])

    async def download(self, url: str, target_quality: Optional[str] = None) -> MediaResult:
        """Скачивание видео или фотокарусели из TikTok без водяных знаков."""
        api_url = "https://www.tikwm.com/api/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(api_url, data={"url": url, "hd": 1}) as resp:
                if resp.status == 200:
                    res_json = await resp.json()
                    if res_json.get("code") == 0 and "data" in res_json:
                        data = res_json["data"]
                        title = data.get("title", "TikTok Media")
                        author = data.get("author", {}).get("nickname", "TikTok User")
                        duration = data.get("duration", 0)

                        # Проверяем, фотокарусель ли это
                        images = data.get("images")
                        if images and isinstance(images, list) and len(images) > 0:
                            # Это фото-карусель
                            image_paths = []
                            unique_id = uuid.uuid4().hex[:8]

                            # Скачиваем все картинки
                            for idx, img_url in enumerate(images):
                                img_path = str(TEMP_DIR / f"tiktok_{unique_id}_{idx}.jpg")
                                async with session.get(img_url) as img_resp:
                                    if img_resp.status == 200:
                                        content = await img_resp.read()
                                        with open(img_path, "wb") as f:
                                            f.write(content)
                                        image_paths.append(img_path)

                            # Скачиваем фоновый трек
                            music_path = None
                            music_url = data.get("music") or data.get("play")
                            if music_url:
                                music_path = str(TEMP_DIR / f"tiktok_{unique_id}_music.mp3")
                                async with session.get(music_url) as m_resp:
                                    if m_resp.status == 200:
                                        m_content = await m_resp.read()
                                        with open(music_path, "wb") as f:
                                            f.write(m_content)

                            return MediaResult(
                                media_type="images",
                                file_paths=image_paths,
                                title=title,
                                author=author,
                                original_url=url,
                                music_path=music_path
                            )

                        # Иначе обычное видео без водяных знаков
                        video_url = data.get("play") or data.get("wmplay")
                        if video_url:
                            if not video_url.startswith("http"):
                                video_url = "https://www.tikwm.com" + video_url

                            video_path = str(TEMP_DIR / f"tiktok_{uuid.uuid4().hex[:8]}.mp4")
                            async with session.get(video_url) as v_resp:
                                if v_resp.status == 200:
                                    content = await v_resp.read()
                                    with open(video_path, "wb") as f:
                                        f.write(content)

                                    return MediaResult(
                                        media_type="video",
                                        file_paths=[video_path],
                                        title=title,
                                        author=author,
                                        duration=duration,
                                        original_url=url
                                    )

        # Если TikWM не сработал — фолбэк на yt-dlp
        from bot.downloaders.ytdlp import YtDlpDownloader
        fallback = YtDlpDownloader()
        return await fallback.download(url, target_quality=target_quality)
