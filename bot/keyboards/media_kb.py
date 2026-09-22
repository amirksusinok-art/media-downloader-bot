from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_media_actions_kb(media_id: str) -> InlineKeyboardMarkup:
    """Клавиатура действий над полученным видео."""
    buttons = [
        [
            InlineKeyboardButton(text="🎵 MP3", callback_data=f"act:mp3:{media_id}"),
            InlineKeyboardButton(text="🗜 Сжать", callback_data=f"act:cmp:{media_id}")
        ],
        [
            InlineKeyboardButton(text="⚡ Скорость", callback_data=f"act:spd_menu:{media_id}"),
            InlineKeyboardButton(text="⭕ В кружочек", callback_data=f"act:circle:{media_id}")
        ],
        [
            InlineKeyboardButton(text="🏷 Вотермарк", callback_data=f"act:wm:{media_id}"),
            InlineKeyboardButton(text="✂️ Обрезать (/cut)", callback_data="info:cut")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_direct_download_kb(download_url: str, size_mb: float = 0.0) -> InlineKeyboardMarkup:
    """Клавиатура с прямой ссылкой на скачивание тяжелого видео в браузере."""
    size_str = f" ({size_mb:.1f} МБ)" if size_mb > 0 else ""
    buttons = [
        [
            InlineKeyboardButton(text=f"🌐 Скачать видео в браузере{size_str}", url=download_url)
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_speed_kb(media_id: str) -> InlineKeyboardMarkup:
    """Подменю выбора скорости воспроизведения."""
    buttons = [
        [
            InlineKeyboardButton(text="0.5x", callback_data=f"spd:0.5:{media_id}"),
            InlineKeyboardButton(text="1.25x", callback_data=f"spd:1.25:{media_id}"),
            InlineKeyboardButton(text="1.5x", callback_data=f"spd:1.5:{media_id}"),
            InlineKeyboardButton(text="2.0x", callback_data=f"spd:2.0:{media_id}")
        ],
        [
            InlineKeyboardButton(text="« Назад", callback_data=f"act:back:{media_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_travel_quality_kb(task_id: str) -> InlineKeyboardMarkup:
    """Выбор качества для пакетного режима «В дорогу»."""
    buttons = [
        [
            InlineKeyboardButton(text="🚗 Компактный (480p - меньше весит)", callback_data=f"pkg:480p:{task_id}")
        ],
        [
            InlineKeyboardButton(text="✈️ Стандартный (720p - баланс)", callback_data=f"pkg:720p:{task_id}")
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"pkg:cancel:{task_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
