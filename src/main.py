import asyncio
import logging
import os
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, Bot, Dispatcher
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.application.interfaces import BotSenderInterface
from src.application.use_cases import SupportService
from src.infrastructure.config import Settings
from src.infrastructure.database import SQLiteRepository
from src.interface.telegram.handlers import assistant, client


class BotSender(BotSenderInterface):
    def __init__(self, bot: Bot, assistants_chat_id: int):
        self.bot = bot
        self.assistants_chat_id = assistants_chat_id

    async def send_to_client(self, cid: int, text: str) -> None:
        await self.bot.send_message(cid, text)

    async def send_to_assistant(self, aid: int, text: str) -> None:
        await self.bot.send_message(aid, text)

    async def notify_assistants(self, text: str) -> None:
        try:
            await self.bot.send_message(self.assistants_chat_id, text)
        except Exception as e:
            logging.error(f"Failed to notify assistants: {e}")


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


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    # Загружаем настройки
    settings = Settings()

    # Обеспечиваем наличие директории для БД
    db_path = settings.db_url.replace("sqlite+aiosqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    # Настройка БД
    engine = create_async_engine(settings.db_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    repo = SQLiteRepository(session_factory)
    await repo.init_db()

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    sender = BotSender(bot, settings.assistants_chat_id)
    support_service = SupportService(repo, sender)

    # DI Middleware
    dp.update.middleware.register(SupportServiceMiddleware(support_service))

    # Регистрируем роутеры с передачей настроек
    dp.include_routers(
        client.create_router(support_service),
        assistant.create_router(support_service),
    )

    logging.info("Starting bot with SQLite...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
