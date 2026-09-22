"""Handlers package."""
from aiogram import Router
from .start import router as start_router
from .cut import router as cut_router
from .travel import router as travel_router
from .actions import router as actions_router
from .media import router as media_router
from .inline import router as inline_router

main_router = Router()

# Порядок регистрации роутеров важен
main_router.include_router(start_router)
main_router.include_router(cut_router)
main_router.include_router(travel_router)
main_router.include_router(actions_router)
main_router.include_router(inline_router)
main_router.include_router(media_router)  # media_router с перехватом ссылок идет последним

__all__ = ["main_router"]
