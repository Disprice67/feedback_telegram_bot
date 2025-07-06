from aiogram import types
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from database.db import BotDatabase

db = BotDatabase()


class AccessMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):

        if isinstance(event, types.Message):
            chat_id = event.chat.id

            if event.text and event.text.startswith('/start'):
                return await handler(event, data)
 
            if not db.is_user_allowed(chat_id):
                await event.answer("❌ У вас нет доступа к боту.")
                return

        return await handler(event, data)