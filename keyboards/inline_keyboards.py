from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta


WEEKDAYS_RU = {
    0: "Понедельник",
    1: "Вторник",
    2: "Среда",
    3: "Четверг",
    4: "Пятница",
    5: "Суббота",
    6: "Воскресенье",
}


def emails_start_inline_keyboard():
    """Устанавливаем дату начала опроса, исключая выходные."""
    keyboards = []
    date = datetime.today()

    while len(keyboards) < 5:
        if date.weekday() < 5:
            formatted_date = date.strftime('%d.%m.%Y')
            weekday_ru = WEEKDAYS_RU[date.weekday()]
            keyboards.append([InlineKeyboardButton(text=f"{formatted_date} ({weekday_ru})", 
                                                   callback_data=f'start_{formatted_date}')])
        date += timedelta(days=1)

    return InlineKeyboardMarkup(inline_keyboard=keyboards)


def emails_end_inline_keyboard(start_date: str):
    """Устанавливаем дату окончания опроса, исключая выходные."""
    keyboards = []
    start_date = datetime.strptime(start_date, '%d.%m.%Y')
    date = start_date + timedelta(days=10)

    while len(keyboards) < 5:
        if date.weekday() < 5:
            formatted_date = date.strftime('%d.%m.%Y')
            weekday_ru = WEEKDAYS_RU[date.weekday()]
            keyboards.append([InlineKeyboardButton(text=f"{formatted_date} ({weekday_ru})", 
                                                   callback_data=f'end_{formatted_date}')])
        date += timedelta(days=1)

    return InlineKeyboardMarkup(inline_keyboard=keyboards)


def emails_accept_settings_keyboard():
    keyboards = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="confirm_mailing")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="cancel_mailing")]
    ])
    return keyboards


def setup_inline_keyboard():
    """Inline-кнопки для настроек."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔧 Рассылка", callback_data="setup_option_1")],
    ])


def upload_inline_keyboard():
    """Inline-кнопки для загрузки данных."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📂 Инженеры", callback_data="upload_engineers")],
        [InlineKeyboardButton(text="📂 Кейсы", callback_data="upload_cases")],
        [InlineKeyboardButton(text="📂 Активности", callback_data="upload_managers")],
        [InlineKeyboardButton(text="❗ Финальная выгрузка", callback_data="download_xlsx")],
    ])


def information_inline_keyboard():
    """Inline-кнопки для информации."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ℹ️ Список опрашиваемых", callback_data="info_option_1")],
        [InlineKeyboardButton(text="ℹ️ Вопросы для проектов", callback_data="info_option_2")],
        [InlineKeyboardButton(text="ℹ️ Настройки рассылки", callback_data="info_option_3")],
        [InlineKeyboardButton(text="ℹ️ Письмо для рассылки", callback_data="info_option_4")],
    ])
