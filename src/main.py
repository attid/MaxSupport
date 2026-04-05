import asyncio
import logging
import os
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.application.interfaces import BotSenderInterface
from src.application.monitoring import AlarmService
from src.application.use_cases import SupportService
from src.infrastructure.config import Settings
from src.infrastructure.database import SQLiteRepository
from src.interface.telegram.handlers import assistant, client


class BotSender(BotSenderInterface):
    def __init__(self, bot: Bot, assistants_chat_id: int):
        self.bot = bot
        self.assistants_chat_id = assistants_chat_id

    async def send_to_client(self, cid: int, text: str, reply_markup: Any = None) -> int:
        msg = await self.bot.send_message(cid, text, reply_markup=reply_markup)
        return msg.message_id

    async def send_to_assistant(self, aid: int, text: str, reply_markup: Any = None) -> int:
        msg = await self.bot.send_message(aid, text, reply_markup=reply_markup)
        return msg.message_id

    async def send_to_topic(
        self, chat_id: int, topic_id: int, text: str, reply_markup: Any = None
    ) -> int:
        msg = await self.bot.send_message(
            chat_id, text, message_thread_id=topic_id, reply_markup=reply_markup
        )
        return msg.message_id

    async def create_forum_topic(self, chat_id: int, name: str) -> int:
        topic = await self.bot.create_forum_topic(chat_id, name)
        return topic.message_thread_id

    async def edit_forum_topic(self, chat_id: int, topic_id: int, name: str) -> None:
        await self.bot.edit_forum_topic(chat_id, topic_id, name=name)

    async def notify_assistants(self, text: str) -> int:
        try:
            msg = await self.bot.send_message(self.assistants_chat_id, text)
            return msg.message_id
        except Exception as e:
            logging.error(f"Failed to notify assistants: {e}")
            return 0

    def get_take_keyboard(self, ticket_id: str) -> Any:
        return InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="Взять", callback_data=f"take:{ticket_id}")
            ]]
        )

    def get_close_keyboard(self, ticket_id: str) -> Any:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Закрыть", callback_data=f"close:{ticket_id}")],
                [InlineKeyboardButton(text="Другой вопрос", callback_data=f"another:{ticket_id}")]
            ]
        )

    def get_taken_keyboard(self, ticket_id: str, username: str) -> Any:
        return InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text=f"Взял @{username}", callback_data="none")
            ]]
        )


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

    # Запускаем мониторинг
    alarm_service = AlarmService(repo, sender)
    asyncio.create_task(alarm_service.start_monitoring())

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
