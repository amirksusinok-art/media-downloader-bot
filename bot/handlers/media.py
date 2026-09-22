import re
import os
import asyncio
from aiogram import Router, F
from aiogram.types import Message, FSInputFile, InputMediaPhoto
from bot.config import MAX_FILE_SIZE_BYTES
from bot.database import get_cached_media, save_cached_media, increment_user_downloads, hash_url
from bot.downloaders.tiktok import TikTokDownloader
from bot.downloaders.ytdlp import YtDlpDownloader
from bot.services.ffmpeg import FFmpegService
from bot.services.cleaner import remove_files
from bot.keyboards.media_kb import get_media_actions_kb, get_travel_quality_kb

router = Router()

URL_REGEX = re.compile(r'https?://[^\s<>"]+', re.IGNORECASE)

tiktok_downloader = TikTokDownloader()
ytdlp_downloader = YtDlpDownloader()

# Временное хранилище пакетных ссылок (в памяти на время выбора качества)
PENDING_PACKS = {}

@router.message(F.text)
async def handle_text_urls(message: Message):
    text = message.text.strip()
    if text.startswith("/"):
        return

    found_urls = URL_REGEX.findall(text)
    if not found_urls:
        return

    # Если отправлено 2 или более ссылок — предлагаем пакетный режим
    if len(found_urls) >= 2:
        import uuid
        task_id = uuid.uuid4().hex[:8]
        PENDING_PACKS[task_id] = found_urls
        await message.answer(
            f"📦 **Обнаружено ссылок: {len(found_urls)} шт.**\n\n"
            "Хотите собрать их в дорожный пакет с оптимизацией для офлайн-просмотра?",
            reply_markup=get_travel_quality_kb(task_id),
            parse_mode="Markdown"
        )
        return

    # Обработка одной ссылки
    url = found_urls[0]
    user_id = message.from_user.id if message.from_user else 0
    url_h = hash_url(url)

    # 1. Проверяем кэш
    cached = await get_cached_media(url, "video")
    if cached:
        try:
            await message.answer_video(
                video=cached["file_id"],
                caption=f"🎬 **{cached.get('title', 'Видео')}**\n⚡ *Отправлено мгновенно из кэша*",
                reply_markup=get_media_actions_kb(url_h),
                parse_mode="Markdown",
                supports_streaming=True
            )
            await increment_user_downloads(user_id)
            return
        except Exception:
            pass  # Если кэшированный file_id устарел/недоступен, скачиваем заново

    status_msg = await message.answer("⏳ Загружаю медиа, пожалуйста, подождите...")
    await message.bot.send_chat_action(message.chat.id, "upload_video")

    # 2. Выбираем подходящий загрузчик
    downloader = tiktok_downloader if tiktok_downloader.can_handle(url) else ytdlp_downloader

    try:
        result = await downloader.download(url)
    except Exception as e:
        await status_msg.edit_text(f"❌ Не удалось скачать медиа: {str(e)[:200]}")
        return

    # 3. Отправка результата
    try:
        if result.media_type == "images":
            # Фотокарусель (например, из TikTok)
            await status_msg.edit_text("📸 Отправляю альбом фотографий...")
            media_group = [
                InputMediaPhoto(media=FSInputFile(p), caption=(result.title if i == 0 else ""))
                for i, p in enumerate(result.file_paths[:10])
            ]
            await message.answer_media_group(media=media_group)

            if result.music_path and os.path.exists(result.music_path):
                await message.answer_audio(
                    audio=FSInputFile(result.music_path),
                    caption=f"🎵 Фоновый трек: {result.author or 'TikTok'}"
                )

            await status_msg.delete()
            await increment_user_downloads(user_id)

        elif result.media_type == "video":
            main_file = result.get_main_file()
            if not main_file or not os.path.exists(main_file):
                await status_msg.edit_text("❌ Файл видео не найден после скачивания.")
                return

            file_size = os.path.getsize(main_file)

            # Проверка лимита Telegram (50 МБ)
            if file_size > MAX_FILE_SIZE_BYTES:
                await status_msg.edit_text("🗜 Видео больше 50 МБ, сжимаю для отправки в Telegram...")
                try:
                    compressed_file = await FFmpegService.compress_video(main_file, target_crf=32)
                    remove_files(main_file)
                    main_file = compressed_file
                    file_size = os.path.getsize(main_file)
                except Exception:
                    pass

            if file_size > MAX_FILE_SIZE_BYTES:
                # Если даже после сжатия видео слишком тяжелое — отправляем аудио
                await status_msg.edit_text("⚠️ Видео превышает 50 МБ. Извлекаю аудиодорожку в MP3...")
                audio_file = await FFmpegService.extract_audio(main_file)
                await message.answer_audio(
                    audio=FSInputFile(audio_file),
                    caption=f"🎵 {result.title}\n⚠️ Видео превысило лимит Telegram, поэтому отправлен звук."
                )
                remove_files(main_file, audio_file)
                await status_msg.delete()
                await increment_user_downloads(user_id)
                return

            caption_lines = [f"🎬 **{result.title}**"]
            if result.author:
                caption_lines.append(f"👤 *{result.author}*")

            sent_msg = await message.answer_video(
                video=FSInputFile(main_file),
                caption="\n".join(caption_lines),
                reply_markup=get_media_actions_kb(url_h),
                parse_mode="Markdown",
                supports_streaming=True,
                duration=result.duration or None,
                width=result.width or None,
                height=result.height or None
            )

            # Сохраняем file_id в кэш SQLite
            if sent_msg.video:
                await save_cached_media(
                    url=url,
                    file_id=sent_msg.video.file_id,
                    media_type="video",
                    title=result.title,
                    file_size=file_size
                )

            await status_msg.delete()
            await increment_user_downloads(user_id)

    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке файла: {str(e)[:200]}")
    finally:
        # Очистка локальных временных файлов
        remove_files(*result.file_paths, result.music_path)
