import json
from datetime import UTC, datetime
from typing import overload

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    event,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.application.interfaces import RepositoryInterface
from src.domain.models import Ticket, TicketMessage, TicketStatus, User, UserRole


def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def setup_sqlite_engine(engine) -> None:
    """Register SQLite pragmas for the engine."""

    event.listen(engine.sync_engine, "connect", _set_sqlite_pragma)


def _utc_now() -> datetime:
    return datetime.now(UTC)


@overload
def _as_utc(value: datetime) -> datetime: ...


@overload
def _as_utc(value: None) -> None: ...


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class Base(DeclarativeBase):
    pass


class UserTable(Base):
    __tablename__ = "users"
    user_id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str | None] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="client")


class TicketTable(Base):
    __tablename__ = "tickets"
    ticket_id: Mapped[str] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    max_chat_id: Mapped[int | None] = mapped_column(nullable=True)
    assistant_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    topic_id: Mapped[int | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open")
    messages_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MessageMappingTable(Base):
    __tablename__ = "message_mappings"
    message_id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.ticket_id"))


def _row_to_user(row: UserTable) -> User:
    return User(
        user_id=row.user_id,
        username=row.username,
        full_name=row.full_name,
        role=UserRole(row.role),
    )


def _row_to_ticket(row: TicketTable) -> Ticket:
    msgs = [TicketMessage(**m) for m in json.loads(row.messages_json)]
    return Ticket(
        ticket_id=row.ticket_id,
        client_id=row.client_id,
        max_chat_id=row.max_chat_id,
        assistant_id=row.assistant_id,
        topic_id=row.topic_id,
        status=TicketStatus(row.status),
        messages=msgs,
        created_at=_as_utc(row.created_at),
        taken_at=_as_utc(row.taken_at),
    )


class SQLiteRepository(RepositoryInterface):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def init_db(self) -> None:
        engine = self.session_factory.kw["bind"]
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def get_user(self, user_id: int) -> User | None:
        async with self.session_factory() as session:
            res = await session.execute(select(UserTable).where(UserTable.user_id == user_id))
            row = res.scalar_one_or_none()
            return _row_to_user(row) if row else None

    async def save_user(self, user: User) -> None:
        async with self.session_factory() as session:
            await session.merge(
                UserTable(
                    user_id=user.user_id,
                    username=user.username,
                    full_name=user.full_name,
                    role=user.role.value,
                )
            )
            await session.commit()

    async def get_ticket(self, ticket_id: str) -> Ticket | None:
        async with self.session_factory() as session:
            res = await session.execute(
                select(TicketTable).where(TicketTable.ticket_id == ticket_id)
            )
            row = res.scalar_one_or_none()
            return _row_to_ticket(row) if row else None

    async def get_all_active_tickets(self) -> list[Ticket]:
        async with self.session_factory() as session:
            res = await session.execute(
                select(TicketTable).where(TicketTable.status != TicketStatus.CLOSED.value)
            )
            return [_row_to_ticket(row) for row in res.scalars().all()]

    async def get_ticket_by_topic(self, topic_id: int) -> Ticket | None:
        async with self.session_factory() as session:
            res = await session.execute(select(TicketTable).where(TicketTable.topic_id == topic_id))
            row = res.scalar_one_or_none()
            return _row_to_ticket(row) if row else None

    async def get_active_ticket_by_client(self, client_id: int) -> Ticket | None:
        async with self.session_factory() as session:
            res = await session.execute(
                select(TicketTable).where(
                    TicketTable.client_id == client_id,
                    TicketTable.status != TicketStatus.CLOSED.value,
                )
            )
            row = res.scalar_one_or_none()
            return _row_to_ticket(row) if row else None

    async def save_ticket(self, ticket: Ticket) -> None:
        async with self.session_factory() as session:
            msgs_json = json.dumps([m.model_dump(mode="json") for m in ticket.messages])
            await session.merge(
                TicketTable(
                    ticket_id=ticket.ticket_id,
                    client_id=ticket.client_id,
                    max_chat_id=ticket.max_chat_id,
                    assistant_id=ticket.assistant_id,
                    topic_id=ticket.topic_id,
                    status=ticket.status.value,
                    messages_json=msgs_json,
                    created_at=ticket.created_at,
                    taken_at=ticket.taken_at,
                )
            )
            await session.commit()

    async def get_available_assistants(self) -> list[User]:
        async with self.session_factory() as session:
            res = await session.execute(
                select(UserTable).where(UserTable.role == UserRole.ASSISTANT.value)
            )
            return [_row_to_user(row) for row in res.scalars().all()]

    async def save_message_mapping(self, message_id: int, ticket_id: str) -> None:
        async with self.session_factory() as session:
            await session.merge(MessageMappingTable(message_id=message_id, ticket_id=ticket_id))
            await session.commit()

    async def get_ticket_id_by_message(self, message_id: int) -> str | None:
        async with self.session_factory() as session:
            res = await session.execute(
                select(MessageMappingTable.ticket_id).where(
                    MessageMappingTable.message_id == message_id
                )
            )
            return res.scalar_one_or_none()
