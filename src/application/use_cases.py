import uuid
from src.domain.models import Ticket, TicketMessage, TicketStatus, User, UserRole
from src.application.interfaces import RepositoryInterface, BotSenderInterface


class SupportService:
    def __init__(self, repo: RepositoryInterface, sender: BotSenderInterface):
        self.repo = repo
        self.sender = sender

    async def handle_client_message(
        self, client_id: int, full_name: str, text: str, username: str = None
    ):
        # Обеспечиваем наличие пользователя
        user = await self.repo.get_user(client_id)
        if not user:
            user = User(
                user_id=client_id,
                full_name=full_name,
                username=username,
                role=UserRole.CLIENT,
            )
            await self.repo.save_user(user)

        # Ищем активный тикет
        ticket = await self.repo.get_active_ticket_by_client(client_id)
        if not ticket:
            ticket = Ticket(ticket_id=str(uuid.uuid4()), client_id=client_id)
            await self.sender.notify_assistants(
                f"Новый тикет {ticket.ticket_id} от {full_name}: {text}"
            )

        # Добавляем сообщение
        msg = TicketMessage(sender_id=client_id, text=text)
        ticket.messages.append(msg)
        await self.repo.save_ticket(ticket)

        # Пересылаем сообщение в чат ассистентов с указанием тикета
        if ticket.assistant_id:
            await self.sender.notify_assistants(
                f"Тикет {ticket.ticket_id} (Ассистент {ticket.assistant_id}) | Клиент {full_name}: {text}"
            )

    async def handle_assistant_reply(
        self, assistant_id: int, ticket_id: str, text: str
    ):
        ticket = await self.repo.get_ticket(ticket_id)
        if not ticket:
            return

        # Назначаем ассистента, если он первый ответил
        if ticket.status == TicketStatus.OPEN:
            ticket.status = TicketStatus.ASSIGNED
            ticket.assistant_id = assistant_id

        # Сохраняем и пересылаем
        msg = TicketMessage(sender_id=assistant_id, text=text)
        ticket.messages.append(msg)
        await self.repo.save_ticket(ticket)
        await self.sender.send_to_client(ticket.client_id, text)
