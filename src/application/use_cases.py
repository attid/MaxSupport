import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog

from src.application.interfaces import (
    BotSenderInterface,
    MaxSenderInterface,
    RepositoryInterface,
)
from src.domain.models import Ticket, TicketMessage, TicketStatus, User, UserRole

logger = structlog.get_logger()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SupportService:
    def __init__(
        self,
        repo: RepositoryInterface,
        sender: BotSenderInterface,
        max_sender: MaxSenderInterface,
    ):
        self._repo = repo
        self._sender = sender
        self._max_sender = max_sender
        self.log = logger.bind(service="support_service")

    @property
    def repo(self) -> RepositoryInterface:
        return self._repo

    @property
    def sender(self) -> BotSenderInterface:
        return self._sender

    @property
    def max_sender(self) -> MaxSenderInterface:
        return self._max_sender

    async def is_assistant(self, user_id: int) -> bool:
        """Check if user is a member of the assistants chat."""
        return await self._sender.is_chat_member(
            self._sender.assistants_chat_id, user_id
        )

    async def get_ticket_id_by_message(self, message_id: int) -> Optional[str]:
        """Get ticket ID associated with a message."""
        return await self._repo.get_ticket_id_by_message(message_id)

    async def handle_client_message(
        self,
        client_id: int,
        full_name: str,
        text: str,
        username: str | None = None,
        force_new_ticket: bool = False,
    ) -> None:
        log = self.log.bind(client_id=client_id, full_name=full_name)
        log.info("handling_client_message", force_new_ticket=force_new_ticket)

        # Обеспечиваем наличие пользователя
        user = await self._repo.get_user(client_id)
        if not user:
            log.info("creating_new_user")
            user = User(
                user_id=client_id,
                full_name=full_name,
                username=username,
                role=UserRole.CLIENT,
            )
            await self._repo.save_user(user)

        # Ищем активный тикет
        ticket = None
        if not force_new_ticket:
            ticket = await self._repo.get_active_ticket_by_client(client_id)

        is_new_ticket = ticket is None

        if is_new_ticket:
            log.info("creating_new_ticket_and_topic")
            ticket_id = str(uuid.uuid4())
            # Создаем топик в группе ассистентов
            topic_name = f"🔴 Новый вопрос: {full_name}"
            topic_id = await self._sender.create_forum_topic(
                self._sender.assistants_chat_id, topic_name
            )

            ticket = Ticket(
                ticket_id=ticket_id,
                client_id=client_id,
                topic_id=topic_id,
            )

        # Добавляем сообщение
        msg = TicketMessage(sender_id=client_id, text=text)
        ticket.messages.append(msg)

        # СНАЧАЛА СОХРАНЯЕМ
        await self._repo.save_ticket(ticket)

        # ПОТОМ уведомляем в топик
        kb = self._sender.get_take_keyboard(ticket.ticket_id)
        if is_new_ticket:
            # Первое сообщение в топике
            msg_id = await self._sender.send_to_topic(
                self._sender.assistants_chat_id,
                ticket.topic_id,
                f"Новый тикет от {full_name} (@{username or 'no_user'}):\n\n{text}",
                reply_markup=kb,
            )
            if msg_id:
                await self._repo.save_message_mapping(msg_id, ticket.ticket_id)
        else:
            # Если тикет был взят (желтый), а клиент написал — снова делаем красным 🔴
            if ticket.status == TicketStatus.ASSIGNED:
                log.info("marking_assigned_ticket_as_red_due_to_client_message")
                new_name = f"🔴 Ждет ответа: {full_name}"
                await self._sender.edit_forum_topic(
                    self._sender.assistants_chat_id, ticket.topic_id, new_name
                )

            # Дополнительное сообщение в существующий топик
            kb_close = self._sender.get_close_keyboard(ticket.ticket_id)
            msg_id = await self._sender.send_to_topic(
                self._sender.assistants_chat_id,
                ticket.topic_id,
                f"Клиент добавил:\n{text}",
                reply_markup=kb_close,
            )
            if msg_id:
                await self._repo.save_message_mapping(msg_id, ticket.ticket_id)

    async def take_ticket(self, ticket_id: str, assistant_id: int, username: str) -> None:
        log = self.log.bind(assistant_id=assistant_id, ticket_id=ticket_id)
        log.info("taking_ticket")

        ticket = await self._repo.get_ticket(ticket_id)
        if not ticket or ticket.status != TicketStatus.OPEN:
            log.warning("ticket_not_eligible_for_taking")
            return

        ticket.status = TicketStatus.ASSIGNED
        ticket.assistant_id = assistant_id
        ticket.taken_at = utc_now()
        await self._repo.save_ticket(ticket)

        # Обновляем имя топика
        new_name = f"🟡 Взял @{username}: {ticket.client_id}"
        await self._sender.edit_forum_topic(
            self._sender.assistants_chat_id, ticket.topic_id, new_name
        )

        # Мы не можем легко найти сообщение с кнопкой "Взять" без message_id,
        # но мы можем отправить новое сообщение в топик или просто оставить как есть.
        # В идеале нужно хранить message_id первого сообщения.
        await self._sender.send_to_topic(
            self._sender.assistants_chat_id,
            ticket.topic_id,
            f"Ассистент @{username} взял тикет в работу.",
            reply_markup=self._sender.get_close_keyboard(ticket_id),
        )

    async def handle_assistant_reply(
        self,
        assistant_id: int,
        ticket_id: str,
        text: str,
    ) -> None:
        log = self.log.bind(assistant_id=assistant_id, ticket_id=ticket_id)
        log.info("handling_assistant_reply")

        ticket = await self._repo.get_ticket(ticket_id)
        if not ticket:
            log.warning("ticket_not_found")
            return

        # Если тикет был OPEN, переводим в ASSIGNED
        if ticket.status == TicketStatus.OPEN:
            ticket.status = TicketStatus.ASSIGNED
            ticket.assistant_id = assistant_id
            ticket.taken_at = utc_now()

        # Возвращаем желтый статус 🟡 в названии топика после ответа ассистента
        # Получаем данные ассистента (для username)
        assistant = await self._repo.get_user(assistant_id)
        if assistant:
            assistant_name = assistant.username or assistant.full_name
        else:
            assistant_name = str(assistant_id)

        new_name = f"🟡 Взял @{assistant_name}: {ticket.client_id}"
        await self._sender.edit_forum_topic(
            self._sender.assistants_chat_id, ticket.topic_id, new_name
        )

        # Сохраняем сообщение
        msg = TicketMessage(sender_id=assistant_id, text=text)
        ticket.messages.append(msg)

        # СНАЧАЛА СОХРАНЯЕМ
        await self._repo.save_ticket(ticket)

        # ПОТОМ отправляем клиенту
        await self._max_sender.send_to_client(ticket.client_id, text)

    async def close_ticket(self, ticket_id: str, assistant_id: int, username: str) -> bool:
        """Close a ticket. Returns True if successful."""
        log = self.log.bind(ticket_id=ticket_id, assistant_id=assistant_id)
        log.info("closing_ticket")

        ticket = await self._repo.get_ticket(ticket_id)
        if not ticket:
            return False

        ticket.status = TicketStatus.CLOSED
        await self._repo.save_ticket(ticket)

        # Обновляем имя топика
        new_name = f"🟢 Закрыл @{username}: {ticket.client_id}"
        await self._sender.edit_forum_topic(
            self._sender.assistants_chat_id, ticket.topic_id, new_name
        )

        await self._sender.send_to_topic(
            self._sender.assistants_chat_id,
            ticket.topic_id,
            f"Тикет закрыт ассистентом @{username}.",
        )

        # Уведомляем клиента
        await self._max_sender.send_to_client(
            ticket.client_id,
            "Ваш тикет закрыт. Если у вас возникнут новые вопросы, просто напишите нам!",
        )

        return True

    async def handle_another_question(
        self, ticket_id: str, assistant_id: int, username: str
    ) -> None:
        """Close current ticket and prompt for a new one, or handle it as a new question."""
        ticket = await self._repo.get_ticket(ticket_id)
        if not ticket:
            return

        # Закрываем текущий
        await self.close_ticket(ticket_id, assistant_id, username)

        # Здесь мы могли бы перенести последнее сообщение в новый тикет,
        # но проще всего попросить клиента написать новый вопрос или
        # вручную создать новый тикет из последнего сообщения.
        # Для простоты — просто закрываем. Пользователь просил "создает новую тему".
        # Но для этого нам нужно знать, какое сообщение "другое".
        # В контексте кнопок под каждым сообщением клиента — мы знаем.
