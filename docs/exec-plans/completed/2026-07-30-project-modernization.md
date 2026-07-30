# MOD-001: Полная модернизация MaxSupport

## Контекст

Нужно обновить Python-зависимости, сохранить поведение Telegram/MAX и устранить
расхождения между AI-first контрактом и реальным репозиторием.

Согласованный дизайн:
[`docs/plans/2026-07-30-project-modernization-design.md`](../../plans/2026-07-30-project-modernization-design.md).

MAX API остаётся на `platform-api.max.ru`; сертификаты и смена домена не входят
в задачу.

## План изменений

1. [x] Добавить characterization-тесты текущих Telegram handlers, MAX parsing,
   repository и lifecycle.
2. [x] Обновить прямые и транзитивные зависимости до последних стабильных
   версий, обновить `uv.lock`.
3. [x] Исправить несовместимости aiogram, pydantic-settings, SQLAlchemy,
   structlog, pytest и ruff.
4. [x] Ввести строгие Pydantic-модели для входящих MAX updates на внешней
   границе.
5. [x] Обрабатывать ошибку одного MAX update без остановки текущего batch.
6. [x] Добавить graceful shutdown фоновых задач, `MaxSender` и SQLAlchemy
   engine.
7. [x] Перевести production-логи на JSON и оставить явный dev-режим.
8. [x] Гарантированно удалять временные файлы Telegram после отправки.
9. [x] Уменьшить перегруженность application-модулей минимальным рефакторингом
   без изменения поведения.
10. [x] Расширить ruff/format на `src`, `tests` и `.linters`.
11. [x] Добавить `test-fast`, `arch-test`, `metrics` и немутирующий `check`.
12. [x] Добавить механические проверки направления импортов и циклов.
13. [x] Синхронизировать README, architecture, conventions, glossary и
   quality grades с фактическим проектом.
14. [x] Удалить устаревший корневой `main.py`.
15. [x] Выполнить полную локальную проверку и сборку Docker image.

## TDD-порядок

Для каждого изменения поведения:

1. Написать тест, воспроизводящий требуемое поведение.
2. Запустить точечный тест и подтвердить ожидаемое падение.
3. Внести минимальную реализацию.
4. Запустить точечный тест.
5. Запустить быстрый общий набор.

## Риски и открытые вопросы

- Новые версии ruff/pytest могут выявить существующие нарушения; исправления
  должны быть локальными, без массового форматирования.
- Строгая MAX-схема должна принимать только используемую часть payload и
  разрешать дополнительные поля платформы.
- Docker build зависит от доступности внешнего registry.
- Pyright добавляется только если проект проходит проверку без массовых
  `ignore` и ложного ощущения типобезопасности.

## Верификация

```bash
uv tree --outdated --depth 1
uv lock --check
uv sync --frozen
just fmt-check
just lint
just arch-test
just test
just metrics
just check
docker build -t maxsupport:verification .
git diff --check
git status --short
```

Ожидаемый результат: все проверки проходят; устаревших прямых зависимостей нет;
MAX endpoint не изменён; публичное поведение сервиса сохранено.

## Результат

- Прямые зависимости обновлены, `uv tree --outdated --depth 1` чист.
- Добавлен Pyright по ADR-0001.
- Строгая MAX validation и batch isolation покрыты тестами.
- Ресурсы закрываются через `AsyncExitStack`, включая частичный startup.
- Production-логи используют JSON и не содержат upload tokens/response body.
- Добавлены архитектурный линтер, JSON-метрики и полный `just check`.
- Добавлены integration/characterization-тесты SQLite, Telegram handlers,
  lifecycle, MAX adapter и файлов.
- Docker image `maxsupport:verification` успешно собран.
- MAX endpoint остался `https://platform-api.max.ru`; сертификаты не менялись.
