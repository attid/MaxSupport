# Пересылка файлов между Max и Telegram

## Контекст
Поддержка отправки/приёма только текста. Клиенты и ассистенты не могли обмениваться файлами.

## План изменений

### Модель данных
1. [x] `Attachment` (type, url, filename, token, file_data) и `AttachmentType` enum в domain
2. [x] `max_chat_id` поле в Ticket и БД

### Max → Telegram
3. [x] Polling извлекает `body.attachments`, создаёт `Attachment` объекты
4. [x] Поддерживаемые: `image`, `file`, `audio`
5. [x] Неподдерживаемые (`sticker`, `location`) → ответ "формат не поддерживается"
6. [x] Файлы скачиваются на диск `/tmp/maxsupport_attachments/` и отправляются через `FSInputFile`
7. [x] `image` → `send_photo`, `file`/`audio` → `send_document`
8. [x] Генерация имён: `audio_<id>.mp3`, `image_<id>.jpg`

### Telegram → Max
9. [x] Хэндлер ловит `photo`, `document`, `audio`, `voice`
10. [x] Скачивает из TG через `bot.download_file`
11. [x] Загружает на Max через `POST /uploads` → получает URL → POST файл → token
12. [x] Отправляет `POST /messages` с `attachments` (type=file для всех uploaded)
13. [x] Retry при `attachment.not.ready` (до 3 попыток, 2с задержка)

### Разделение сообщений
14. [x] Текст + вложения из Max → два сообщения в TG (текст, потом файлы)
15. [x] Текст + вложения из TG → одно сообщение в Max (API поддерживает)

## Верификация
- Протестировано с живым API: фото, PDF, аудио, стикер, геолокация
- 23 теста, все зелёные

## Коммиты
- `da3311a` feat: add file forwarding between Max and Telegram
- `e1b5e79` fix(max): send uploaded attachments as file type
- `65ecd9a` fix(max): always include text field and log response body on error
- `28aa73d` fix(max): retry on attachment.not.ready when sending files
- `24c8671` fix: generate readable filenames for audio/image attachments
- `126063f` fix(telegram): save attachments to disk before sending to TG
