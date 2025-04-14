from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message
from keyboards.inline_keyboards import setup_inline_keyboard
from aiogram.fsm.context import FSMContext


setup_router = Router()

@setup_router.message(Command('setup'))
async def setup(message: Message, state: FSMContext):
    """Начальная команда /setup"""
    await state.clear()
    await message.answer(
        "⚙️ *Настройки опросника*\n\n"
        "Здесь вы можете изменить параметры опроса. Выберите, что хотите настроить:",
        parse_mode="Markdown",
        reply_markup=setup_inline_keyboard()
    )
