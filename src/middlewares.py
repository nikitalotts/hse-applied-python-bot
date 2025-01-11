from typing import Dict, Any, Awaitable, Callable

from aiogram import BaseMiddleware, Dispatcher
from aiogram.types import Message
from src.handlers import is_user_exists
from src.commands import *


class ProfileRequiredMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ):
        if event.text and event.text.startswith("/"):
            text = event.text.replace("/", "")
            user_id = event.from_user.id
            if (not text.startswith((START, SET_PROFILE))
                    and not text.startswith((START, HELP))
                    and not is_user_exists(user_id)):
                await event.answer(
                    "Пожалуйста, сначала настройте профиль с помощью команды /set_profile."
                )
                return
        return await handler(event, data)


class ProtectFromChangeMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ):
        if event.text and event.text.startswith(f"/{SET_PROFILE}"):
            user_id = event.from_user.id
            if is_user_exists(user_id):
                await event.answer(
                    "Вы уже настроили профиль. К сожалению, на данный момент обновление профиля недоступно."
                )
                return
        return await handler(event, data)


def setup_middleware(dp: Dispatcher):
    dp.message.middleware(ProfileRequiredMiddleware())
    dp.message.middleware(ProtectFromChangeMiddleware())
