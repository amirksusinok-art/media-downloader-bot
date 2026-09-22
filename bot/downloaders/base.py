from dataclasses import dataclass, field
from typing import List, Optional
from abc import ABC, abstractmethod

@dataclass
class MediaResult:
    media_type: str  # 'video', 'audio', 'images'
    file_paths: List[str]  # локальные пути к скачанным файлам
    title: str = "Media"
    author: Optional[str] = None
    duration: int = 0
    original_url: str = ""
    music_path: Optional[str] = None  # для TikTok-каруселей фоновый трек
    thumbnail_path: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None

    def get_main_file(self) -> Optional[str]:
        return self.file_paths[0] if self.file_paths else None

class BaseDownloader(ABC):
    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Проверяет, подходит ли ссылка для данного загрузчика."""
        pass

    @abstractmethod
    async def download(self, url: str, target_quality: Optional[str] = None) -> MediaResult:
        """Скачивает медиа по ссылке."""
        pass
