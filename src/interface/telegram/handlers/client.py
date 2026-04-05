from aiogram import F, Router, types

from src.application.use_cases import SupportService


def create_router(support_service: SupportService) -> Router:
    router = Router()

    @router.message(F.chat.type == "private")
    async def on_client_message(message: types.Message):
        if not message.text or not message.text.strip():
            await message.answer("Сообщение не может быть пустым.")
            return

        text = message.text.strip()[:4000]  # Telegram message limit

        await support_service.handle_client_message(
            client_id=message.from_user.id,
            full_name=message.from_user.full_name,
            username=message.from_user.username,
            text=text,
        )
        await message.answer("Ваше сообщение передано поддержке.")

    return router
