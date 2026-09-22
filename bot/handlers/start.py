from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from bot.database import register_user

router = Router()

START_TEXT = """
👋 **Привет! Я универсальный бот-загрузчик медиа без водяных знаков.**

Просто **отправь мне ссылку** на видео или пост, и я пришлю чистое медиа в максимальном качестве!

---
🎯 **Поддерживаемые площадки:**
• **TikTok** — видео без водяных знаков и фото-слайды (карусели с музыкой)
• **YouTube** — Shorts и видеоролики
• **Instagram** — Reels и посты
• **X (Twitter)** — видео и GIF
• **VK** — VK Клипы и Видео
• **Reddit** — видео со звуком
• **Pinterest** — идеи и видео
• **Twitch** — клипы стримеров
• **Likee** — ролики

---
⚡ **Крутые возможности под каждым видео:**
🎵 **MP3** — мгновенное извлечение музыки
⚡ **Скорость** — ускорение (1.25x, 1.5x, 2x) или замедление (0.5x)
🗜 **Сжать** — уменьшение веса файла для слабого интернета
⭕ **В кружочек** — конвертация в видеосообщение Telegram
🏷 **Вотермарк** — наложение вашего никнейма или логотипа на видео
🌐 **Файлы >50 МБ** — прямая ссылка на скачивание в браузере

---
🛠 **Полезные команды:**
• `/watermark @канал` — настроить свой водяной знак (или `/watermark auto`)
• `/cut 0:10 0:30 <ссылка>` — быстрая обрезка нужного фрагмента видео
• `/travel` (или `/pack`) — пакетный режим «В дорогу» (скачивание нескольких видео с оптимизацией)
• `@botname <ссылка>` — инлайн-режим в любом групповом чате!
"""

@router.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    if user:
        await register_user(user.id, user.username, user.first_name)
    await message.answer(START_TEXT, parse_mode="Markdown")

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(START_TEXT, parse_mode="Markdown")
