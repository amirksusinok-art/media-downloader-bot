import asyncio
from typing import Callable, Any, Optional
from aiogram.types import Message

class TaskQueueManager:
    """
    Менеджер очередей с ограничением параллельных ресурсоемких задач (FFmpeg / скачивание).
    Защищает сервер от падения по памяти (Out Of Memory) на тарифах с 512MB RAM.
    """
    def __init__(self, max_concurrent: int = 2):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._waiting_count = 0
        self._lock = asyncio.Lock()

    async def run(
        self,
        coro_func: Callable[..., Any],
        *args,
        status_msg: Optional[Message] = None,
        **kwargs
    ) -> Any:
        # Проверяем, свободен ли слот
        if self._semaphore.locked():
            async with self._lock:
                self._waiting_count += 1
                pos = self._waiting_count

            if status_msg:
                try:
                    await status_msg.edit_text(
                        f"⏳ **Сервер занят.** Ваша задача в очереди (позиция #{pos})...\n"
                        "Пожалуйста, подождите, скоро начнется обработка."
                    )
                except Exception:
                    pass

            try:
                async with self._semaphore:
                    async with self._lock:
                        self._waiting_count = max(0, self._waiting_count - 1)
                    if status_msg:
                        try:
                            await status_msg.edit_text("⚡ Очередь подошла! Начинаю обработку видео...")
                        except Exception:
                            pass
                    return await coro_func(*args, **kwargs)
            except Exception:
                async with self._lock:
                    self._waiting_count = max(0, self._waiting_count - 1)
                raise
        else:
            async with self._semaphore:
                return await coro_func(*args, **kwargs)

# Глобальный экземпляр очереди с лимитом в 2 одновременные задачи
ffmpeg_queue = TaskQueueManager(max_concurrent=2)
