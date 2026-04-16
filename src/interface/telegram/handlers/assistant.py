from aiogram import F, Router, types

from src.application.use_cases import SupportService


def create_router(support_service: SupportService) -> Router:
    router = Router()

    @router.callback_query(F.data.startswith("take:"))
    async def on_take_ticket(callback: types.CallbackQuery):
        ticket_id = callback.data.split(":")[1]

        # Проверка роли
        if not await support_service.is_assistant(callback.from_user.id):
            await callback.answer("У вас нет прав для этого действия.", show_alert=True)
            return

        await support_service.take_ticket(
            ticket_id,
            callback.from_user.id,
            callback.from_user.username or callback.from_user.full_name,
        )
        await callback.answer("Вы взяли тикет в работу.")
        # Опционально: отредактировать сообщение, удалив кнопку или заменив её
        try:
            await callback.message.edit_reply_markup(
                reply_markup=support_service.sender.get_taken_keyboard(
                    ticket_id, callback.from_user.username or callback.from_user.full_name
                )
            )
        except Exception:
            pass

    @router.callback_query(F.data.startswith("close:"))
    async def on_close_ticket(callback: types.CallbackQuery):
        ticket_id = callback.data.split(":")[1]

        if not await support_service.is_assistant(callback.from_user.id):
            await callback.answer("У вас нет прав.", show_alert=True)
            return

        await support_service.close_ticket(
            ticket_id,
            callback.from_user.id,
            callback.from_user.username or callback.from_user.full_name,
        )
        await callback.answer("Тикет закрыт.")

    @router.callback_query(F.data.startswith("another:"))
    async def on_another_question(callback: types.CallbackQuery):
        ticket_id = callback.data.split(":")[1]

        if not await support_service.is_assistant(callback.from_user.id):
            await callback.answer("У вас нет прав.", show_alert=True)
            return

        await support_service.handle_another_question(
            ticket_id,
            callback.from_user.id,
            callback.from_user.username or callback.from_user.full_name,
        )
        await callback.answer("Тикет закрыт. Попросите клиента написать новый вопрос.")

    @router.message(F.message_thread_id)
    async def on_assistant_reply(message: types.Message):
        if not message.text:
            return

        # Проверка роли
        if not await support_service.is_assistant(message.from_user.id):
            return

        # Ищем тикет по topic_id
        ticket = await support_service.repo.get_ticket_by_topic(message.message_thread_id)
        if not ticket:
            return

        await support_service.handle_assistant_reply(
            assistant_id=message.from_user.id,
            ticket_id=ticket.ticket_id,
            text=message.text,
            username=message.from_user.username or message.from_user.full_name,
        )

    return router
