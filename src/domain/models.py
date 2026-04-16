from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    """Return current UTC time with timezone info."""
    return datetime.now(timezone.utc)


class AttachmentType(str, Enum):
    IMAGE = "image"
    FILE = "file"
    AUDIO = "audio"


class Attachment(BaseModel):
    type: AttachmentType
    url: str = ""
    filename: str | None = None
    token: str | None = None
    file_data: bytes | None = None


class UserRole(str, Enum):
    CLIENT = "client"
    ASSISTANT = "assistant"


class User(BaseModel):
    user_id: int
    username: Optional[str] = None
    full_name: str
    role: UserRole = UserRole.CLIENT


class TicketStatus(str, Enum):
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
    max_chat_id: Optional[int] = None
    assistant_id: Optional[int] = None
    topic_id: Optional[int] = None
    status: TicketStatus = TicketStatus.OPEN
    messages: List[TicketMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    taken_at: Optional[datetime] = None
