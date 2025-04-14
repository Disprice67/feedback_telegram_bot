from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from keyboards.inline_keyboards import information_inline_keyboard
from aiogram.fsm.context import FSMContext
import requests
from settings.config import URL_WEB_SITE, HEADERS
import tempfile
from aiogram.types import FSInputFile


information_router = Router()

@information_router.message(Command('information'))
async def information(message: Message, state: FSMContext):
    """Начальная команда /information"""
    await state.clear()
    await message.answer(
        "ℹ️ *Информация по опроснику* \n\n"
        "Здесь вы можете ознакомиться с подробной информацией по текущему опроснику. Выберите действие из меню:",
        parse_mode="Markdown",
        reply_markup=information_inline_keyboard()
    )


@information_router.callback_query(F.data.in_(['info_option_1']))
async def list_engineers(callback: CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Список опрашиваемых'"""
    try:
        response = requests.get(f'{URL_WEB_SITE}api/v1/engineers/stats/', headers=HEADERS, verify=False)
        response_data = response.json()

        engineers = response_data.get("engineers", [])
        total_feedbacks = response_data.get("total_feedbacks", {})

        message_text = "📋 *Список опрашиваемых инженеров:*\n\n"
        message_text += "👷‍♂️ **Имя Фамилия** — **Отправлено/Не отправлено**\n\n"


        if not engineers:
            message_text += "Нет инженеров с отзывами.\n"
        else:
            for engineer in engineers:
                message_text += (
                    f"👷‍♂️ {engineer['engineer']} — "
                    f"{engineer['feedback_stats']}\n"
                )

        message_text += "\n📊 *Общая статистика:*\n"
        message_text += f"✅ Отправлено: {total_feedbacks.get('total_sent', 0)}\n"
        message_text += f"❌ Не отправлено: {total_feedbacks.get('total_unsent', 0)}\n"

        await callback.message.answer(message_text, parse_mode="Markdown")

    except Exception as e:
        await callback.message.answer("❌ Произошла ошибка при получении данных. Попробуйте позже.")


@information_router.callback_query(F.data.in_(['info_option_2']))
async def list_project_questions(callback: CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Вопросы для проектов'"""
    labels = {
        'first_question': '❓ Требовалась ли тебе помощь менеджера при решении кейсов?',
        'second_question': '❓ Участвовал ли менеджер в решении кейсов?',
        'third_question': '❓ Было ли это участие полезным?',
        'fourth_question': '❓ Есть ли у тебя вопросы по текущему проекту, которые нужно обсудить с менеджером?',
        'fourth_comment_question': '💬 Вопросы по проекту:',
        'rating': '⭐ Оцени работу менеджера в проекте по шкале от -1 до 2, где:',
        'comment': '📝 Комментарий (поле свободное для заполнения):',
    }

    message_text = "📋 *Вопросы для проектов:*\n\n"
    for key, question in labels.items():
        message_text += f"{question}  \n"

    await callback.message.answer(message_text, parse_mode="Markdown")


@information_router.callback_query(F.data == "info_option_4")
async def show_email_template(callback: CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Письмо для рассылки' — показывает HTML шаблон письма."""
    try:
        response = requests.get(
            f"{URL_WEB_SITE}api/v1/email-template/preview/",
            headers=HEADERS,
            verify=False
        )
        response.raise_for_status()
        rendered_template = response.json().get("template", "")

        if not rendered_template:
            await callback.message.answer("⚠️ Не удалось получить шаблон письма.")
            return

        with tempfile.NamedTemporaryFile("w+", suffix=".html", delete=False, encoding="utf-8") as tmp:
            tmp.write(rendered_template)
            tmp_path = tmp.name

        document = FSInputFile(tmp_path, filename="email_template.html")
        await callback.message.answer_document(
            document,
            caption="📨 Шаблон письма для рассылки"
        )

    except Exception as e:
        await callback.message.answer("🚫 Произошла ошибка при получении шаблона письма.")
