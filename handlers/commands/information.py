from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from keyboards.inline_keyboards import information_inline_keyboard, cancel_existing_mailing_keyboard
from aiogram.fsm.context import FSMContext
import requests
from settings.config import API_URL, HEADER
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime


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
        await callback.message.delete()
        loading_msg = await callback.message.answer("🔄 Запрос на сервер...")
        response = requests.get(f'{API_URL}/stats/all', headers=HEADER, verify=False)
        response_data = response.json()

        engineers = response_data.get("engineers", [])
        total_feedbacks = response_data.get("total_feedbacks", {})

        message_text = "📋 *Список опрашиваемых инженеров:*\n\n"
        message_text += "👷‍♂️ **Имя Фамилия** — **Отправлено/Не отправлено**\n\n"


        if not engineers:
            message_text += "Нет инженеров с проектами.\n"
        else:
            for engineer in engineers:
                message_text += (
                    f"👷‍♂️ {engineer['engineer']} — "
                    f"{engineer['feedback_stats']}\n"
                )

        message_text += "\n📊 *Общая статистика:*\n"
        message_text += f"✅ Отправлено: {total_feedbacks.get('total_sent', 0)}\n"
        message_text += f"❌ Не отправлено: {total_feedbacks.get('total_unsent', 0)}\n"

        await loading_msg.edit_text(message_text, parse_mode="Markdown")

    except Exception as e:
        await loading_msg.edit_text("❌ Произошла ошибка при получении данных. Попробуйте позже.")


@information_router.callback_query(F.data.in_(['info_option_2']))
async def list_project_questions(callback: CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Вопросы для проектов'"""
    await callback.message.delete()
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


def create_mailing_list_keyboard(mailings):
    """Создает клавиатуру со списком всех рассылок."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for mailing in mailings:
        button_text = f"{mailing['period_name']}"
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"mailing_info_{mailing['id']}"
            )
        ])
    return keyboard


def create_mailing_action_keyboard(mailing_id, status):
    """Создает клавиатуру для действий с рассылкой."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    if status != 'completed':
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text="❌ Отменить рассылку",
                callback_data=f"cancel_mailing_{mailing_id}"
            )
        ])
    return keyboard


@information_router.callback_query(F.data == "info_option_3")
async def show_mailing_list(callback: CallbackQuery):
    """Показывает список рассылок с правильной обработкой пустого состояния"""
    await callback.message.delete()
    try:
        loading_msg = await callback.message.answer("🔄 Получаем список рассылок...")

        response = requests.get(
            f"{API_URL}/mailing/all/",
            headers=HEADER,
            verify=False,
        )
        response.raise_for_status()

        data = response.json()
        if not data or 'data' not in data:
            raise ValueError("Неверный формат ответа от сервера")

        if not data['data']:
            await loading_msg.edit_text("⚠️ Нет активных рассылок")
        else:
            await loading_msg.edit_text(
                "📋 Выберите опросник:",
                reply_markup=create_mailing_list_keyboard(data['data'])
            )

    except requests.exceptions.RequestException as e:
        error_detail = str(e)
        if isinstance(e, requests.exceptions.Timeout):
            error_detail = "Сервер не отвечает (таймаут)"
        elif isinstance(e, requests.exceptions.HTTPError):
            error_detail = f"HTTP ошибка: {e.response.status_code}"

        await loading_msg.edit_text(f"🚫 Ошибка запроса: {error_detail}")

    except ValueError as e:
        await loading_msg.edit_text(f"🚫 Ошибка данных: {str(e)}")

    except Exception as e:
        await loading_msg.edit_text(f"🚫 Неожиданная ошибка: {str(e)}")


@information_router.callback_query(F.data.startswith("mailing_info_"))
async def show_mailing_info(callback: CallbackQuery):
    """Показывает информацию о выбранной рассылке."""
    await callback.message.delete()
    try:
        mailing_id = callback.data.split("_")[-1]
        loading_msg = await callback.message.answer("🔄 Запрос на сервер...")

        response = requests.get(
            f"{API_URL}/mailing/{mailing_id}/",
            headers=HEADER,
            verify=False
        )
        response.raise_for_status()
        mailing_data = response.json()

        stats_mailing = mailing_data.get('statistics', '')
        feedback_stats = None
        if not stats_mailing:
            stats_response = requests.get(
                f"{API_URL}/stats/count/{mailing_id}/",
                headers=HEADER,
                verify=False
            )
            feedback_stats = stats_response.json()

        tasklog_response = requests.get(
            f"{API_URL}/mailing/tasklog/{mailing_id}/",
            headers=HEADER,
            verify=False
        )
        task_logs = tasklog_response.json()
        start_date_formated = datetime.strptime(mailing_data.get('start_date', '-'), "%Y-%m-%d").strftime("%d.%m.%Y")
        end_date_formated = datetime.strptime(mailing_data.get('end_date', '-'), "%Y-%m-%d").strftime("%d.%m.%Y")

        message_text = f"✉️ *Информация о опроснике:*\n\n"
        message_text += f"📅 **Период**: {mailing_data.get('period_name', 'Не указано')}\n"
        message_text += f"🗓 **Дата начала**: {start_date_formated}\n"
        message_text += f"🗓 **Дата окончания**: {end_date_formated}\n"
        message_text += f"📈 **Статус**: {mailing_data.get('status_display', '-')}\n"

        intermediate_dates = mailing_data.get('intermediate_dates', [])
        if intermediate_dates:
            message_text += "\n📍 **Даты рассылок**:\n"
            if task_logs and tasklog_response.status_code == 200:
                status_mapping = {
                        'CREATE': 'Запланирована',
                        'SUCCESS': 'Выполнена',
                        'FAILURE': 'Ошибка',
                        'SKIPPED': 'Пропущено',
                        'RETRY': 'Повтор'
                    }
                for date in intermediate_dates:
                    matching_task = next(
                        (task for task in task_logs if task['scheduled_date'] == date and task['task_name'] == 'send_emails'),
                        None
                    )
                    status = matching_task['status'] if matching_task else "Не выполнено"
                    status_display = status_mapping.get(status, status)
                    status_emoji = {
                        'CREATE': '⏳',
                        'SUCCESS': '✅',
                        'FAILURE': '❌',
                        'SKIPPED': '⏭️',
                        'RETRY': '🔄'
                    }.get(status, '⚪')
                    date_formated = datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m.%Y")
                    message_text += f"- {date_formated} {status_emoji} {status_display}\n"
            else:
                for date in intermediate_dates:
                    date_formated = datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m.%Y")
                    message_text += f"- {date_formated}\n"
        else:
            message_text += "\n📍 **Промежуточные даты**: Отсутствуют\n"

        if not stats_mailing:
            if feedback_stats and stats_response.status_code == 200:
                message_text += "\n📋 **Статистика отзывов**:\n"
                message_text += f"✅ Отправлено: {feedback_stats.get('total_sent', 0)}\n"
                message_text += f"⏳ Не отправлено: {feedback_stats.get('total_unsent', 0)}\n"
            elif stats_response.status_code == 404:
                message_text += f"\n⚠️ **{feedback_stats.get('detail', 'Статистика недоступна')}** \n"
        else:
            message_text += "\n📋 **Статистика отзывов**:\n"
            message_text += f"✅ Отправлено: {stats_mailing.get('total_sent', 0)}\n"
            message_text += f"⏳ Не отправлено: {stats_mailing.get('total_unsent', 0)}\n"

        await loading_msg.edit_text(
            message_text,
            parse_mode="Markdown",
            reply_markup=create_mailing_action_keyboard(mailing_data['id'], mailing_data['status'])
        )
    except requests.exceptions.RequestException as e:
        await loading_msg.edit_text(f"🚫 Ошибка при получении информации о рассылке: {str(e)}")


@information_router.callback_query(F.data.startswith("cancel_mailing_"))
async def cancel_mailing(callback: CallbackQuery):
    """Обрабатываем отмену выбранной рассылки."""
    await callback.message.delete()
    try:
        mailing_id = callback.data.split("_")[-1]
        response = requests.get(
            f"{API_URL}/mailing/{mailing_id}/",
            headers=HEADER,
            verify=False
        )
        response.raise_for_status()
        mailing_data = response.json()

        if mailing_data['status'] == 'completed':
            await callback.message.answer("🚫 Нельзя отменить завершенную рассылку.")
            return

        response = requests.delete(
            f"{API_URL}/mailing/{mailing_id}/",
            headers=HEADER,
            verify=False
        )
        response.raise_for_status()
        await callback.message.answer(
            "✅ *Рассылка отменена*\n"
            f"📌 Период: `{mailing_data['period_name']}`\n",
            parse_mode="Markdown"
        )
    except requests.exceptions.RequestException as e:
        await callback.message.answer(f"❗ Ошибка при отмене рассылки: {str(e)}")
    await callback.answer()
