import asyncio
import os
import uuid
from pathlib import Path
from typing import Tuple, Optional
from bot.config import TEMP_DIR

class FFmpegService:
    @staticmethod
    async def _run_command(*args) -> Tuple[int, str, str]:
        """Запуск команды ffmpeg асинхронно."""
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        return proc.returncode, stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace")

    @classmethod
    async def extract_audio(cls, video_path: str) -> str:
        """Извлечение MP3-аудио из видео."""
        out_path = str(TEMP_DIR / f"audio_{uuid.uuid4().hex[:8]}.mp3")
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vn",
            "-acodec", "libmp3lame",
            "-q:a", "2",
            out_path
        ]
        rc, _, err = await cls._run_command(*cmd)
        if rc != 0 or not os.path.exists(out_path):
            raise RuntimeError(f"Ошибка извлечения аудио: {err}")
        return out_path

    @classmethod
    async def change_speed(cls, video_path: str, speed: float) -> str:
        """Изменение скорости видео (0.5x - 2.0x)."""
        out_path = str(TEMP_DIR / f"speed_{uuid.uuid4().hex[:8]}.mp4")
        v_pts = 1.0 / speed
        filter_str = f"[0:v]setpts={v_pts:.4f}*PTS[v];[0:a]atempo={speed:.2f}[a]"

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-filter_complex", filter_str,
            "-map", "[v]",
            "-map", "[a]",
            "-c:v", "libx264",
            "-preset", "faster",
            "-crf", "24",
            "-c:a", "aac",
            "-movflags", "+faststart",
            out_path
        ]
        rc, _, err = await cls._run_command(*cmd)
        if rc != 0 or not os.path.exists(out_path):
            raise RuntimeError(f"Ошибка изменения скорости: {err}")
        return out_path

    @classmethod
    async def compress_video(cls, video_path: str, target_crf: int = 28) -> str:
        """Сжатие видео с помощью H.264 + faststart."""
        out_path = str(TEMP_DIR / f"compressed_{uuid.uuid4().hex[:8]}.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", str(target_crf),
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            out_path
        ]
        rc, _, err = await cls._run_command(*cmd)
        if rc != 0 or not os.path.exists(out_path):
            raise RuntimeError(f"Ошибка сжатия видео: {err}")
        return out_path

    @classmethod
    async def convert_to_video_note(cls, video_path: str) -> str:
        """Конвертация в формат круглого видеосообщения Telegram (1:1, до 60 сек)."""
        out_path = str(TEMP_DIR / f"videonote_{uuid.uuid4().hex[:8]}.mp4")
        # Обрезка до квадрата по центру и масштабирование в 480x480
        cmd = [
            "ffmpeg", "-y",
            "-t", "60",
            "-i", video_path,
            "-vf", "crop=min(iw\\,ih):min(iw\\,ih),scale=480:480:flags=lanczos",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "26",
            "-c:a", "aac",
            "-b:a", "64k",
            "-movflags", "+faststart",
            out_path
        ]
        rc, _, err = await cls._run_command(*cmd)
        if rc != 0 or not os.path.exists(out_path):
            raise RuntimeError(f"Ошибка конвертации в кружочек: {err}")
        return out_path

    @classmethod
    async def trim_video(cls, video_path: str, start_time: str, end_time: str) -> str:
        """Быстрая обрезка видео по таймкодам."""
        out_path = str(TEMP_DIR / f"trimmed_{uuid.uuid4().hex[:8]}.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-ss", start_time,
            "-to", end_time,
            "-i", video_path,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-movflags", "+faststart",
            out_path
        ]
        rc, _, err = await cls._run_command(*cmd)
        if rc != 0 or not os.path.exists(out_path):
            raise RuntimeError(f"Ошибка обрезки видео: {err}")
        return out_path
