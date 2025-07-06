from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
import requests
from keyboards.inline_keyboards import emails_start_inline_keyboard, emails_end_inline_keyboard, emails_accept_settings_keyboard, cancel_existing_mailing_keyboard_restart, setup_inline_keyboard
from settings.config import API_URL, HEADER
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
import re

mailing_router = Router()


class MailingStates(StatesGroup):
    start_date = State()
    end_date = State()
    intermediate_dates = State()
    confirmation = State()
    cancel_existing = State()


class TestStates(StatesGroup):
    waiting_for_email = State()
    waiting_for_full_name = State()
    waiting_for_confirmation = State()


WEEKDAYS_RU = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

@mailing_router.callback_query(F.data.in_(['setup_option_1']))
async def setup_emails(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки рассылка."""
    await callback.message.delete()
    await state.clear()
    await callback.message.answer('Выберите дату начала опросника:', reply_markup=emails_start_inline_keyboard())
    await state.set_state(MailingStates.start_date)

@mailing_router.callback_query(MailingStates.start_date)
async def start_date(callback: CallbackQuery, state: FSMContext):
    """Обрабатываем дату начала опросника."""
    await callback.message.delete()
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
    await state.set_state(MailingStates.intermediate_dates)

    await intermediate_dates(callback, state)

@mailing_router.callback_query(MailingStates.intermediate_dates)
async def intermediate_dates(callback: CallbackQuery, state: FSMContext):
    """Обрабатываем даты повторных рассылок."""
    await callback.message.delete()
    data = await state.get_data()
    intermediate_dates = calculate_intermediate_dates(data['start_date'], data['end_date'])
    await state.update_data(intermediate_dates=intermediate_dates)
    dates_text = '\n\n'.join(intermediate_dates)
    total_days = (data['end_date'] - data['start_date']).days + 1
    start_date_formatted = data['start_date'].date().strftime('%d.%m.%Y')
    end_date_formatted = data['end_date'].date().strftime('%d.%m.%Y')
    text = (
        f"📢 *Настройка рассылки* 📢\n\n"
        f"📅 *Начало опроса:* {start_date_formatted}\n"
        f"⏳ *Конец опроса:* {end_date_formatted}\n\n"
        f"📆 *Всего дней опроса:* {total_days}\n\n"
        f"🔁 *Даты рассылок:*\n{dates_text}\n\n"
        f"🕒 *Время рассылки:* 12:00\n\n"
        f"✅ *Сохранить рассылку?*"
    )

    await callback.message.answer(text, reply_markup=emails_accept_settings_keyboard(), parse_mode='Markdown')
    await state.set_state(MailingStates.confirmation)
    await callback.answer()

@mailing_router.callback_query(MailingStates.confirmation)
async def confirm_mailing(callback: CallbackQuery, state: FSMContext):
    """Подтверждение сохранения рассылки."""
    try:
        await callback.message.delete()
        if callback.data == 'confirm_mailing':
            loading_msg = await callback.message.answer("🔄 Отправка на сервер...")
            data = await state.get_data()
            try:
                intermediate_dates = [
                    datetime.strptime(d.split(" ")[0], "%d.%m.%Y").date()
                    for d in data.get("intermediate_dates", [])
                    if d.strip()
                ]
            except ValueError as e:
                await loading_msg.edit_text(f"❌ Неверный формат промежуточных дат: {str(e)}")
                await state.clear()
                return

            payload = {
                "chat_id": callback.from_user.id,
                "start_date": data["start_date"].strftime("%Y-%m-%d"),
                "end_date": data["end_date"].strftime("%Y-%m-%d"),
                "intermediate_dates": [d.strftime("%Y-%m-%d") for d in intermediate_dates],
            }

            try:
                response = requests.post(f'{API_URL}/mailing/settings/', json=payload, headers=HEADER, verify=False)
                response.raise_for_status()
                await loading_msg.edit_text("✅ Рассылка сохранена в системе!")
                await state.clear()

            except requests.exceptions.HTTPError as e:
                if response.status_code == 400:
                    try:
                        error_msg = response.json().get("error", "Неизвестная ошибка")
                        if "пересекается" in error_msg.lower():
                            date_matches = re.findall(r"\d{4}-\d{2}-\d{2}", error_msg)
                            if len(date_matches) >= 4:
                                def reformat_date(date_str):
                                    year, month, day = date_str.split('-')
                                    return f"{day}.{month}.{year}"

                                reformatted_dates = [reformat_date(date) for date in date_matches]

                                new_dates = f"{reformatted_dates[0]} - {reformatted_dates[1]}"
                                existing_dates = f"{reformatted_dates[2]} - {reformatted_dates[3]}"
                                message = (
                                    "⚠️ *Конфликт дат*\n"
                                    "──────────────\n"
                                    "🗓 *Ваши даты:*\n"
                                    f"`{new_dates}`\n\n"
                                    "📅 *Активная рассылка:*\n" 
                                    f"`{existing_dates}`\n"
                                    "──────────────\n"
                                    "Отменить активную рассылку и создать новую?"
                                )
                            else:
                                message = (
                                    f"❌ {error_msg}\n\n"
                                    "Хотите отменить существующую рассылку и создать новую?"
                                )
                            await loading_msg.edit_text(
                                message,
                                reply_markup=cancel_existing_mailing_keyboard_restart(),
                                parse_mode='Markdown'
                            )
                            await state.set_state(MailingStates.cancel_existing)
                        else:
                            await loading_msg.edit_text(
                                f"❌ Ошибка: {error_msg}",
                                parse_mode="Markdown"
                            )
                    except ValueError:
                        await loading_msg.edit_text(
                            "❌ Произошла ошибка при обработке ответа сервера",
                        )
                else:
                    await loading_msg.edit_text(f"❌ Неожиданная ошибка при создании рассылки: {str(e)}")
                    await state.clear()

            except requests.exceptions.RequestException as e:
                await loading_msg.edit_text(f"❌ Ошибка связи с сервером: {str(e)}")
                await state.clear()

        elif callback.data == 'cancel_mailing':
            await state.clear()
            await callback.message.answer(
                "🔄 Давайте начнем заново!\n\nВыберите дату начала:",
                reply_markup=emails_start_inline_keyboard(),
            )
            await state.set_state(MailingStates.start_date)

        await callback.answer()

    except Exception as e:
        await loading_msg.edit_text(f"❗ Произошла ошибка: {str(e)}")
        await state.clear()
        await callback.answer()


@mailing_router.callback_query(MailingStates.cancel_existing)
async def cancel_existing_mailing(callback: CallbackQuery, state: FSMContext):
    """Обрабатываем отмену существующей рассылки."""
    await callback.message.delete()
    try:
        loading_msg = await callback.message.answer("🔄 Удаление рассылки...")
        if callback.data == 'cancel_existing_mailing_restart':
            list_response = requests.get(
                f"{API_URL}/mailing/all/",
                headers=HEADER,
                verify=False
            )
            list_response.raise_for_status()

            mailings = list_response.json().get('data', [])
            if not mailings:
                await loading_msg.edit_text(
                    "ℹ️ Нет активных рассылок для удаления",
                    parse_mode="Markdown"
                )
                return

            latest_mailing = mailings[0]
            mailing_id = latest_mailing['id']

            delete_response = requests.delete(
                f"{API_URL}/mailing/{mailing_id}/",
                headers=HEADER,
                verify=False
            )
            delete_response.raise_for_status()

            await loading_msg.edit_text(
                "✅ Рассылка удалена. Выберите новые даты:",
                reply_markup=emails_start_inline_keyboard(),
                parse_mode="Markdown"
            )
            await state.set_state(MailingStates.start_date)

        await callback.answer()

    except requests.exceptions.HTTPError as e:
        error_msg = "Неизвестная ошибка сервера"
        try:
            error_msg = e.response.json().get('error', str(e))
        except:
            error_msg = str(e)
        await loading_msg.edit_text(
            f"❌ Ошибка при удалении рассылки: {error_msg}",
            parse_mode="Markdown"
        )
    except requests.exceptions.RequestException as e:
        await loading_msg.edit_text(
            f"❌ Ошибка соединения: {str(e)}",
            parse_mode="Markdown"
        )
    except Exception as e:
        await loading_msg.edit_text(
            f"❌ Неожиданная ошибка: {str(e)}",
            parse_mode="Markdown"
        )
    finally:
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


@mailing_router.callback_query(F.data == "settings_test")
async def start_test_dialog(callback: CallbackQuery, state: FSMContext):
    """Начало диалога для тестового функционала."""
    await callback.message.delete()
    await state.clear()
    await callback.message.answer("📧 Укажите почту для тестового письма \n" \
                                  "📌 Например: user@croc.ru", parse_mode="Markdown")
    await state.set_state(TestStates.waiting_for_email)


@mailing_router.message(TestStates.waiting_for_email)
async def process_email(message: Message, state: FSMContext):
    """Обработка ввода почты."""
    email = message.text.strip()
    if '@' not in email or '.' not in email:
        await message.answer("❌ Неверный формат почты. Укажите корректный email\n" \
                             "📌 Например: user@croc.ru", parse_mode="Markdown")
        return
    await state.update_data(email=email)
    await message.answer("👤 Укажите ФИ для тестовой учетной записи \n" \
                         "📌 Например: Василенко Станислав", parse_mode="Markdown")
    await state.set_state(TestStates.waiting_for_full_name)

@mailing_router.message(TestStates.waiting_for_full_name)
async def process_full_name(message: Message, state: FSMContext):
    """Обработка ввода ФИ и отправка на сервер."""
    full_name = message.text.strip()
    name_parts = full_name.split(' ', 1)
    if len(name_parts) < 2:
        await message.answer("❌ Укажите ФИ в формате 'Фамилия Имя' \n" \
                             "📌 Например Василенко Станислав.", parse_mode="Markdown")
        return
    await state.update_data(full_name=full_name, first_name=name_parts[1], last_name=name_parts[0])

    data = await state.get_data()
    email = data.get("email")
    first_name = data.get("first_name")
    last_name = data.get("last_name")

    test_api_url = f"{API_URL}/test-create/"
    test_data = {
        "email": email,
        "first_name": first_name,
        "last_name": last_name
    }
    await message.answer("🔄 Отправка на сервер...", parse_mode="Markdown")
    try:
        response = requests.post(test_api_url, json=test_data, headers=HEADER, verify=False)
        response.raise_for_status()
        if response.status_code == 201:
            await message.answer(
                f"✅ Тестовая учетная запись создана для {full_name}.\n\n"
                f"📬 Письмо отправлено на {email}.",
            )
        await state.clear()
    except requests.exceptions.HTTPError as e:
        try:
            error_msg = response.json().get("error", "Неизвестная ошибка сервера")
        except:
            error_msg = str(e)
        if "уже существует" in error_msg:
            await message.answer(
                f"✅ Пользователь с email {email} уже существует!\n\n"
                "📬 Отправляю письмо.",
            )
        else:
            await message.answer(f"❌ Ошибка сервера: {error_msg}", parse_mode="Markdown")
        await state.clear()
    except requests.exceptions.RequestException as e:
        await message.answer(f"❌ Ошибка соединения: {str(e)}", parse_mode="Markdown")
        await state.clear()
