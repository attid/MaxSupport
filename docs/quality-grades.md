# Оценки качества

Дата оценки: 2026-07-30.

| Область | Оценка | Обоснование | Следующий шаг |
|---|---:|---|---|
| Domain | A | Небольшие типизированные модели, UTC, без обратных импортов | Добавлять бизнес-инварианты вместе с тестами |
| Application | B | Use cases и monitoring покрыты тестами, но `SupportService` остаётся крупным фасадом | Разделять только при появлении независимых сценариев |
| MAX interface | B | Строгая валидация, batch isolation и backoff | Добавить contract fixtures из обезличенных реальных updates |
| Telegram interface | B | Типы aiogram проверяются Pyright, вложения покрыты частично | Добавить тесты callback handlers |
| Persistence | B | Async SQLite, WAL/FK, integration round-trip | Ввести migrations до первого изменения схемы |
| Observability | B | JSON-логи и статические JSON-метрики | Добавить runtime health endpoint при появлении HTTP interface |
| Tooling/CI | A | uv lock, ruff, Pyright, pytest и архитектурный линтер | Поддерживать версии и не ослаблять правила |
| Documentation | A | Архитектура, conventions, glossary, runbook и планы синхронизированы | Обновлять вместе с публичными контрактами |

Оценка понижается в том же PR, где обнаружен новый долг. Повышение требует
механической проверки, а не только текстового заявления.
