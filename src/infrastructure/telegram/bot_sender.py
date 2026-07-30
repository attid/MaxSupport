"""Telegram BotSender — реализация BotSenderInterface через aiogram."""

import os
import uuid
from pathlib import Path
from typing import Any

import httpx
import structlog
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup

from src.application.interfaces import BotSenderInterface
from src.domain.models import Attachment, AttachmentType

ATTACHMENTS_DIR = Path("/tmp/maxsupport_attachments")
ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)

logger = structlog.get_logger()


class BotSender(BotSenderInterface):
    def __init__(self, bot: Bot, assistants_chat_id: int):
        self._bot = bot
        self._assistants_chat_id = assistants_chat_id

    @property
    def assistants_chat_id(self) -> int:
        return self._assistants_chat_id

    async def send_to_assistant(
        self, assistant_id: int, text: str, reply_markup: Any = None
    ) -> int:
        msg = await self._bot.send_message(assistant_id, text, reply_markup=reply_markup)
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

    async def send_file_to_topic(self, chat_id: int, topic_id: int, attachment: Attachment) -> int:
        log = logger.bind(
            action="send_file_to_topic",
            att_type=attachment.type,
            url=attachment.url[:80] if attachment.url else None,
        )
        local_path: Path | None = None
        try:
            filename = attachment.filename or "file"
            local_path = ATTACHMENTS_DIR / f"{uuid.uuid4()}_{filename}"

            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as http:
                log.info("downloading_attachment")
                r = await http.get(attachment.url)
                r.raise_for_status()
                local_path.write_bytes(r.content)
                log.info("saved_attachment", path=str(local_path), size=os.path.getsize(local_path))

            input_file = FSInputFile(local_path, filename=filename)

            if attachment.type == AttachmentType.IMAGE:
                msg = await self._bot.send_photo(chat_id, input_file, message_thread_id=topic_id)
            else:
                msg = await self._bot.send_document(chat_id, input_file, message_thread_id=topic_id)
            log.info("file_sent_to_topic", message_id=msg.message_id)
            return msg.message_id
        except Exception as e:
            log.error("send_file_to_topic_error", error=str(e))
            return 0
        finally:
            if local_path is not None:
                local_path.unlink(missing_ok=True)
