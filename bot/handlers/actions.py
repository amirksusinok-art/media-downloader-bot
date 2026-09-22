import os
import uuid
from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile
from bot.config import TEMP_DIR
from bot.services.ffmpeg import FFmpegService
from bot.services.cleaner import remove_files
from bot.keyboards.media_kb import get_media_actions_kb, get_speed_kb

router = Router()

async def download_message_video(callback: CallbackQuery) -> str:
    """Скачивает видеофайл из сообщения Telegram для обработки."""
    msg = callback.message
    if not msg or not msg.video:
        raise ValueError("В сообщении нет видеофайла.")

    bot = callback.bot
    file_info = await bot.get_file(msg.video.file_id)
    local_path = str(TEMP_DIR / f"input_{uuid.uuid4().hex[:8]}.mp4")
    await bot.download_file(file_info.file_path, destination=local_path)
    return local_path

@router.callback_query(F.data.startswith("act:mp3:"))
async def on_extract_mp3(callback: CallbackQuery):
    await callback.answer("⏳ Извлекаю аудиодорожку...")
    input_file = None
    audio_file = None
    try:
        input_file = await download_message_video(callback)
        audio_file = await FFmpegService.extract_audio(input_file)

        await callback.message.reply_audio(
            audio=FSInputFile(audio_file),
            caption="🎵 Извлечённый MP3 звук"
        )
    except Exception as e:
        await callback.message.reply(f"❌ Ошибка извлечения звука: {str(e)[:150]}")
    finally:
        remove_files(input_file, audio_file)

@router.callback_query(F.data.startswith("act:cmp:"))
async def on_compress_video(callback: CallbackQuery):
    await callback.answer("⏳ Сжимаю видео...")
    input_file = None
    compressed_file = None
    try:
        input_file = await download_message_video(callback)
        compressed_file = await FFmpegService.compress_video(input_file, target_crf=28)

        old_size_mb = os.path.getsize(input_file) / (1024 * 1024)
        new_size_mb = os.path.getsize(compressed_file) / (1024 * 1024)

        media_id = callback.data.split(":")[-1]
        await callback.message.reply_video(
            video=FSInputFile(compressed_file),
            caption=f"🗜 **Сжатое видео**\nРазмер: {old_size_mb:.1f} МБ ➔ {new_size_mb:.1f} МБ",
            reply_markup=get_media_actions_kb(media_id),
            supports_streaming=True
        )
    except Exception as e:
        await callback.message.reply(f"❌ Ошибка сжатия видео: {str(e)[:150]}")
    finally:
        remove_files(input_file, compressed_file)

@router.callback_query(F.data.startswith("act:circle:"))
async def on_convert_circle(callback: CallbackQuery):
    await callback.answer("⭕ Конвертирую в кружочек (Video Note)...")
    input_file = None
    circle_file = None
    try:
        input_file = await download_message_video(callback)
        circle_file = await FFmpegService.convert_to_video_note(input_file)

        await callback.message.reply_video_note(
            video_note=FSInputFile(circle_file)
        )
    except Exception as e:
        await callback.message.reply(f"❌ Ошибка создания видеосообщения: {str(e)[:150]}")
    finally:
        remove_files(input_file, circle_file)

@router.callback_query(F.data.startswith("act:spd_menu:"))
async def on_open_speed_menu(callback: CallbackQuery):
    media_id = callback.data.split(":")[-1]
    await callback.message.edit_reply_markup(reply_markup=get_speed_kb(media_id))
    await callback.answer()

@router.callback_query(F.data.startswith("act:back:"))
async def on_back_to_main_menu(callback: CallbackQuery):
    media_id = callback.data.split(":")[-1]
    await callback.message.edit_reply_markup(reply_markup=get_media_actions_kb(media_id))
    await callback.answer()

@router.callback_query(F.data.startswith("spd:"))
async def on_apply_speed(callback: CallbackQuery):
    parts = callback.data.split(":")
    speed_val = float(parts[1])
    media_id = parts[2]

    await callback.answer(f"⚡ Устанавливаю скорость {speed_val}x...")
    input_file = None
    speed_file = None
    try:
        input_file = await download_message_video(callback)
        speed_file = await FFmpegService.change_speed(input_file, speed_val)

        await callback.message.reply_video(
            video=FSInputFile(speed_file),
            caption=f"⚡ Видео со скоростью **{speed_val}x**",
            reply_markup=get_media_actions_kb(media_id),
            supports_streaming=True
        )
    except Exception as e:
        await callback.message.reply(f"❌ Ошибка изменения скорости: {str(e)[:150]}")
    finally:
        remove_files(input_file, speed_file)

@router.callback_query(F.data == "info:cut")
async def on_cut_info(callback: CallbackQuery):
    await callback.answer(
        "✂️ Как обрезать видео:\nОтправьте команду:\n/cut 0:10 0:30 <ссылка>\nили ответьте /cut 0:10 0:30 на любое видео!",
        show_alert=True
    )
