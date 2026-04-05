from aiogram import Router, types, F
from src.application.use_cases import SupportService

router = Router()


@router.message(F.chat.type == "private")
async def on_client_message(message: types.Message, support_service: SupportService):
    if not message.text:
        return

    await support_service.handle_client_message(
        client_id=message.from_user.id,
        full_name=message.from_user.full_name,
        username=message.from_user.username,
        text=message.text,
    )
    # Можно добавить подтверждение клиенту
    # await message.answer("Ваше сообщение передано поддержке.")
