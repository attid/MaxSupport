import re
from aiogram import Router, F, types
from src.application.use_cases import SupportService
from src.infrastructure.config import config

router = Router()

# Ограничиваем этот роутер только чатом ассистентов
router.message.filter(F.chat.id == config.assistants_chat_id)


@router.message(F.reply_to_message)
async def on_assistant_reply(message: types.Message, support_service: SupportService):
    if not message.text:
        return

    # Извлекаем ID тикета из сообщения, на которое отвечает ассистент
    # Ожидаемый формат: "Новый тикет <uuid> от ..." или "Тикет <uuid> | Клиент ..."
    original_text = message.reply_to_message.text
    if not original_text:
        return

    # Ищем UUID в тексте
    match = re.search(
        r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", original_text
    )
    if not match:
        await message.reply(
            "Не удалось определить ID тикета из сообщения. Убедитесь, что отвечаете на правильное сообщение бота."
        )
        return

    ticket_id = match.group(1)

    await support_service.handle_assistant_reply(
        assistant_id=message.from_user.id, ticket_id=ticket_id, text=message.text
    )
    # Можно добавить реакцию (эмодзи) на сообщение ассистента, чтобы показать, что оно доставлено
    # Но для MVP просто отправим подтверждение
    await message.reply("Отправлено клиенту.")
