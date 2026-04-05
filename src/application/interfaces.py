from abc import ABC, abstractmethod
from typing import Any, List, Optional

from src.domain.models import Ticket, User


class RepositoryInterface(ABC):
    @abstractmethod
    async def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        pass

    @abstractmethod
    async def get_active_ticket_by_client(self, client_id: int) -> Optional[Ticket]:
        pass

    @abstractmethod
    async def get_all_active_tickets(self) -> List[Ticket]:
        pass

    @abstractmethod
    async def get_ticket_by_topic(self, topic_id: int) -> Optional[Ticket]:
        pass

    @abstractmethod
    async def save_ticket(self, ticket: Ticket) -> None:
        pass

    @abstractmethod
    async def get_user(self, user_id: int) -> Optional[User]:
        pass

    @abstractmethod
    async def save_user(self, user: User) -> None:
        pass

    @abstractmethod
    async def get_available_assistants(self) -> List[User]:
        pass

    @abstractmethod
    async def save_message_mapping(self, message_id: int, ticket_id: str) -> None:
        pass

    @abstractmethod
    async def get_ticket_id_by_message(self, message_id: int) -> Optional[str]:
        pass


class BotSenderInterface(ABC):
    @property
    @abstractmethod
    def assistants_chat_id(self) -> int:
        pass

    @abstractmethod
    async def send_to_client(
        self, client_id: int, text: str, reply_markup: Optional[Any] = None
    ) -> int:
        pass

    @abstractmethod
    async def send_to_assistant(
        self, assistant_id: int, text: str, reply_markup: Optional[Any] = None
    ) -> int:
        pass

    @abstractmethod
    async def send_to_topic(
        self, chat_id: int, topic_id: int, text: str, reply_markup: Optional[Any] = None
    ) -> int:
        pass

    @abstractmethod
    async def create_forum_topic(self, chat_id: int, name: str) -> int:
        pass

    @abstractmethod
    async def edit_forum_topic(self, chat_id: int, topic_id: int, name: str) -> None:
        pass

    @abstractmethod
    async def notify_assistants(self, text: str) -> int:
        pass

    @abstractmethod
    def get_take_keyboard(self, ticket_id: str) -> Any:
        pass

    @abstractmethod
    def get_close_keyboard(self, ticket_id: str) -> Any:
        pass

    @abstractmethod
    def get_taken_keyboard(self, ticket_id: str, username: str) -> Any:
        pass
