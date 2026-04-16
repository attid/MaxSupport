"""Telegram BotSender — реализация BotSenderInterface через aiogram."""

from typing import Any

import structlog
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.application.interfaces import BotSenderInterface

logger = structlog.get_logger()


class BotSender(BotSenderInterface):
    def __init__(self, bot: Bot, assistants_chat_id: int):
        self._bot = bot
        self._assistants_chat_id = assistants_chat_id

    @property
    def assistants_chat_id(self) -> int:
        return self._assistants_chat_id

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
        try:
            await self._bot.edit_forum_topic(chat_id, topic_id, name=name)
        except TelegramBadRequest as e:
            if "TOPIC_NOT_MODIFIED" not in str(e):
                raise

    async def is_chat_member(self, chat_id: int, user_id: int) -> bool:
        try:
            member = await self._bot.get_chat_member(chat_id, user_id)
            return member.status in ("creator", "administrator", "member")
        except Exception:
            return False

    async def notify_assistants(self, text: str) -> int:
        log = logger.bind(chat_id=self._assistants_chat_id)
        try:
            msg = await self._bot.send_message(self._assistants_chat_id, text)
            return msg.message_id
        except Exception as e:
            log.error("failed_to_notify_assistants", error=str(e))
            return 0

    def get_take_keyboard(self, ticket_id: str) -> Any:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Взять", callback_data=f"take:{ticket_id}")]
            ]
        )

    def get_close_keyboard(self, ticket_id: str) -> Any:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Закрыть", callback_data=f"close:{ticket_id}")],
                [InlineKeyboardButton(text="Другой вопрос", callback_data=f"another:{ticket_id}")],
            ]
        )

    def get_taken_keyboard(self, ticket_id: str, username: str) -> Any:
        return InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=f"Взял @{username}", callback_data="none")]]
        )
