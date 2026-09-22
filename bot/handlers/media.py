import re
import os
import asyncio
from aiogram import Router, F
from aiogram.types import Message, FSInputFile, InputMediaPhoto
from bot.config import MAX_FILE_SIZE_BYTES
from bot.database import get_cached_media, save_cached_media, increment_user_downloads, hash_url, get_user_watermark
from bot.downloaders.tiktok import TikTokDownloader
from bot.downloaders.ytdlp import YtDlpDownloader
from bot.services.ffmpeg import FFmpegService
from bot.services.cleaner import remove_files
from bot.services.queue import ffmpeg_queue
from bot.services.web_downloads import web_download_manager
from bot.keyboards.media_kb import get_media_actions_kb, get_travel_quality_kb, get_direct_download_kb

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
        result = await ffmpeg_queue.run(downloader.download, url, status_msg=status_msg)
    except Exception as e:
        err_text = str(e)
        if "Sign in to confirm you’re not a bot" in err_text or "Sign in to confirm you're not a bot" in err_text:
            await status_msg.edit_text(
                "⚠️ **YouTube заблокировал серверный запрос (защита от ботов).**\n\n"
                "Для скачивания этого видео боту нужен файл `cookies.txt`.\n\n"
                "👉 **Как решить за 20 секунд:**\n"
                "1. Установите бесплатное расширение [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc).\n"
                "2. Откройте youtube.com и нажмите *«Export»* в расширении.\n"
                "3. **Просто отправьте полученный файл `cookies.txt` прямо в этот чат!**\n\n"
                "Бот автоматически активирует его и сможет скачивать любые видео с YouTube.",
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
        else:
            await status_msg.edit_text(f"❌ Не удалось скачать медиа: {err_text[:250]}")
        return

    # 3. Отправка результата
    is_web_download = False
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

            # Проверяем, включен ли автоматический водяной знак
            wm_text, is_wm_auto = await get_user_watermark(user_id)
            if is_wm_auto and wm_text:
                try:
                    await status_msg.edit_text("🏷 Накладываю ваш водяной знак...")
                    wm_file = await ffmpeg_queue.run(FFmpegService.apply_watermark, main_file, wm_text, status_msg=status_msg)
                    remove_files(main_file)
                    main_file = wm_file
                    result.file_paths = [main_file]
                except Exception:
                    pass

            file_size = os.path.getsize(main_file)

            # Проверка лимита Telegram (50 МБ)
            if file_size > MAX_FILE_SIZE_BYTES:
                await status_msg.edit_text("🗜 Видео больше 50 МБ, сжимаю для отправки в Telegram...")
                try:
                    compressed_file = await ffmpeg_queue.run(
                        FFmpegService.compress_video, main_file, target_crf=32, status_msg=status_msg
                    )
                    if os.path.getsize(compressed_file) < file_size:
                        remove_files(main_file)
                        main_file = compressed_file
                        file_size = os.path.getsize(main_file)
                    else:
                        remove_files(compressed_file)
                except Exception:
                    pass

            # Если файл ВСЕ ЕЩЕ больше 50 МБ -> генерируем прямую веб-ссылку на скачивание!
            if file_size > MAX_FILE_SIZE_BYTES:
                size_mb = file_size / (1024 * 1024)
                await status_msg.edit_text(
                    f"⚠️ **Видео весит {size_mb:.1f} МБ** (превышает лимит Telegram 50 МБ).\n\n"
                    f"🌐 Я сгенерировал **прямую ссылку для скачивания в браузере** на максимальной скорости!\n"
                    f"*(Ссылка действительна 1 час и удалится сразу после скачивания)*",
                    reply_markup=get_direct_download_kb(
                        web_download_manager.create_download_link(main_file, f"{result.title}.mp4"),
                        size_mb
                    ),
                    parse_mode="Markdown"
                )
                is_web_download = True
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
        # Если файл передан в веб-менеджер скачивания, не удаляем его сразу
        if not is_web_download:
            remove_files(*result.file_paths, result.music_path)
