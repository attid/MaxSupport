"""aiogram middleware for injecting SupportService into handlers."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware

from src.application.use_cases import SupportService


class SupportServiceMiddleware(BaseMiddleware):
    def __init__(self, service: SupportService):
        self.service = service

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        data["support_service"] = self.service
        return await handler(event, data)
