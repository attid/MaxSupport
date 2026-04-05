import uuid

from src.application.interfaces import BotSenderInterface, RepositoryInterface
from src.domain.models import Ticket, TicketMessage, TicketStatus, User, UserRole


class SupportService:
    def __init__(self, repo: RepositoryInterface, sender: BotSenderInterface):
        self._repo = repo
        self._sender = sender

    @property
    def repo(self) -> RepositoryInterface:
        return self._repo

    @property
    def sender(self) -> BotSenderInterface:
        return self._sender

    async def handle_client_message(
        self,
        client_id: int,
        full_name: str,
        text: str,
        username: str | None = None,
    ) -> None:
        # Обеспечиваем наличие пользователя
        user = await self._repo.get_user(client_id)
        if not user:
            user = User(
                user_id=client_id,
                full_name=full_name,
                username=username,
                role=UserRole.CLIENT,
            )
            await self._repo.save_user(user)

        # Ищем активный тикет
        ticket = await self._repo.get_active_ticket_by_client(client_id)
        is_new_ticket = ticket is None

        if is_new_ticket:
            ticket = Ticket(
                ticket_id=str(uuid.uuid4()),
                client_id=client_id,
            )

        # Добавляем сообщение
        msg = TicketMessage(sender_id=client_id, text=text)
        ticket.messages.append(msg)

        # СНАЧАЛА СОХРАНЯЕМ
        await self._repo.save_ticket(ticket)

        # ПОТОМ уведомляем (только для новых тикетов)
        if is_new_ticket:
            await self._sender.notify_assistants(
                f"Новый тикет {ticket.ticket_id} от {full_name}: {text}"
            )

    async def handle_assistant_reply(
        self,
        assistant_id: int,
        ticket_id: str,
        text: str,
    ) -> None:
        ticket = await self._repo.get_ticket(ticket_id)
        if not ticket:
            return

        # Назначаем ассистента, если он первый ответил
        if ticket.status == TicketStatus.OPEN:
            ticket.status = TicketStatus.ASSIGNED
            ticket.assistant_id = assistant_id

        # Сохраняем сообщение
        msg = TicketMessage(sender_id=assistant_id, text=text)
        ticket.messages.append(msg)

        # СНАЧАЛА СОХРАНЯЕМ
        await self._repo.save_ticket(ticket)

        # ПОТОМ отправляем клиенту
        await self._sender.send_to_client(ticket.client_id, text)

    async def close_ticket(self, ticket_id: str) -> bool:
        """Close a ticket. Returns True if successful, False if ticket not found."""
        ticket = await self._repo.get_ticket(ticket_id)
        if not ticket:
            return False

        ticket.status = TicketStatus.CLOSED
        await self._repo.save_ticket(ticket)
        return True
