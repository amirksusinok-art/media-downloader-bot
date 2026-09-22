import os
import time
from pathlib import Path
from typing import Union, List, Optional
from bot.config import TEMP_DIR

def remove_files(*file_paths: Optional[Union[str, Path]]):
    """Безопасно удаляет переданные файлы с диска."""
    for path in file_paths:
        if not path:
            continue
        try:
            p = Path(path)
            if p.exists() and p.is_file():
                p.unlink(missing_ok=True)
        except Exception:
            pass

def cleanup_temp_dir(max_age_seconds: int = 1800):
    """Очищает старые временные файлы, оставшиеся дольше max_age_seconds."""
    now = time.time()
    if not TEMP_DIR.exists():
        return

    for item in TEMP_DIR.iterdir():
        if item.is_file():
            try:
                if now - item.stat().st_mtime > max_age_seconds:
                    item.unlink(missing_ok=True)
            except Exception:
                pass
