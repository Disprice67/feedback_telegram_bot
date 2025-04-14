from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
import requests
from keyboards.inline_keyboards import emails_start_inline_keyboard, emails_end_inline_keyboard, emails_accept_settings_keyboard


mailing_router = Router()

class MailingStates(StatesGroup):
    start_date = State()
    end_date = State()
    intermediate_dates = State()
    confirmation = State()

WEEKDAYS_RU = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

@mailing_router.callback_query(F.data.in_(['setup_option_1']))
async def setup_emails(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки рассылка."""
    await state.clear()
    await callback.message.answer('Выберите дату начала опросника', reply_markup=emails_start_inline_keyboard())
    await state.set_state(MailingStates.start_date)

@mailing_router.callback_query(MailingStates.start_date)
async def start_date(callback: CallbackQuery, state: FSMContext):
    """Обрабатываем дату начала опросника."""
    start_date = callback.data.replace('start_', '')
    await state.update_data(start_date=datetime.strptime(start_date, '%d.%m.%Y'))
    await callback.message.answer(f'\U0001F4A1Дата начала: {start_date}\n\nВыберите дату окончания:',
                                  reply_markup=emails_end_inline_keyboard(start_date))
    await state.set_state(MailingStates.end_date)
    await callback.answer()

@mailing_router.callback_query(MailingStates.end_date)
async def end_date(callback: CallbackQuery, state: FSMContext):
    """Обрабатываем дату окончания опросника."""
    end_date = callback.data.replace('end_', '')
    await state.update_data(end_date=datetime.strptime(end_date, '%d.%m.%Y'))
    await callback.message.answer(f'💡Дата окончания: {end_date}')
    await state.set_state(MailingStates.intermediate_dates)

    await intermediate_dates(callback, state)

@mailing_router.callback_query(MailingStates.intermediate_dates)
async def intermediate_dates(callback: CallbackQuery, state: FSMContext):
    """Обрабатываем даты повторных рассылок."""
    data = await state.get_data()
    intermediate_dates = calculate_intermediate_dates(data['start_date'], data['end_date'])
    await state.update_data(intermediate_dates=intermediate_dates)
    dates_text = '\n\n'.join(intermediate_dates)
    total_days = (data['end_date'] - data['start_date']).days + 1
    text = (
        f"📢 *Настройка рассылки* 📢\n\n"
        f"📅 *Начало опроса:* {data['start_date'].date()}\n"
        f"⏳ *Конец опроса:* {data['end_date'].date()}\n\n"
        f"📆 *Всего дней опроса:* {total_days}\n\n"
        f"🔁 *Даты повторных рассылок:*\n{dates_text}\n\n"
        f"✅ *Сохранить рассылку?*"
    )

    await callback.message.answer(text, reply_markup=emails_accept_settings_keyboard())
    await state.set_state(MailingStates.confirmation)
    await callback.answer()

@mailing_router.callback_query(MailingStates.confirmation)
async def confirm_mailing(callback: CallbackQuery, state: FSMContext):
    """Подтверждение сохранения рассылки."""
    if callback.data == 'confirm_mailing':
        data = await state.get_data()
        intermediate_dates = [
            datetime.strptime(d.split(" ")[0], "%d.%m.%Y") for d in data["intermediate_dates"]
        ]
        payload = {
            "chat_id": callback.from_user.id,
            "start_date": data["start_date"].strftime("%Y-%m-%d"),
            "end_date": data["end_date"].strftime("%Y-%m-%d"),
            "intermediate_dates": [d.strftime("%Y-%m-%d") for d in intermediate_dates],
        }
        response = requests.post(API_URL, json=payload)
        if response.status_code == 201:
            await callback.message.answer("✅ Рассылка сохранена в системе!")
        else:
            await callback.message.answer("❌ Ошибка сохранения рассылки.")
        await state.clear()
    elif callback.data == 'cancel_mailing':
        await callback.message.answer("❌ Настройки отменены!")
        await state.clear()
        await callback.message.answer("🔄 Давайте начнем заново!\n\nВыберите дату начала:",
                                      reply_markup=emails_start_inline_keyboard())
        await state.set_state(MailingStates.start_date)
    await callback.answer()

def calculate_intermediate_dates(start_date: datetime, end_date: datetime) -> list[str]:
    dates = [f"{start_date.strftime('%d.%m.%Y')} ({WEEKDAYS_RU[start_date.weekday()]})"]
    mid_date = get_next_weekday(start_date + (end_date - start_date) / 2)
    dates.append(f"{mid_date.strftime('%d.%m.%Y')} ({WEEKDAYS_RU[mid_date.weekday()]})")

    last_date = get_next_weekday(end_date - timedelta(days=1))
    dates.append(f"{last_date.strftime('%d.%m.%Y')} ({WEEKDAYS_RU[last_date.weekday()]})")
    return dates

def get_next_weekday(date: datetime) -> datetime:
    if date.weekday() == 5: return date - timedelta(days=1)
    if date.weekday() == 6: return date - timedelta(days=2)
    return date
