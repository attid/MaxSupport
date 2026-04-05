import re

from aiogram import F, Router, types

from src.application.use_cases import SupportService


def create_router(support_service: SupportService) -> Router:
    router = Router()

    @router.message(F.reply_to_message)
    async def on_assistant_reply(message: types.Message):
        if not message.text:
            return

        # Извлекаем ID тикета из сообщения, на которое отвечает ассистент
        original_text = message.reply_to_message.text
        if not original_text:
            await message.reply(
                "Не удалось определить ID тикета из сообщения. "
                "Убедитесь, что отвечаете на правильное сообщение бота."
            )
            return

        # Ищем UUID в тексте
        match = re.search(
            r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
            original_text,
            re.IGNORECASE,
        )
        if not match:
            await message.reply(
                "Не удалось определить ID тикета. Убедитесь, что отвечаете на сообщение бота."
            )
            return

        ticket_id = match.group(1)

        await support_service.handle_assistant_reply(
            assistant_id=message.from_user.id,
            ticket_id=ticket_id,
            text=message.text,
        )
        await message.reply("Отправлено клиенту.")

    return router
