# REV-001: Ревизия проекта — исправление найденных проблем

## Контекст
Полная ревизия проекта выявила критические, средние и мелкие проблемы. Этот план покрывает всё от P0 до P2.

## План изменений
1. [x] P0: Починить lint + fmt ошибки (5 lint errors → 0)
2. [x] P0: Раскомментировать ENTRYPOINT в Dockerfile
3. [x] P0: Написать README.md
4. [x] P1: Вынести BotSender в `src/infrastructure/telegram/bot_sender.py`, middleware в `src/interface/telegram/middleware.py`
5. [x] P1: Добавить `__init__.py` во все пакеты (9 файлов)
6. [x] P1: Починить повторяющиеся алармы в monitoring.py (добавить `_alarmed_tickets` set)
7. [x] P1: Реорганизовать httpx-клиент в MaxSender (один AsyncClient, reuse connection)
8. [x] P1: Исправить datetime.now → datetime.now(timezone.utc) в database.py
9. [x] P1: Добавить ruff format --check в CI и justfile
10. [x] P2: Вынести `_row_to_ticket` и `_row_to_user` в database.py (убрать 4× дублирование)
11. [x] P2: Заменить logging на structlog в max.py и main.py
12. [x] P2: Добавить exponential backoff в max_polling.py
13. [x] P2: Добавить тесты для monitoring.py (3 теста) и max_polling.py (4 теста)
14. [x] `just check` проходит: lint 0 errors, format clean, 20 tests pass

## Верификация
- `just lint` → 0 ошибок ✅
- `just fmt-check` → 20 files already formatted ✅
- `just test` → 20 passed ✅
- `just check` → всё зелёное ✅
