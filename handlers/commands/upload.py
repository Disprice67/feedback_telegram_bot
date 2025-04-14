from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from keyboards.inline_keyboards import upload_inline_keyboard
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from utils import read_excel, validate_columns, get_file_stream, get_category_config
import requests
from settings.config import HEADERS
from io import BytesIO
from aiogram.types import BufferedInputFile
from datetime import datetime


upload_router = Router()

@upload_router.message(Command('upload'))
async def upload(message: Message, state: FSMContext):
    """Начальная команда /upload"""
    await state.clear()

    await message.answer(
        "📂 *Загрузка данных*\n\n"
        "Здесь вы можете загрузить информацию в базу данных.\n\n"
        "🧭 *Рекомендуемый порядок действий:*\n"
        "1️⃣ Сначала загрузите *инженеров* — если появились новые.\n"
        "2️⃣ Затем загрузите *кейсы*.\n"
        "3️⃣ После этого загрузите *активности* — они связаны с кейсами и инженерами.\n"
        "📥 *Формат файла:* XLSX.\n\n"
        "❗❗Обязательно соблюдайте порядок загрузки❗❗\n\n"
        "🔎 *Важно:* система автоматически проверяет содержимое файла на наличие обязательных столбцов и формат данных перед загрузкой. "
        "Если файл окажется некорректным — вы получите уведомление об ошибке.\n\n"
        "🔽 Выберите категорию для загрузки ниже:",
        parse_mode="Markdown",
        reply_markup=upload_inline_keyboard()
    )


class UploadStates(StatesGroup):
    category = State()
    waiting_for_file = State()


categorys = {
    "upload_cases": "Кейсы",
    "upload_engineers": "Инженеры",
    "upload_managers": "Активности",
}

@upload_router.callback_query(F.data.in_(["upload_cases", "upload_engineers", "upload_managers", 'download_xlsx']))
async def choose_category(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор категории и запрашивает файл."""
    await state.update_data(category=callback.data)
    if callback.data == 'download_xlsx':
        dowload_config = get_category_config(callback.data)
        await callback.message.answer("⚠️ Скачиваю...")
        await handle_download_xlsx(callback, dowload_config["url"])
        return
    else:
        await callback.message.answer(
            f"📂 Вы выбрали категорию: *{categorys[callback.data]}*.\n\n"
            "🔄 Теперь отправьте файл.",
            parse_mode="Markdown",
        )
        await state.set_state(UploadStates.waiting_for_file)


async def handle_download_xlsx(callback: CallbackQuery, url: str):
    try:
        response = requests.get(url, headers=HEADERS, verify=False)
        response.raise_for_status()

        file_bytes = BytesIO(response.content)
        file_bytes.name = f"export_{datetime.now().strftime('%Y-%m-%d')}.xlsx"

        xlsx_file = BufferedInputFile(file_bytes.read(), filename="export.xlsx")

        await callback.message.answer_document(xlsx_file, caption="✅ Финальная выгрузка")
    except Exception as e:
        await callback.message.answer(f"❌ Не удалось скачать файл.\nОшибка: {str(e)}")


@upload_router.message(F.document, UploadStates.waiting_for_file)
async def handle_file_upload(message: Message, state: FSMContext):
    file_name = message.document.file_name
    if not file_name.lower().endswith('.xlsx'):
        await message.answer("❌ Неверный формат! Отправьте файл с расширением *XLSX*.", parse_mode="Markdown")
        return

    state_data = await state.get_data()
    category = state_data.get('category')
    config = get_category_config(category)

    if not config:
        await message.answer("❌ Неизвестная категория загрузки.")
        return

    file_stream = await get_file_stream(message)

    df = read_excel(file_stream)
    if df is None:
        await message.answer("❌ Ошибка при чтении Excel-файла.")
        return

    if not validate_columns(df, config['columns']):
        await message.answer(build_error_message(config['columns']), parse_mode="HTML")
        return

    await message.answer("⚠️ Началась обработка и загрузка данных в БД.\n\nНеобходимо подождать 👀")
    response = await upload_xlsx_to_api(file_stream, config['url'])

    await handle_upload_response(message, response)
    await state.clear()


async def upload_xlsx_to_api(file_stream: BytesIO, url: str) -> requests.Response:
    file_stream.seek(0)
    return requests.post(
        url,
        headers=HEADERS,
        files={'file': ('uploaded_file.xlsx', file_stream, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')},
        verify=False
    )


async def handle_upload_response(message, response):
    try:
        data = response.json()
    except Exception:
        await message.answer("❌ Ошибка сервера. Попробуйте позже.", parse_mode="Markdown")
        return

    if response.status_code == 201:
        msg = f"✅ {data.get('message', 'Файл успешно загружен!')}\n"

        new_users = data.get("new_users")
        if new_users:
            msg += "\n👥 *Добавлены пользователи:*\n"
            for user in new_users:
                name = str(user.get("first_name", "")).strip().title()
                email = user.get("email", "—")
                msg += f"- {name} – {email}\n"

        await message.answer(msg, parse_mode="Markdown")

    elif response.status_code == 400:
        errors = data if isinstance(data, dict) else {"error": "Ошибка валидации."}
        msg = "❌ *Ошибки загрузки:*\n"
        for field, messages in errors.items():
            if isinstance(messages, list):
                for m in messages:
                    msg += f"- *{field}*: {m}\n"
            else:
                msg += f"- *{field}*: {messages}\n"
        await message.answer(msg, parse_mode="Markdown")

    else:
        error = data.get("error", f"Неизвестная ошибка ({response.status_code})")
        await message.answer(f"❌ {error}", parse_mode="Markdown")


def build_error_message(columns: list[str]) -> str:
    return (
        "❌ Ошибка! Проверьте файл, он должен содержать следующие столбцы:\n\n"
        + ", ".join(columns)
    )
