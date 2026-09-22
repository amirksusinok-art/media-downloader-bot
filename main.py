import os
import sys
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import BOT_TOKEN
from bot.database import init_db
from bot.handlers import main_router
from bot.services.cleaner import cleanup_temp_dir

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)
logger = logging.getLogger("MediaBot")

async def main():
    if not BOT_TOKEN or BOT_TOKEN == "your_telegram_bot_token_here":
        logger.error(
            "❌ ОШИБКА: BOT_TOKEN не указан!\n"
            "Пожалуйста, создайте файл .env на основе .env.example и укажите ваш токен от @BotFather:\n"
            "BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
        )
        sys.exit(1)

    logger.info("Инициализация базы данных...")
    await init_db()

    logger.info("Очистка старых временных файлов...")
    cleanup_temp_dir()

    logger.info("Запуск бота...")
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    dp.include_router(main_router)

    # Пропускаем накопившиеся апдейты
    await bot.delete_webhook(drop_pending_updates=True)

    # Поддержка бесплатного хостинга на Render и раздачи тяжелых файлов (>50 МБ):
    port = int(os.getenv("PORT", "10000"))
    try:
        from aiohttp import web
        from bot.services.web_downloads import web_download_manager

        async def download_handler(request):
            token = request.match_info.get("token")
            info = web_download_manager.get_download(token)
            if not info:
                return web.Response(status=404, text="Файл не найден, ссылка устарела или уже была использована.")

            file_path = info["file_path"]
            filename = info.get("filename", "video.mp4")

            async def delayed_cleanup():
                # Удаляем файл через 60 секунд после начала отдачи браузеру
                await asyncio.sleep(60)
                web_download_manager.complete_download(token)

            asyncio.create_task(delayed_cleanup())

            return web.FileResponse(
                path=file_path,
                headers={"Content-Disposition": f'attachment; filename="{filename}"'}
            )

        app = web.Application()
        app.router.add_get("/", lambda r: web.Response(text="Bot is running OK!"))
        app.router.add_get("/health", lambda r: web.Response(text="OK"))
        app.router.add_get("/download/{token}", download_handler)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info(f"Встроенный веб-сервер успешно запущен на порту {port}")
    except Exception as e:
        logger.warning(f"Не удалось запустить встроенный веб-сервер: {e}")

    logger.info("Бот успешно запущен и ожидает сообщений!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
