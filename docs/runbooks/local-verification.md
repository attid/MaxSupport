# Локальная проверка

## Полная проверка

```bash
uv sync --frozen
uv lock --check
just check
just metrics
```

`just check` не изменяет файлы. Если форматирование не проходит:

```bash
just fmt
just check
```

## Диагностика

- Ruff: исправить указанное правило или выполнить `just fmt`.
- Pyright: сузить Optional-значение проверкой; не добавлять глобальный ignore.
- Architecture: перенести внешний контракт в interface/infrastructure или
  определить порт в application.
- Pytest: сначала запустить конкретный тест с `-vv`, затем весь набор.
- Lockfile: выполнить `uv lock --upgrade`, проверить diff `uv.lock` и повторить
  frozen sync.

## Проверка контейнера

```bash
docker build -t maxsupport:verification .
```

Сборка не требует токенов. Для запуска замените literal placeholders в
Compose-конфигурации через интерфейс управления сервером.
