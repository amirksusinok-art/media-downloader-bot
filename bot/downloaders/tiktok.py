import os
import uuid
import aiohttp
from typing import Optional, List
from bot.downloaders.base import BaseDownloader, MediaResult
from bot.config import TEMP_DIR
from bot.services.cleaner import remove_files

class TikTokDownloader(BaseDownloader):
    def can_handle(self, url: str) -> bool:
        lower = url.lower()
        return any(domain in lower for domain in ["tiktok.com", "vt.tiktok.com", "vm.tiktok.com"])

    async def download(self, url: str, target_quality: Optional[str] = None) -> MediaResult:
        """Скачивание видео или фотокарусели из TikTok без водяных знаков через потоковую загрузку."""
        endpoints = [
            "https://www.tikwm.com/api/",
            "https://api.tikwm.com/api/"
        ]

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Referer": "https://www.tiktok.com/",
            "Accept": "application/json, text/plain, */*"
        }

        timeout = aiohttp.ClientTimeout(total=60, connect=15)

        last_error = "Не удалось связаться с сервером TikTok"

        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            for api_url in endpoints:
                try:
                    async with session.post(api_url, data={"url": url, "hd": 1}) as resp:
                        if resp.status != 200:
                            continue

                        res_json = await resp.json()
                        if res_json.get("code") != 0 or "data" not in res_json:
                            msg = res_json.get("msg", "Ошибка API TikTok")
                            last_error = f"TikTok API: {msg}"
                            continue

                        data = res_json["data"]
                        title = data.get("title") or "TikTok Media"
                        author = data.get("author", {}).get("nickname") or data.get("author", {}).get("unique_id") or "TikTok User"
                        duration = data.get("duration", 0)

                        # 1. Проверяем, фотокарусель ли это
                        images = data.get("images")
                        if images and isinstance(images, list) and len(images) > 0:
                            image_paths = []
                            unique_id = uuid.uuid4().hex[:8]

                            for idx, img_url in enumerate(images):
                                img_path = str(TEMP_DIR / f"tiktok_{unique_id}_{idx}.jpg")
                                async with session.get(img_url) as img_resp:
                                    if img_resp.status == 200:
                                        with open(img_path, "wb") as f:
                                            async for chunk in img_resp.content.iter_chunked(65536):
                                                f.write(chunk)
                                        image_paths.append(img_path)

                            # Скачиваем фоновый трек
                            music_path = None
                            music_url = data.get("music") or data.get("play")
                            if music_url:
                                music_path = str(TEMP_DIR / f"tiktok_{unique_id}_music.mp3")
                                async with session.get(music_url) as m_resp:
                                    if m_resp.status == 200:
                                        with open(music_path, "wb") as f:
                                            async for chunk in m_resp.content.iter_chunked(65536):
                                                f.write(chunk)

                            return MediaResult(
                                media_type="images",
                                file_paths=image_paths,
                                title=title,
                                author=author,
                                original_url=url,
                                music_path=music_path
                            )

                        # 2. Скачивание видео (перебираем hdplay, play, wmplay)
                        candidate_urls = []
                        if target_quality != "480p" and data.get("hdplay"):
                            candidate_urls.append(data["hdplay"])
                        if data.get("play"):
                            candidate_urls.append(data["play"])
                        if data.get("wmplay"):
                            candidate_urls.append(data["wmplay"])

                        for vid_url in candidate_urls:
                            if not vid_url.startswith("http"):
                                vid_url = "https://www.tikwm.com" + vid_url

                            video_path = str(TEMP_DIR / f"tiktok_{uuid.uuid4().hex[:8]}.mp4")
                            try:
                                async with session.get(vid_url) as v_resp:
                                    if v_resp.status == 200:
                                        with open(video_path, "wb") as f:
                                            async for chunk in v_resp.content.iter_chunked(65536):
                                                f.write(chunk)

                                        if os.path.exists(video_path) and os.path.getsize(video_path) > 1000:
                                            return MediaResult(
                                                media_type="video",
                                                file_paths=[video_path],
                                                title=title,
                                                author=author,
                                                duration=duration,
                                                original_url=url
                                            )
                                        else:
                                            remove_files(video_path)
                            except Exception:
                                remove_files(video_path)
                                continue

                except Exception as e:
                    last_error = str(e)
                    continue

        # Если прямое API не сработало, возвращаем понятную ошибку
        raise RuntimeError(f"Не удалось загрузить видео из TikTok ({last_error}). Проверьте, не является ли видео приватным или удаленным.")
