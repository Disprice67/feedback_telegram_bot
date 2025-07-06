from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from keyboards.inline_keyboards import upload_inline_keyboard
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from utils import read_excel, validate_columns, get_file_stream, get_category_config
from utils.html_preview import generate_engineers_preview, generate_cases_preview, generate_managers_preview
import requests
from settings.config import HEADER
from io import BytesIO
from aiogram.types import BufferedInputFile
from datetime import datetime
import pandas as pd
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


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
        response = requests.get(url, headers=HEADER, verify=False)
        response.raise_for_status()

        file_bytes = BytesIO(response.content)
        file_bytes.name = f"export_{datetime.now().strftime('%Y-%m-%d')}.xlsx"

        xlsx_file = BufferedInputFile(file_bytes.read(), filename="export.xlsx")

        await callback.message.answer_document(xlsx_file, caption="✅ Финальная выгрузка")
    except Exception as e:
        await callback.message.answer(f"❌ Не удалось скачать файл.\nОшибка: {str(e)}")


@upload_router.message(F.document, UploadStates.waiting_for_file)
async def handle_file_upload(message: Message, state: FSMContext):
    state_data = await state.get_data()
    request_message_id = state_data.get('request_message_id')
    chat_id = message.chat.id

    if request_message_id:
        try:
            await message.bot.delete_message(chat_id, request_message_id)
        except Exception:
            pass

    file_name = message.document.file_name
    if not file_name.lower().endswith('.xlsx'):
        await message.answer("❌ Неверный формат! Отправьте файл с расширением *XLSX*.", parse_mode="Markdown")
        return

    category = state_data.get('category')
    config = get_category_config(category)

    if not config:
        await message.answer("❌ Неизвестная категория загрузки.")
        return

    file_stream = await get_file_stream(message)
    file_stream.seek(0)
    file_bytes = file_stream.read()
    file_stream.seek(0)

    df = read_excel(file_stream)
    if df is None:
        await message.answer("❌ Ошибка при чтении Excel-файла.")
        return

    if not validate_columns(df, config['columns']):
        await message.answer(build_error_message(config['columns']), parse_mode="HTML")
        return

    if category == 'upload_engineers':
        preview_html, page, total_pages = generate_engineers_preview(df)
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Вперёд ➡️", callback_data="preview_next")] if total_pages > 1 else [],
            [
                InlineKeyboardButton(text="✅ Отправить", callback_data="preview_send"),
                InlineKeyboardButton(text="❌ Не отправлять", callback_data="preview_cancel")
            ]
        ])
    elif category == 'upload_cases':
        preview_html, page, total_pages = generate_cases_preview(df)
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Вперёд ➡️", callback_data="preview_next")] if total_pages > 1 else [],
            [
                InlineKeyboardButton(text="✅ Отправить", callback_data="preview_send"),
                InlineKeyboardButton(text="❌ Не отправлять", callback_data="preview_cancel")
            ]
        ])
    elif category == 'upload_managers':
        preview_html, page, total_pages = generate_managers_preview(df)
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Вперёд ➡️", callback_data="preview_next")] if total_pages > 1 else [],
            [
                InlineKeyboardButton(text="✅ Отправить", callback_data="preview_send"),
                InlineKeyboardButton(text="❌ Не отправлять", callback_data="preview_cancel")
            ]
        ])
    else:
        await message.answer("⚠️ Началась обработка и загрузка данных в БД.\n\nНеобходимо подождать 👀")
        response = await upload_xlsx_to_api(file_stream, config['url'])
        await handle_upload_response(message, response)
        await state.clear()
        return

    await state.update_data(df=df.to_dict(), page=page, file_stream=file_bytes, category=category)
    await message.answer(preview_html, parse_mode="HTML", reply_markup=markup)


@upload_router.callback_query(F.data.startswith("preview_"))
async def handle_preview_pagination(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает перелистывание страниц, отправку или отмену."""
    action = callback.data.split("_")[1]
    state_data = await state.get_data()
    df_dict = state_data.get('df')
    current_page = state_data.get('page', 0)
    message = callback.message

    if not df_dict:
        await callback.message.edit_text("❌ Данные устарели. Загрузите файл заново.")
        return

    df = pd.DataFrame(df_dict)

    if action == "send":
        await callback.message.delete()
        await callback.message.answer("⚠️ Отправляю данные в БД.\n\nПодождите 👀")
        config = get_category_config(state_data.get('category'))
        file_stream = BytesIO(state_data.get('file_stream'))
        response = await upload_xlsx_to_api(file_stream, config['url'])
        await handle_upload_response(callback.message, response)
        await state.clear()
        return

    if action == "cancel":
        await callback.message.delete()
        await callback.message.answer("❌ Отправка данных отменена.")
        await state.clear()
        return

    if action == "next":
        new_page = current_page + 1
    elif action == "prev":
        new_page = current_page - 1
    else:
        new_page = current_page

    if state_data.get('category') == 'upload_engineers':
        from utils.html_preview import generate_engineers_preview
        preview_html, page, total_pages = generate_engineers_preview(df, new_page)
    elif state_data.get('category') == 'upload_cases':
        preview_html, page, total_pages = generate_cases_preview(df, new_page)
    elif state_data.get('category') == 'upload_managers':
        preview_html, page, total_pages = generate_managers_preview(df, new_page)
    else:
        preview_html, page, total_pages = generate_engineers_preview(df, new_page)

    markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Вперёд ➡️", callback_data="preview_next")] if total_pages > 1 and page < total_pages - 1 else [],
            [
                InlineKeyboardButton(text="✅ Отправить", callback_data="preview_send"),
                InlineKeyboardButton(text="❌ Не отправлять", callback_data="preview_cancel")
            ]
        ])
    if page > 0:
        markup.inline_keyboard.insert(0, [InlineKeyboardButton(text="⬅️ Назад", callback_data="preview_prev")])

    await message.edit_text(preview_html, parse_mode="HTML", reply_markup=markup)
    await state.update_data(page=page)


async def upload_xlsx_to_api(file_stream: BytesIO, url: str) -> requests.Response:
    file_stream.seek(0)
    return requests.post(
        url,
        headers=HEADER,
        files={'file': ('uploaded_file.xlsx', file_stream, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')},
        verify=False
    )


async def handle_upload_response(message, response):
    try:
        data = response.json()
    except Exception:
        await message.answer("❌ Ошибка сервера. Попробуйте позже.", parse_mode="Markdown")
        return

    msg = ""
    if response.status_code == 201:
        msg = f"✅ {data.get('message', 'Файл успешно загружен!')}\n"
        new_users = data.get("new_users")
        if new_users:
            msg += "\n👥 *Добавлены пользователи:*\n"
            for user in new_users:
                first_name = str(user.get("first_name", "")).strip()
                last_name = str(user.get("last_name", "")).strip()
                email = user.get("email", "—")
                msg += f"- {last_name} {first_name} – {email}\n"
    elif response.status_code == 207:
        msg = f"⚠️ {data.get('message', 'Частичная загрузка')}\n"
        missing_users = data.get("missing_users")
        missing_actives = data.get("activities_without_cases")
        if missing_users:
            msg += "\n❌ *Пользователи с кейсами, но без УЗ:*\n"
            for user in missing_users:
                msg += f"- {user}\n"
        serialization_errors = data.get("serialization_errors")
        if serialization_errors:
            msg += "\n❌ *Ошибки валидации кейсов:*\n"
            for error in serialization_errors:
                msg += f"- Строка {error['row']}: {error['errors']}\n"
        if missing_actives:
            msg += "\n❌ *Проекты по которым нет кейсов:*\n"
            for active in missing_actives:
                msg += f"{active}\n"
    elif response.status_code == 400:
        msg = "❌ *Ошибки загрузки:*\n"
        errors = data if isinstance(data, dict) else {"error": "Ошибка валидации."}
        for field, messages in errors.items():
            if isinstance(messages, list):
                for m in messages:
                    msg += f"- *{field}*: {m}\n"
            else:
                msg += f"- *{field}*: {messages}\n"
    else:
        error = data.get("error", f"Неизвестная ошибка ({response.status_code})")
        msg = f"❌ {error}"

    await message.answer(msg,)

def build_error_message(columns: list[str]) -> str:
    return (
        "❌ Ошибка! Проверьте файл, он должен содержать следующие столбцы:\n\n"
        + ", ".join(columns)
    )


def build_error_message(columns: list[str]) -> str:
    return (
        "❌ Ошибка! Проверьте файл, он должен содержать следующие столбцы:\n\n"
        + ", ".join(columns)
    )
