import os
from aiogram import Router, F
from aiogram.types import Message
from bot.config import COOKIES_PATH, ADMIN_ID

router = Router()

@router.message(F.document)
async def handle_document(message: Message):
    doc = message.document
    if not doc or not doc.file_name:
        return

    fname = doc.file_name.lower()
    # Реагируем на файлы с именем cookies.txt или содержащие cookies в названии
    if "cookie" in fname and fname.endswith(".txt"):
        user_id = message.from_user.id if message.from_user else 0

        # Проверка прав администратора, если ADMIN_ID задан
        if ADMIN_ID != 0 and user_id != ADMIN_ID:
            await message.answer("❌ Загружать файл cookies.txt разрешено только администратору бота.")
            return

        status_msg = await message.answer("⏳ Сохраняю и проверяю файл cookies...")
        try:
            bot = message.bot
            file_info = await bot.get_file(doc.file_id)

            # Сохраняем прямо в data/cookies.txt
            await bot.download_file(file_info.file_path, destination=str(COOKIES_PATH))

            file_size = os.path.getsize(COOKIES_PATH)
            await status_msg.edit_text(
                f"✅ **Файл cookies.txt успешно загружен и активирован!**\n\n"
                f"📊 Размер: `{file_size} байт`\n"
                f"🛡 Теперь YouTube и Instagram будут скачиваться со 100% стабильностью без блокировок.",
                parse_mode="Markdown"
            )
        except Exception as e:
            await status_msg.edit_text(f"❌ Не удалось сохранить cookies: {str(e)[:150]}")
