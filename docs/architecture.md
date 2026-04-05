# Architecture of MaxSupport

Этот проект следует принципам Чистой архитектуры. Зависимости направлены только внутрь.

## Layers

### 1. Domain (`src/domain/`)
- Чистые бизнес-сущности (User, Ticket, Message).
- Бизнес-правила и логика обработки (напр., распределение тикета на свободного ассистента).
- Не зависит от фреймворков (aiogram) или БД.

### 2. Application (`src/application/`)
- Use Cases (Сценарии использования): `CreateTicket`, `AssignAssistant`, `ForwardMessage`.
- Интерфейсы (Порты): `BotInterface`, `RepositoryInterface`.
- Оркестрация домена.

### 3. Infrastructure (`src/infrastructure/`)
- Реализация портов:
  - `MongoDBRepository` (реализация `RepositoryInterface`).
  - `TelegramSender` (реализация `BotInterface` через aiogram).
- Внешние API, логирование, конфиги.

### 4. Interface (`src/interface/`)
- **Telegram Bot API**: Хендлеры aiogram (Client handlers, Assistant handlers).
- Middleware.
- CLI команды.

## Dependency Flow
`domain ← application ← infrastructure & interface`

Прямые импорты из `infrastructure` в `application` запрещены. Инфраструктура внедряется (DI) в Application слое.
