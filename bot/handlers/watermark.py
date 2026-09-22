from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from bot.database import set_user_watermark, get_user_watermark, toggle_watermark_auto

router = Router()

@router.message(Command("watermark"))
async def cmd_watermark(message: Message):
    """
    Управление водяным знаком:
    /watermark @channel - установить текст вотермарка
    /watermark auto - переключить режим автоналожения на все новые видео
    /watermark off - отключить водяной знак
    """
    user_id = message.from_user.id if message.from_user else 0
    text = (message.text or "").strip()
    parts = text.split(maxsplit=1)

    # Если параметров нет - показываем статус и инструкцию
    if len(parts) == 1:
        current_wm, is_auto = await get_user_watermark(user_id)
        status_text = f"Текущий текст: **{current_wm}**" if current_wm else "Текст: *не установлен*"
        auto_text = "Включено ✅" if is_auto else "Выключено ❌"

        await message.answer(
            f"🏷 **Настройка водяного знака**\n\n"
            f"• {status_text}\n"
            f"• Авто-наложение на все видео: **{auto_text}**\n\n"
            f"📖 **Команды:**\n"
            f"• `/watermark @мой_канал` — задать текст или никнейм\n"
            f"• `/watermark auto` — вкл/выкл авто-наложение на все новые видео\n"
            f"• `/watermark off` — удалить водяной знак\n\n"
            f"💡 *Также вы можете накладывать вотермарк вручную по кнопке под каждым скачанным видео.*",
            parse_mode="Markdown"
        )
        return

    arg = parts[1].strip()

    if arg.lower() == "off":
        await set_user_watermark(user_id, None)
        await message.answer("❌ Водяной знак отключен.")
        return

    if arg.lower() == "auto":
        new_state = await toggle_watermark_auto(user_id)
        state_str = "Включено ✅ (будет накладываться на все скачиваемые видео)" if new_state else "Выключено ❌ (только по кнопке под видео)"
        await message.answer(f"⚙️ Автоматическое наложение: **{state_str}**", parse_mode="Markdown")
        return

    # Задаем новый текст
    if len(arg) > 40:
        await message.answer("⚠️ Текст водяного знака слишком длинный (максимум 40 символов).")
        return

    await set_user_watermark(user_id, arg)
    await message.answer(
        f"✅ Водяной знак успешно установлен: **{arg}**\n\n"
        f"Теперь вы можете нажимать кнопку **«🏷 Вотермарк»** под любым видео или включить авто-режим командой `/watermark auto`.",
        parse_mode="Markdown"
    )
