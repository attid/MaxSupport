import json
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String,
    Text,
    DateTime,
    ForeignKey,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.domain.models import Ticket, TicketMessage, TicketStatus, User, UserRole
from src.application.interfaces import RepositoryInterface


class Base(DeclarativeBase):
    pass


class UserTable(Base):
    __tablename__ = "users"
    user_id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[Optional[str]] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="client")


class TicketTable(Base):
    __tablename__ = "tickets"
    ticket_id: Mapped[str] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    assistant_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.user_id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="open")
    messages_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class SQLiteRepository(RepositoryInterface):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def init_db(self):
        engine = self.session_factory.kw["bind"]
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def get_user(self, user_id: int) -> Optional[User]:
        async with self.session_factory() as session:
            res = await session.execute(
                select(UserTable).where(UserTable.user_id == user_id)
            )
            row = res.scalar_one_or_none()
            if row:
                return User(
                    user_id=row.user_id,
                    username=row.username,
                    full_name=row.full_name,
                    role=UserRole(row.role),
                )
            return None

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

    async def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        async with self.session_factory() as session:
            res = await session.execute(
                select(TicketTable).where(TicketTable.ticket_id == ticket_id)
            )
            row = res.scalar_one_or_none()
            if row:
                msgs = [TicketMessage(**m) for m in json.loads(row.messages_json)]
                return Ticket(
                    ticket_id=row.ticket_id,
                    client_id=row.client_id,
                    assistant_id=row.assistant_id,
                    status=TicketStatus(row.status),
                    messages=msgs,
                    created_at=row.created_at,
                )
            return None

    async def get_active_ticket_by_client(self, client_id: int) -> Optional[Ticket]:
        async with self.session_factory() as session:
            res = await session.execute(
                select(TicketTable).where(
                    TicketTable.client_id == client_id,
                    TicketTable.status != TicketStatus.CLOSED.value,
                )
            )
            row = res.scalar_one_or_none()
            if row:
                return await self.get_ticket(row.ticket_id)
            return None

    async def save_ticket(self, ticket: Ticket) -> None:
        async with self.session_factory() as session:
            msgs_json = json.dumps([m.model_dump(mode="json") for m in ticket.messages])
            await session.merge(
                TicketTable(
                    ticket_id=ticket.ticket_id,
                    client_id=ticket.client_id,
                    assistant_id=ticket.assistant_id,
                    status=ticket.status.value,
                    messages_json=msgs_json,
                    created_at=ticket.created_at,
                )
            )
            await session.commit()

    async def get_available_assistants(self) -> List[User]:
        return []  # Пока пусто
