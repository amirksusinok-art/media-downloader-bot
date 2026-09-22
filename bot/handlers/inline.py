import hashlib
from aiogram import Router
from aiogram.types import (
    InlineQuery,
    InlineQueryResultCachedVideo,
    InlineQueryResultArticle,
    InputTextMessageContent
)
from bot.database import get_cached_media

router = Router()

@router.inline_query()
async def inline_media_handler(query: InlineQuery):
    text = query.query.strip()
    if not text.startswith("http"):
        return

    cached = await get_cached_media(text, "video")
    results = []

    if cached:
        result_id = hashlib.md5(text.encode()).hexdigest()
        results.append(
            InlineQueryResultCachedVideo(
                id=result_id,
                video_file_id=cached["file_id"],
                title=cached.get("title") or "Скачанное видео",
                caption=f"🎬 **{cached.get('title', 'Видео')}**\n⚡ Отправлено через @{query.from_user.username or 'бота'}",
                parse_mode="Markdown"
            )
        )
    else:
        result_id = hashlib.md5(text.encode()).hexdigest()
        results.append(
            InlineQueryResultArticle(
                id=result_id,
                title="📥 Новое видео — нажмите для загрузки",
                description="Это видео ещё не в кэше. Нажмите, чтобы запросить его загрузку.",
                input_message_content=InputTextMessageContent(
                    message_text=f"📥 Скачиваю медиа по ссылке:\n{text}"
                )
            )
        )

    await query.answer(results=results, cache_time=10, is_personal=True)
