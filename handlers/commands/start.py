from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, BotCommand
from aiogram.fsm.context import FSMContext
from aiogram import Bot

start_router = Router()


async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="setup", description="🔧 Настройка"),
        BotCommand(command='upload', description='📦 Загрузить/Выгрузить'),
        BotCommand(command='information', description='❗Информация')
    ]
    await bot.set_my_commands(commands)


@start_router.message(Command('start'))
async def start(message: Message, state: FSMContext):
    """Начальная команда /start"""
    await state.clear()
    await message.answer(
        "👋 *Добро пожаловать!* \n\n"
        "Этот бот поможет вам управлять опросами и загружать данные в систему. В меню доступны следующие команды:\n\n"
        "⚙️ */setup* — Настройки опросника.\n"
        "📂 */upload* — Загрузка данных в базу.\n"
        "ℹ️ */information* — Информация по текущему опросу.\n\n"
        "Выберите команду из меню или введите её вручную.",
        parse_mode="Markdown"
    )
