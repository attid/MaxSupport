from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.models import Ticket, User


class RepositoryInterface(ABC):
    @abstractmethod
    async def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        pass

    @abstractmethod
    async def get_active_ticket_by_client(self, client_id: int) -> Optional[Ticket]:
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


class BotSenderInterface(ABC):
    @abstractmethod
    async def send_to_client(self, client_id: int, text: str) -> None:
        pass

    @abstractmethod
    async def send_to_assistant(self, assistant_id: int, text: str) -> None:
        pass

    @abstractmethod
    async def notify_assistants(self, text: str) -> None:
        pass
