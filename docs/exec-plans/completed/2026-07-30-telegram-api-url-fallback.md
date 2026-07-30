# TELEGRAM_API_URL: custom server and fallback

## Контекст

Aiogram уже получает custom API server через `TelegramAPIServer.from_base()`,
но пустая переменная `TELEGRAM_API_URL` не заменяется стандартным адресом
Telegram и приводит к некорректным URL.

## План изменений

1. [x] Зафиксировать тестами custom method/file URL и fallback для пустого значения.
2. [x] Нормализовать `TELEGRAM_API_URL` при загрузке настроек.
3. [x] Уточнить поведение переменной в README.
4. [x] Выполнить `just check`.

## Риски и открытые вопросы

- Пользовательский base URL должен передаваться в официальный механизм aiogram
  без ручной сборки Telegram endpoint.

## Верификация

- Тесты проверяют итоговые method/file URL.
- Пустое и состоящее из пробелов значение возвращает `https://api.telegram.org`.
- `just check` проходит.
