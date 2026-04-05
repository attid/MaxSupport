import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.infrastructure.config import config
from src.infrastructure.database import SQLiteRepository
from src.interface.telegram.handlers import client, assistant
from src.application.use_cases import SupportService
from src.application.interfaces import BotSenderInterface


class BotSender(BotSenderInterface):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def send_to_client(self, cid: int, text: str):
        await self.bot.send_message(cid, text)

    async def send_to_assistant(self, aid: int, text: str):
        await self.bot.send_message(aid, text)

    async def notify_assistants(self, text: str):
        try:
            await self.bot.send_message(config.assistants_chat_id, text)
        except Exception as e:
            logging.error(f"Failed to notify assistants: {e}")


async def main():
    logging.basicConfig(level=logging.INFO)

    # Обеспечиваем наличие директории для БД
    db_dir = os.path.dirname(config.db_url.replace("sqlite+aiosqlite:///", ""))
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    # Настройка БД
    engine = create_async_engine(config.db_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    repo = SQLiteRepository(session_factory)
    await repo.init_db()

    bot = Bot(token=config.bot_token)
    dp = Dispatcher()

    sender = BotSender(bot)
    support_service = SupportService(repo, sender)

    # DI Middleware
    dp.update.middleware.register(
        lambda handler, event, data: (
            data.update({"support_service": support_service}),
            handler(event, data),
        )[1]
    )

    dp.include_router(client.router)
    dp.include_router(assistant.router)

    logging.info("Starting bot with SQLite...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
