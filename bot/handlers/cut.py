import os
import re
import uuid
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from bot.config import TEMP_DIR
from bot.services.ffmpeg import FFmpegService
from bot.services.cleaner import remove_files
from bot.downloaders.tiktok import TikTokDownloader
from bot.downloaders.ytdlp import YtDlpDownloader

router = Router()

URL_REGEX = re.compile(r'https?://[^\s<>"]+', re.IGNORECASE)

tiktok_downloader = TikTokDownloader()
ytdlp_downloader = YtDlpDownloader()

@router.message(Command("cut"))
async def cmd_cut(message: Message):
    """
    Команда /cut:
    Вариант 1: /cut 0:10 0:35 https://...
    Вариант 2: /cut 0:10 0:35 (в ответ на сообщение с видео)
    """
    text = message.text or ""
    parts = text.split()

    if len(parts) < 3:
        await message.answer(
            "✂️ **Использование команды /cut:**\n\n"
            "1. По ссылке:\n`/cut 0:10 0:25 https://vt.tiktok.com/...`\n\n"
            "2. В ответ на видео:\nОтветьте на видео командой `/cut 0:10 0:25`",
            parse_mode="Markdown"
        )
        return

    start_time = parts[1]
    end_time = parts[2]

    # Проверяем, есть ли ссылка в команде
    urls = URL_REGEX.findall(text)
    input_video = None
    trimmed_video = None

    status_msg = await message.answer(f"⏳ Вырезаю фрагмент с {start_time} по {end_time}...")

    try:
        if urls:
            url = urls[0]
            downloader = tiktok_downloader if tiktok_downloader.can_handle(url) else ytdlp_downloader
            res = await downloader.download(url)
            if res.media_type != "video":
                await status_msg.edit_text("❌ По ссылке не найдено видео для обрезки.")
                remove_files(*res.file_paths, res.music_path)
                return
            input_video = res.get_main_file()

        elif message.reply_to_message and message.reply_to_message.video:
            reply_video = message.reply_to_message.video
            file_info = await message.bot.get_file(reply_video.file_id)
            input_video = str(TEMP_DIR / f"reply_input_{uuid.uuid4().hex[:8]}.mp4")
            await message.bot.download_file(file_info.file_path, destination=input_video)

        else:
            await status_msg.edit_text("❌ Укажите ссылку на видео или ответьте командой на сообщение с видео!")
            return

        # Обрезаем через FFmpeg
        trimmed_video = await FFmpegService.trim_video(input_video, start_time, end_time)

        await message.answer_video(
            video=FSInputFile(trimmed_video),
            caption=f"✂️ Отрезок: **{start_time} ➔ {end_time}**",
            parse_mode="Markdown",
            supports_streaming=True
        )
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка обрезки: {str(e)[:150]}")
    finally:
        remove_files(input_video, trimmed_video)
