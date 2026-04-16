# Авторизация ассистентов — membership вместо DB role

## Контекст
`is_assistant` проверял наличие user в БД с ролью ASSISTANT, но механизма
регистрации ассистентов не было. Кнопка "Взять" и ответы в топик не работали.

## План изменений
1. [x] `is_assistant` → проверка членства в `ASSISTANTS_CHAT_ID` через `get_chat_member`
2. [x] Добавлен `is_chat_member` в `BotSenderInterface` и `BotSender`
3. [x] Добавлен `_ensure_assistant` — автосоздание user в БД при первом действии (FK integrity)
4. [x] Игнорирование `TOPIC_NOT_MODIFIED` при повторном переименовании топика
5. [x] Обновлены тесты

## Коммиты
- `5529b52` fix(auth): check assistants chat membership instead of DB role
- `78d8e04` fix(db): auto-create assistant user before FK assignment
- `4817001` fix(telegram): ignore TOPIC_NOT_MODIFIED error on rename
