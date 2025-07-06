from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, BotCommand
from aiogram.fsm.context import FSMContext
from aiogram import Bot
import requests
from database.db import BotDatabase
from settings.config import API_URL, HEADER


start_router = Router()
db = BotDatabase()


async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="setup", description="🔧 Настройка"),
        BotCommand(command='upload', description='📦 Загрузить/Выгрузить'),
        BotCommand(command='information', description='❗Информация')
    ]
    await bot.set_my_commands(commands)


@start_router.message(Command('start'))
async def start_with_token(message: Message, state: FSMContext):
    """Обработка /start с токеном."""
    await state.clear()
    chat_id = message.chat.id
    args = message.text.split(maxsplit=1)
    token = args[1] if len(args) > 1 else None

    if token:
        response = requests.post(
            f"{API_URL}/telegram/verify-token/",
            headers=HEADER,
            data={"token": token, "chat_id": chat_id},
            verify=False
        )

        data = response.json()
        if data.get("status") == "success":
            email = data.get("email")
            if not email:
                await message.answer("❌ Не получили почту от сервера!")
            db.add_user(chat_id, email, is_allowed=True)
            await message.answer("✅ Ваш Telegram успешно привязан!")
            await show_menu(message)
        else:
            await message.answer(f"❌ Ошибка: {data.get('error', 'Токен неверный')}")
    else:
        if not db.is_user_allowed(chat_id):
            await message.answer("❌ У вас нет доступа к боту.")
        else:
            await show_menu(message)


async def show_menu(message: Message):
    """Показывает меню только авторизованным пользователям"""
    await message.answer(
        "👋 *Добро пожаловать!* \n\n"
        "Этот бот поможет вам управлять опросами и загружать данные в систему. В меню доступны следующие команды:\n\n"
        "⚙️ */setup* — Настройки опросника.\n"
        "📂 */upload* — Загрузка данных в базу.\n"
        "ℹ️ */information* — Информация опросникам.\n\n"
        "Выберите команду из меню или введите её вручную.",
        parse_mode="Markdown"
    )
