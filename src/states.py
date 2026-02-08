from inspect import signature

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Update


class AnonChatState(StatesGroup):
    message = State()


class SendEmailState(StatesGroup):
    email = State()


class EditPostState(StatesGroup):
    edit_post = State()


class ClearStateMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Update, data: dict):
        state = data.get('state')
        callback = getattr(data.get('handler'), 'callback', None)

        if state and callback and not any(param.annotation is FSMContext for param in signature(callback).parameters.values()):
            await state.clear()

        return await handler(event, data)
