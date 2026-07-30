from abc import ABC, abstractmethod
from typing import Any

from src.domain.models import Attachment, Ticket, User


class RepositoryInterface(ABC):
    @abstractmethod
    async def get_ticket(self, ticket_id: str) -> Ticket | None:
        pass

    @abstractmethod
    async def get_active_ticket_by_client(self, client_id: int) -> Ticket | None:
        pass

    @abstractmethod
    async def get_all_active_tickets(self) -> list[Ticket]:
        pass

    @abstractmethod
    async def get_ticket_by_topic(self, topic_id: int) -> Ticket | None:
        pass

    @abstractmethod
    async def save_ticket(self, ticket: Ticket) -> None:
        pass

    @abstractmethod
    async def get_user(self, user_id: int) -> User | None:
        pass

    @abstractmethod
    async def save_user(self, user: User) -> None:
        pass

    @abstractmethod
    async def get_available_assistants(self) -> list[User]:
        pass

    @abstractmethod
    async def save_message_mapping(self, message_id: int, ticket_id: str) -> None:
        pass

    @abstractmethod
    async def get_ticket_id_by_message(self, message_id: int) -> str | None:
        pass


class MaxSenderInterface(ABC):
    @abstractmethod
    async def send_to_client(
        self, chat_id: int, text: str, attachments: list[Attachment] | None = None
    ) -> int:
        pass

    @abstractmethod
    async def upload_file(self, file_data: bytes, filename: str) -> str | None:
        """Upload a file to Max and return the attachment token."""
        pass

    @abstractmethod
    async def get_me(self) -> dict:
        """Returns bot info from MAX platform."""
        pass

    @abstractmethod
    async def get_updates(self, marker: int | None) -> tuple[list[dict], int | None]:
        """Fetch new updates from MAX platform.

        Returns (updates, new_marker). The caller must pass new_marker
        into the next call to avoid receiving duplicate updates.
        """
        pass


class BotSenderInterface(ABC):
    @property
    @abstractmethod
    def assistants_chat_id(self) -> int:
        pass

    @abstractmethod
    async def is_chat_member(self, chat_id: int, user_id: int) -> bool:
        """Check if user is a member of the given chat."""
        pass

    @abstractmethod
    async def send_to_assistant(
        self, assistant_id: int, text: str, reply_markup: Any | None = None
    ) -> int:
        pass

    @abstractmethod
    async def send_to_topic(
        self, chat_id: int, topic_id: int, text: str, reply_markup: Any | None = None
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

    @abstractmethod
    async def send_file_to_topic(self, chat_id: int, topic_id: int, attachment: Attachment) -> int:
        """Download file by URL and send to TG topic as photo or document."""
        pass
