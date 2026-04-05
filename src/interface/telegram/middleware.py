"""aiogram middleware for injecting SupportService into handlers."""

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware

from src.application.use_cases import SupportService


class SupportServiceMiddleware(BaseMiddleware):
    def __init__(self, service: SupportService):
        self.service = service

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any],
    ) -> Any:
        data["support_service"] = self.service
        return await handler(event, data)
