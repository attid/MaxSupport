import asyncio
import logging
import os
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.application.interfaces import BotSenderInterface, MaxSenderInterface
from src.application.monitoring import AlarmService
from src.application.use_cases import SupportService
from src.infrastructure.config import Settings
from src.infrastructure.database import SQLiteRepository
from src.infrastructure.max import MaxSender
from src.interface.telegram.handlers import assistant, client


class BotSender(BotSenderInterface):
    def __init__(self, bot: Bot, assistants_chat_id: int):
        self._bot = bot
        self._assistants_chat_id = assistants_chat_id

    @property
    def assistants_chat_id(self) -> int:
        return self._assistants_chat_id

    async def send_to_client(self, cid: int, text: str, reply_markup: Any = None) -> int:
        msg = await self._bot.send_message(cid, text, reply_markup=reply_markup)
        return msg.message_id

    async def send_to_assistant(self, aid: int, text: str, reply_markup: Any = None) -> int:
        msg = await self._bot.send_message(aid, text, reply_markup=reply_markup)
        return msg.message_id

    async def send_to_topic(
        self, chat_id: int, topic_id: int, text: str, reply_markup: Any = None
    ) -> int:
        msg = await self._bot.send_message(
            chat_id, text, message_thread_id=topic_id, reply_markup=reply_markup
        )
        return msg.message_id

    async def create_forum_topic(self, chat_id: int, name: str) -> int:
        topic = await self._bot.create_forum_topic(chat_id, name)
        return topic.message_thread_id

    async def edit_forum_topic(self, chat_id: int, topic_id: int, name: str) -> None:
        await self._bot.edit_forum_topic(chat_id, topic_id, name=name)

    async def notify_assistants(self, text: str) -> int:
        try:
            msg = await self._bot.send_message(self._assistants_chat_id, text)
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

    commit_sha = os.getenv("COMMIT_SHA", "unknown")
    logging.info(f"Starting application on commit: {commit_sha}")

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

    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()

    sender = BotSender(bot, settings.assistants_chat_id)
    max_sender = MaxSender(token=settings.max_bot_token)
    support_service = SupportService(repo, sender, max_sender)

    # Логируем информацию о ботах
    bot_info = await bot.get_me()
    logging.info(f"Telegram Bot connected: @{bot_info.username} (ID: {bot_info.id})")

    max_info = await max_sender.get_me()
    max_username = max_info.get("username") or max_info.get("name", "Unknown")
    logging.info(f"Max Bot connected: @{max_username}")

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

    logging.info("Starting polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
