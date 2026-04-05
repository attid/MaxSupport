# Code Review Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use subagent-driven-development to implement this plan task-by-task.

**Goal:** Исправить все критические и средние проблемы, найденные при code review

**Architecture:** Чистая архитектура с правильным DI, устранение глобального состояния, исправление бизнес-логики

**Tech Stack:** aiogram, aiosqlite, pydantic, pytest

---

## Проблемы для исправления

| # | Проблема | Серьёзность |
|---|----------|-------------|
| 1 | Middleware не работает (лямбда вместо класса) | 🔴 |
| 2 | Глобальный синглтон `config` | 🔴 |
| 3 | Бизнес-логика: notify до save | 🟠 |
| 4 | TicketMessage datetime.now | 🟡 |
| 5 | get_available_assistants — заглушка | 🟠 |
| 6 | Дублирование запросов в репозитории | 🟡 |
| 7 | Нет валидации входных данных | 🟠 |
| 8 | Тесты не работают (PYTHONPATH) | 🔴 |

---

## Task 1: Исправить Middleware

**Files:**
- Modify: `src/main.py`

**Step 1: Добавить класс SupportServiceMiddleware**

```python
from aiogram import BaseMiddleware
from typing import Any, Awaitable, Callable, Dict

class SupportServiceMiddleware(BaseMiddleware):
    def __init__(self, service: SupportService):
        self.service = service
    
    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any],
    ) -> Any:
        data["support_service"] = self.service
        return await handler(event, data)
```

**Step 2: Заменить register на новый middleware**

**Step 3: Проверить ruff**

---

## Task 2: Убрать глобальный config

**Files:**
- Modify: `src/infrastructure/config.py` — убрать `config = Settings()`
- Modify: `src/interface/telegram/handlers/assistant.py` — получать через DI
- Modify: `src/main.py` — создавать Settings и передавать

**Step 1: Изменить config.py**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    assistants_chat_id: int
    db_url: str = "sqlite+aiosqlite:///./data.db"

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", env_file_encoding="utf-8"
    )
```

**Step 2: Изменить assistant.py — принимать chat_id через параметр**

**Step 3: В main.py создавать Settings и передавать куда нужно**

---

## Task 3: Исправить бизнес-логику (notify после save)

**Files:**
- Modify: `src/application/use_cases.py`

**Step 1: Изменить порядок — сначала save, потом notify**

```python
async def handle_client_message(
    self, client_id: int, full_name: str, text: str, username: str = None
):
    # ...создание/получение пользователя...
    
    # Сначала получаем тикет и добавляем сообщение
    ticket = await self.repo.get_active_ticket_by_client(client_id)
    if not ticket:
        ticket = Ticket(ticket_id=str(uuid.uuid4()), client_id=client_id)
    
    # Добавляем сообщение
    msg = TicketMessage(sender_id=client_id, text=text)
    ticket.messages.append(msg)
    
    # СОХРАНЯЕМ СНАЧАЛА
    await self.repo.save_ticket(ticket)
    
    # ПОТОМ уведомляем (только если новый тикет)
    if not ticket.messages[:-1]:  # был новым
        await self.sender.notify_assistants(
            f"Новый тикет {ticket.ticket_id} от {full_name}: {text}"
        )
```

---

## Task 4: Исправить datetime.now на utcnow

**Files:**
- Modify: `src/domain/models.py`

```python
from datetime import datetime, timezone

class TicketMessage(BaseModel):
    sender_id: int
    text: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Ticket(BaseModel):
    # ...
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

---

## Task 5: Реализовать get_available_assistants

**Files:**
- Modify: `src/infrastructure/database.py`
- Modify: `tests/test_domain.py` — добавить тест

**Step 1: Реализовать метод**

```python
async def get_available_assistants(self) -> List[User]:
    async with self.session_factory() as session:
        res = await session.execute(
            select(UserTable).where(UserTable.role == UserRole.ASSISTANT.value)
        )
        rows = res.scalars().all()
        return [
            User(
                user_id=row.user_id,
                username=row.username,
                full_name=row.full_name,
                role=UserRole(row.role),
            )
            for row in rows
        ]
```

---

## Task 6: Оптимизировать get_active_ticket_by_client

**Files:**
- Modify: `src/infrastructure/database.py`

**Step 1: Получать данные в одном запросе**

```python
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
```

---

## Task 7: Добавить валидацию входных данных

**Files:**
- Modify: `src/application/use_cases.py`
- Modify: `src/interface/telegram/handlers/client.py`

**Step 1: Добавить валидацию в хендлере**

```python
@router.message(F.chat.type == "private")
async def on_client_message(message: types.Message, support_service: SupportService):
    if not message.text or not message.text.strip():
        await message.answer("Сообщение не может быть пустым.")
        return
    
    text = message.text.strip()[:4000]  # Лимит Telegram
    
    await support_service.handle_client_message(...)
```

---

## Task 8: Исправить тесты

**Files:**
- Modify: `pyproject.toml`
- Modify: `tests/test_domain.py`

**Step 1: Добавить pytest config**

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
pythonpath = ["."]
```

**Step 2: Расширить тесты**

```python
import pytest
from src.domain.models import User, UserRole, Ticket, TicketMessage, TicketStatus

def test_user_creation():
    user = User(user_id=123, full_name="Test User")
    assert user.user_id == 123
    assert user.full_name == "Test User"
    assert user.role == UserRole.CLIENT

def test_ticket_message_has_timestamp():
    msg = TicketMessage(sender_id=1, text="Hello")
    assert msg.timestamp is not None

def test_ticket_default_status():
    ticket = Ticket(ticket_id="test-123", client_id=1)
    assert ticket.status == TicketStatus.OPEN

def test_ticket_messages_list():
    ticket = Ticket(ticket_id="test-123", client_id=1)
    assert len(ticket.messages) == 0
    ticket.messages.append(TicketMessage(sender_id=1, text="Hi"))
    assert len(ticket.messages) == 1
```

---

## Task 9: Финальная проверка

**Step 1: Запустить все проверки**

```bash
just check
```

**Step 2: Убедиться что всё зелёное**

**Step 3: Запустить тесты отдельно**

```bash
pytest tests/ -v
```

---

## Commit Messages

1. `fix: create proper SupportServiceMiddleware class`
2. `fix: remove global config singleton, use DI`
3. `fix: save ticket before notifying assistants`
4. `fix: use timezone-aware utc datetime in models`
5. `feat: implement get_available_assistants`
6. `perf: optimize get_active_ticket_by_client query`
7. `feat: add input validation in handlers`
8. `test: fix pytest configuration and add tests`
