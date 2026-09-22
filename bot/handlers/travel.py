import os
import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from bot.handlers.media import PENDING_PACKS, tiktok_downloader, ytdlp_downloader
from bot.services.cleaner import remove_files
from bot.keyboards.media_kb import get_media_actions_kb
from bot.database import hash_url

router = Router()

@router.message(Command("travel"))
@router.message(Command("pack"))
async def cmd_travel(message: Message):
    await message.answer(
        "✈️ **Режим «В дорогу / Самолёт»**\n\n"
        "Отправьте мне список ссылок (каждая с новой строки или через пробел).\n"
        "Я сожму и оптимизирую их кодеками с флагом `+faststart` для мгновенного офлайн-просмотра!",
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("pkg:cancel:"))
async def on_cancel_pack(callback: CallbackQuery):
    task_id = callback.data.split(":")[-1]
    PENDING_PACKS.pop(task_id, None)
    await callback.message.edit_text("❌ Формирование пакета отменено.")
    await callback.answer()

@router.callback_query(F.data.startswith("pkg:"))
async def on_start_pack(callback: CallbackQuery):
    parts = callback.data.split(":")
    quality = parts[1]  # 480p или 720p
    task_id = parts[2]

    urls = PENDING_PACKS.pop(task_id, None)
    if not urls:
        await callback.answer("⚠️ Список ссылок устарел. Отправьте ссылки заново.", show_alert=True)
        return

    total = len(urls)
    status_msg = await callback.message.edit_text(
        f"📦 **Сборка дорожного пакета ({quality})...**\n⏳ Подготовка (0 из {total})",
        parse_mode="Markdown"
    )
    await callback.answer()

    for idx, url in enumerate(urls, 1):
        try:
            await status_msg.edit_text(
                f"📦 **Сборка дорожного пакета ({quality})**\n"
                f"⏳ Скачиваю и оптимизирую {idx} из {total}...\n"
                f"🔗 `{url[:40]}...`",
                parse_mode="Markdown"
            )

            downloader = tiktok_downloader if tiktok_downloader.can_handle(url) else ytdlp_downloader
            res = await downloader.download(url, target_quality=quality)

            if res.media_type == "video":
                main_file = res.get_main_file()
                if main_file and os.path.exists(main_file):
                    url_h = hash_url(url)
                    await callback.message.answer_video(
                        video=FSInputFile(main_file),
                        caption=f"📦 [Пакет {quality}] 🎬 **{res.title}** ({idx}/{total})",
                        reply_markup=get_media_actions_kb(url_h),
                        parse_mode="Markdown",
                        supports_streaming=True
                    )
            remove_files(*res.file_paths, res.music_path)

        except Exception as e:
            await callback.message.answer(f"⚠️ Ошибка при обработке ({idx}/{total}): {str(e)[:100]}")

    await status_msg.edit_text(f"✅ **Дорожный пакет готов!**\nВсего обработано: {total} видео.")
