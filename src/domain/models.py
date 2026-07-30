from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    """Return current UTC time with timezone info."""
    return datetime.now(UTC)


class AttachmentType(StrEnum):
    IMAGE = "image"
    FILE = "file"
    AUDIO = "audio"


class Attachment(BaseModel):
    type: AttachmentType
    url: str = ""
    filename: str | None = None
    token: str | None = None
    file_data: bytes | None = None


class UserRole(StrEnum):
    CLIENT = "client"
    ASSISTANT = "assistant"


class User(BaseModel):
    user_id: int
    username: str | None = None
    full_name: str
    role: UserRole = UserRole.CLIENT


class TicketStatus(StrEnum):
    OPEN = "open"
    ASSIGNED = "assigned"
    CLOSED = "closed"


class TicketMessage(BaseModel):
    sender_id: int
    text: str
    timestamp: datetime = Field(default_factory=utc_now)


class Ticket(BaseModel):
    ticket_id: str
    client_id: int
    max_chat_id: int | None = None
    assistant_id: int | None = None
    topic_id: int | None = None
    status: TicketStatus = TicketStatus.OPEN
    messages: list[TicketMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    taken_at: datetime | None = None
