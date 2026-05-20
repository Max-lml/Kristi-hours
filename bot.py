import asyncio
import logging
import io
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from config_reader import config
from keyboards import builders
from services.google_sheets import gs_service

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone

# СПИСОК АДМИНИСТРАТОРОВ (Твой ID и ID Кристины)
ADMIN_IDS = [364213802, 154491963]


# СОСТОЯНИЯ FSM
class RecordHours(StatesGroup):
    choosing_date = State()
    manual_date = State()
    entering_hours = State()


class AddClient(StatesGroup):
    entering_name = State()
    choosing_type = State()


class AddEvent(StatesGroup):
    choosing_entry_type = State()
    choosing_location = State()
    choosing_client = State()
    entering_personal_title = State()
    choosing_date = State()
    manual_date = State()
    entering_time = State()
    choosing_payment = State()
    entering_amount = State()


class ArchiveClientState(StatesGroup):
    choosing_client = State()


class TopUpSubState(StatesGroup):
    choosing_client = State()
    choosing_lessons = State()


class ViewScheduleState(StatesGroup):
    entering_date = State()


logging.basicConfig(level=logging.INFO)
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()


# --- БАЗОВЫЕ КОМАНДЫ И СБРОСЫ ---

@dp.message(Command("start"))
@dp.message(F.text == "⬅️ Главное меню")
@dp.message(F.text == "⬅️ В меню")
async def cmd_start(message: types.Message, state: FSMContext = None):
    if state:
        await state.clear()

    # Разводка меню по правам доступа
    if message.from_user.id in ADMIN_IDS:
        await message.answer("Главное меню (Доступ: Администратор):", reply_markup=builders.admin_main_menu())
    else:
        await message.answer(
            f"Привет, {message.from_user.full_name}! 👋\nЯ бот-ассистент Кристины. Здесь ты можешь посмотреть расписание занятий.",
            reply_markup=builders.client_main_menu()
        )


@dp.message(F.text == "❌ Отмена")
async def cancel_any_action(message: types.Message, state: FSMContext = None):
    if state:
        current_state = await state.get_state()
        await state.clear()
        if current_state and any(s in current_state for s in ["AddClient", "ArchiveClientState", "TopUpSubState"]):
            await message.answer("Действие отменено.", reply_markup=builders.clients_menu())
            return
        if current_state and "ViewScheduleState" in current_state:
            reply_kbd = builders.schedule_menu() if message.from_user.id in ADMIN_IDS else builders.client_schedule_menu()
            await message.answer("Просмотр расписания отменен.", reply_markup=reply_kbd)
            return

    reply_kbd = builders.admin_main_menu() if message.from_user.id in ADMIN_IDS else builders.client_main_menu()
    await message.answer("Действие отменено.", reply_markup=reply_kbd)


# --- РАЗДЕЛ: РАСПИСАНИЕ (ОБЩИЙ ДЛЯ АДМИНОВ И КЛИЕНТОВ) ---

@dp.message(F.text == "📅 Расписание")
@dp.message(F.text == "📅 Расписание занятий")
async def open_schedule_section(message: types.Message, state: FSMContext = None):
    if state:
        await state.clear()

    if message.from_user.id in ADMIN_IDS:
        await message.answer("Выберите режим просмотра расписания:", reply_markup=builders.schedule_menu())
    else:
        await message.answer("За какой день показать расписание занятий?", reply_markup=builders.client_schedule_menu())


@dp.message(F.text == "На сегодня 🗓")
async def show_schedule_today(message: types.Message):
    date_str = datetime.now().strftime("%d.%m.%Y")
    await render_day_schedule(message, date_str, "сегодня")


@dp.message(F.text == "На завтра 🌅")
async def show_schedule_tomorrow(message: types.Message):
    date_str = (datetime.now() + timedelta(days=1)).strftime("%d.%m.%Y")
    await render_day_schedule(message, date_str, "завтра")


@dp.message(F.text == "Выбрать дату 📆")
async def choose_custom_date(message: types.Message, state: FSMContext):
    await state.set_state(ViewScheduleState.entering_date)
    builder = ReplyKeyboardBuilder()
    builder.button(text="❌ Отмена")
    await message.answer("Введи дату для просмотра в формате ДД.ММ.ГГГГ\nНапример: 25.05.2026",
                         reply_markup=builder.as_markup(resize_keyboard=True))


@dp.message(ViewScheduleState.entering_date)
async def process_custom_view_date(message: types.Message, state: FSMContext):
    try:
        datetime.strptime(message.text, "%d.%m.%Y")
        await state.clear()
        await render_day_schedule(message, message.text, message.text)
    except ValueError:
        await message.answer("❌ Неверный формат! Введи строго вот так: 25.05.2026")


# Защищенный хэндлер активных дней (Только Админ)
@dp.message(F.text == "Активные дни ✨")
async def show_active_days(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer("⏳ Сканирую таблицу на наличие записей...")
    active_dates = gs_service.get_active_dates()
    if not active_dates:
        await message.answer("В таблице пока нет будущих записей или уроков.", reply_markup=builders.schedule_menu())
        return
    await message.answer("Вот дни, на которые у вас что-то запланировано. Нажмите на любой:",
                         reply_markup=builders.active_dates_buttons(active_dates))


@dp.message(F.text.regexp(r'^📅 \d{2}\.\d{2}\.\d{4}$'))
async def process_active_day_click(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    date_str = message.text.replace("📅 ", "").strip()
    await render_day_schedule(message, date_str, date_str)


async def render_day_schedule(message: types.Message, date_str: str, day_text: str):
    events = gs_service.get_schedule_for_date(date_str)
    reply_kbd = builders.schedule_menu() if message.from_user.id in ADMIN_IDS else builders.client_schedule_menu()

    if not events:
        await message.answer(f"📅 Расписание на день `{date_str}` пусто.", reply_markup=reply_kbd)
        return

    text = f"📅 **Расписание на {day_text}:**\n\n"
    for ev in events:
        # Для клиентов убираем пометки Личный/Школа, пишем просто Урок
        clean_type_text = "Урок" if "Урок" in ev['type'] else "Личное дело"

        # Если посторонний человек заглянул в личные дела админа - скрываем название
        title_text = "Занято (Личное дело)" if (
                    ev['type'] == "Личное дело" and message.from_user.id not in ADMIN_IDS) else ev['title']

        icon = "🎓" if "Урок" in ev['type'] else "🏃‍♂️"
        text += f"• `{ev['time']}` — {icon} {title_text} ({clean_type_text})\n"

    await message.answer(text, parse_mode="Markdown", reply_markup=reply_kbd)


# --- ЗАЩИЩЕННЫЙ РАЗДЕЛ: ПОДРОБНЫЕ ФИНАНСЫ (Только Админ) ---

@dp.message(F.text == "💰 Финансы")
async def show_finance_report(message: types.Message, state: FSMContext = None):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔️ У вас нет прав доступа к этому разделу.")
        return
    if state:
        await state.clear()
    await message.answer("⏳ Рассчитываю подробные финансовые показатели...")
    report = gs_service.get_detailed_financial_report()

    text = (
        "📊 **Финансовый дашборд Кристины:**\n\n"
        "📅 **За эту неделю:**\n"
        f"• Личные уроки: *{report['personal_week']:.0f} руб.*\n"
        f"• Школа Сабины: *{report['school_week']:.0f} руб.*\n"
        f"• Всего за неделю: **{report['personal_week'] + report['school_week']:.0f} руб.**\n\n"
        "🗓 **За текущий месяц:**\n"
        f"• Личные уроки: *{report['personal_month']:.0f} руб.*\n"
        f"• Школа Сабины: *{report['school_month']:.0f} руб.*\n"
        f"• Всего за месяц: **{report['personal_month'] + report['school_month']:.0f} руб.**\n\n"
        f"🚨 **Список и сумма долгов ({report['total_debts']:.0f} руб.):**\n"
        f"{report['debts_details']}"
    )
    await message.answer(text, parse_mode="Markdown")


# --- ЗАЩИЩЕННАЯ ЛОГИКА: ДОБАВЛЕНИЕ ЗАПИСИ (Только Админ) ---

@dp.message(F.text == "➕ Добавить запись")
async def start_add_event(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    await state.set_state(AddEvent.choosing_entry_type)
    await message.answer("Что добавляем?", reply_markup=builders.entry_type_selection())


@dp.message(AddEvent.choosing_entry_type, F.text == "Личное дело 🏃‍♂️")
async def process_personal_event(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    await state.update_data(entry_type="Личное дело", payment_type="—", amount=0.0)
    await state.set_state(AddEvent.entering_personal_title)
    builder = ReplyKeyboardBuilder()
    builder.button(text="❌ Отмена")
    await message.answer("Введите название дела:", reply_markup=builder.as_markup(resize_keyboard=True))


@dp.message(AddEvent.entering_personal_title)
async def process_personal_title(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    await state.update_data(name_or_event=message.text)
    await state.set_state(AddEvent.choosing_date)
    await message.answer("Выберите дату события:", reply_markup=builders.schedule_date_selection())


@dp.message(AddEvent.choosing_entry_type, F.text == "Урок 🎓")
async def process_lesson_event_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    await state.set_state(AddEvent.choosing_location)
    await message.answer("Выберите формат/локацию занятия:", reply_markup=builders.lesson_location_selection())


@dp.message(AddEvent.choosing_location, F.text.in_({"Личный урок 👤", "Школа Сабины 🏫"}))
async def process_lesson_location(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    clean_type = "Урок (Личный)" if "Личный" in message.text else "Урок (Школа)"
    await update_data_safe(state, entry_type=clean_type)

    clients = gs_service.get_active_clients()
    if not clients:
        await message.answer("❌ У вас еще нет активных учеников!", reply_markup=builders.admin_main_menu())
        await state.clear()
        return
    await state.set_state(AddEvent.choosing_client)
    await message.answer("Выберите ученика из списка:", reply_markup=builders.clients_as_buttons(clients))


@dp.message(AddEvent.choosing_client)
async def process_chosen_client(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    clients = gs_service.get_active_clients()
    if message.text not in clients:
        await message.answer("Пожалуйста, выберите ученика, нажав на кнопку!")
        return
    await update_data_safe(state, name_or_event=message.text)
    await state.set_state(AddEvent.choosing_date)
    await message.answer(f"Выбран ученик: {message.text}. На какую дату планируем занятие?",
                         reply_markup=builders.schedule_date_selection())


@dp.message(AddEvent.choosing_date, F.text != "Другая дата")
async def process_event_date(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        datetime.strptime(message.text, "%d.%m.%Y")
        await update_data_safe(state, event_date=message.text)
        await state.set_state(AddEvent.entering_time)
        builder = ReplyKeyboardBuilder()
        builder.button(text="❌ Отмена")
        await message.answer(f"Дата {message.text} выбрана. Введите время:",
                             reply_markup=builder.as_markup(resize_keyboard=True))
    except ValueError:
        await message.answer("❌ Выберите дату на кнопках или нажмите 'Другая дата'")


@dp.message(AddEvent.choosing_date, F.text == "Другая дата")
async def manual_event_date(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    await state.set_state(AddEvent.manual_date)
    builder = ReplyKeyboardBuilder()
    builder.button(text="❌ Отмена")
    await message.answer("Введи дату в формате ДД.ММ.ГГГГ:", reply_markup=builder.as_markup(resize_keyboard=True))


@dp.message(AddEvent.manual_date)
async def process_manual_event_date(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        datetime.strptime(message.text, "%d.%m.%Y")
        await update_data_safe(state, event_date=message.text)
        await state.set_state(AddEvent.entering_time)
        builder = ReplyKeyboardBuilder()
        builder.button(text="❌ Отмена")
        await message.answer(f"Дата {message.text} принята. Введите время:",
                             reply_markup=builder.as_markup(resize_keyboard=True))
    except ValueError:
        await message.answer("❌ Ошибка формата! Напишите вот так: 24.05.2026")


@dp.message(AddEvent.entering_time)
async def process_event_time(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    await update_data_safe(state, event_time=message.text)
    data = await state.get_data()

    if data['entry_type'] == "Личное дело":
        gs_service.append_schedule(data['event_date'], data['event_time'], data['name_or_event'], data['entry_type'],
                                   data['payment_type'], data['amount'])
        await message.answer(f"✅ Личное дело записано!", reply_markup=builders.admin_main_menu())
        await state.clear()
    else:
        await state.set_state(AddEvent.choosing_payment)
        await message.answer("Выберите тип оплаты занятия:", reply_markup=builders.payment_type_selection())


@dp.message(AddEvent.choosing_payment, F.text.in_({"Разовая", "Абонемент", "В долг (Не оплачено)"}))
async def process_event_payment_type(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    await update_data_safe(state, payment_type=message.text)
    await state.set_state(AddEvent.entering_amount)
    builder = ReplyKeyboardBuilder()
    builder.button(text="❌ Отмена")
    prompt = "Введите стоимость этого занятия по абонементу:" if message.text == "Абонемент" else "Введите стоимость занятия цифрами:"
    await message.answer(prompt, reply_markup=builder.as_markup(resize_keyboard=True))


@dp.message(AddEvent.entering_amount)
async def process_event_amount(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        amount = float(message.text.replace(",", "."))
        data = await state.get_data()
        gs_service.append_schedule(data['event_date'], data['event_time'], data['name_or_event'], data['entry_type'],
                                   data['payment_type'], amount)
        await message.answer(f"✅ Урок успешно добавлен!", reply_markup=builders.admin_main_menu())
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите числовое значение цены:")


async def update_data_safe(state: FSMContext, **kwargs):
    data = await state.get_data()
    data.update(kwargs)
    await state.set_data(data)


# --- ЗАЩИЩЕННЫЙ РАЗДЕЛ: КЛИЕНТЫ (Только Админ) ---

@dp.message(F.text == "👥 Ученики")
async def open_clients_section(message: types.Message, state: FSMContext = None):
    if message.from_user.id not in ADMIN_IDS: return
    if state: await state.clear()
    await message.answer("Управление базой учеников:", reply_markup=builders.clients_menu())


@dp.message(F.text == "📋 Список учеников")
async def show_clients_list(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    await message.answer("⏳ Загружаю список учеников...")
    clients = gs_service.get_active_clients()
    if not clients:
        await message.answer("У тебя пока нет активных учеников.")
        return
    text = "👥 **Активные ученики:**\n\n" + "\n".join([f"• {name}" for name in clients])
    await message.answer(text, parse_mode="Markdown")


@dp.message(F.text == "➕ Добавить ученика")
async def start_add_client(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    await state.set_state(AddClient.entering_name)
    builder = ReplyKeyboardBuilder()
    builder.button(text="❌ Отмена")
    await message.answer("Введите имя ученика:", reply_markup=builder.as_markup(resize_keyboard=True))


@dp.message(AddClient.entering_name)
async def process_client_name(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    await state.update_data(client_name=message.text)
    await state.set_state(AddClient.choosing_type)
    await message.answer(f"Какого типа ученик '{message.text}'?", reply_markup=builders.client_type_selection())


@dp.message(AddClient.choosing_type, F.text.in_({"Индив", "Пара", "Группа"}))
async def process_client_type(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    data = await state.get_data()
    gs_service.add_new_client(data['client_name'], message.text)
    await message.answer(f"✅ Ученик сохранен!", reply_markup=builders.clients_menu())
    await state.clear()


@dp.message(F.text == "🗄 В архив")
async def start_archive_client(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    clients = gs_service.get_active_clients()
    if not clients:
        await message.answer("Нет активных учеников для архивации.")
        return
    await state.set_state(ArchiveClientState.choosing_client)
    await message.answer("Кого перевести в архив?", reply_markup=builders.clients_as_buttons(clients))


@dp.message(ArchiveClientState.choosing_client)
async def process_archive_client(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    clients = gs_service.get_active_clients()
    if message.text not in clients:
        await message.answer("Выберите ученика с помощью кнопки!")
        return
    gs_service.archive_client(message.text)
    await message.answer(f"🗄 Ученик {message.text} переведен в архив.", reply_markup=builders.clients_menu())
    await state.clear()


@dp.message(F.text == "💎 Пополнить абонемент")
async def start_top_up_sub(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    clients = gs_service.get_active_clients()
    if not clients:
        await message.answer("Нет активных учеников.")
        return
    await state.set_state(TopUpSubState.choosing_client)
    await message.answer("Выберите ученика для пополнения абонемента:",
                         reply_markup=builders.clients_as_buttons(clients))


@dp.message(TopUpSubState.choosing_client)
async def process_top_up_client(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    clients = gs_service.get_active_clients()
    if message.text not in clients:
        await message.answer("Выберите ученика с помощью кнопки!")
        return
    await state.update_data(sub_client=message.text)
    await state.set_state(TopUpSubState.choosing_lessons)
    await message.answer(f"На сколько занятий пополнить абонемент для {message.text}?",
                         reply_markup=builders.subscription_lessons_selection())


@dp.message(TopUpSubState.choosing_lessons, F.text.in_({"4 занятия", "8 занятий", "12 занятий"}))
async def process_top_up_lessons(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    data = await state.get_data()
    lessons_count = int(message.text.split()[0])
    gs_service.top_up_subscription(data['sub_client'], lessons_count)
    await message.answer(f"✅ Баланс абонемента для {data['sub_client']} увеличен.",
                         reply_markup=builders.clients_menu())
    await state.clear()


# --- ЗАЩИЩЕННЫЙ СТАРЫЙ ФУНКЦИОНАЛ ЗАПИСИ ЧАСОВ (Только Админ) ---

@dp.message(F.text == "Записать часы")
async def start_record(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    await state.set_state(RecordHours.choosing_date)
    await message.answer("За какую дату записываем?", reply_markup=builders.date_selection())


@dp.message(RecordHours.choosing_date, F.text != "Другая дата", F.text != "Аналитика", F.text != "Сверить часы",
            F.text != "Открыть таблицу 📝", F.text != "👥 Ученики", F.text != "➕ Добавить запись",
            F.text != "📅 Расписание", F.text != "💰 Финансы", F.text != "📅 Расписание занятий")
async def process_date(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        datetime.strptime(message.text, "%d.%m.%Y")
        await update_data_safe(state, chosen_date=message.text)
        await state.set_state(RecordHours.entering_hours)
        builder = ReplyKeyboardBuilder()
        builder.button(text="❌ Отмена")
        await message.answer(f"Выбрана дата: {message.text}\nСколько часов ты отработала?",
                             reply_markup=builder.as_markup(resize_keyboard=True))
    except ValueError:
        await message.answer("❌ Напиши дату цифрами (ДД.ММ.ГГГГ) или выбери на кнопках)")


@dp.message(RecordHours.choosing_date, F.text == "Другая дата")
async def manual_date_entry(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    await state.set_state(RecordHours.manual_date)
    builder = ReplyKeyboardBuilder()
    builder.button(text="❌ Отмена")
    await message.answer("Введи дату в формате ДД.ММ.ГГГГ:", reply_markup=builder.as_markup(resize_keyboard=True))


@dp.message(RecordHours.manual_date)
async def process_manual_date(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        datetime.strptime(message.text, "%d.%m.%Y")
        await update_data_safe(state, chosen_date=message.text)
        await state.set_state(RecordHours.entering_hours)
        builder = ReplyKeyboardBuilder()
        builder.button(text="❌ Отмена")
        await message.answer(f"Дата {message.text} принята. Сколько часов ты отработала?",
                             reply_markup=builder.as_markup(resize_keyboard=True))
    except ValueError:
        await message.answer("❌ Ошибка в формате! Напишите вот так: 16.04.2026")


@dp.message(RecordHours.entering_hours)
async def process_hours(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        hours = float(message.text.replace(",", "."))
        if hours <= 0 or hours > 24:
            await message.answer("❌ Введено странное количество часов. Попробуй еще раз)")
            return
        data = await state.get_data()
        gs_service.append_hours(data['chosen_date'], hours)
        await message.answer(f"✅ Записала! {data['chosen_date']} — {hours} ч.", reply_markup=builders.admin_main_menu())
        await state.clear()
    except ValueError:
        await message.answer("❌ Нужно ввести число (например: 5 или 1.5)")


@dp.message(F.text == "Сверить часы")
async def check_hours_start(message: types.Message, state: FSMContext = None):
    if message.from_user.id not in ADMIN_IDS: return
    if state: await state.clear()
    await message.answer("За какой месяц хочешь посмотреть отчет?", reply_markup=builders.month_selection())


@dp.message(F.text.regexp(r'\d{2}\.\d{4}'))
async def process_report(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    await message.answer(f"⏳ Считаю часы за {message.text}...")
    total = gs_service.get_month_report(message.text)
    await message.answer(f"📊 В месяце {message.text} отработано: {total} ч.", reply_markup=builders.admin_main_menu())


@dp.message(F.text == "Аналитика")
async def send_analytics(message: types.Message, state: FSMContext = None):
    if message.from_user.id not in ADMIN_IDS: return
    if state: await state.clear()
    await message.answer("📊 Собираю данные и рисую график...")
    data = gs_service.get_all_data_for_analytics()
    if not data:
        await message.answer("Данных для графиков пока маловато.")
        return
    months = sorted(data.keys())
    hours = [data[m] for m in months]
    plt.figure(figsize=(10, 5))
    plt.plot(months, hours, marker='o', linestyle='-', color='b')
    plt.title('Твоя продуктивность')
    plt.ylabel('Часы')
    plt.grid(True)
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    photo = types.BufferedInputFile(buf.read(), filename="stats.png")
    await message.answer_photo(photo, caption="📈 Твоя нагрузка по месяцам")
    plt.close()


@dp.message(F.text == "Открыть таблицу 📝")
async def cmd_open_table(message: types.Message, state: FSMContext = None):
    if message.from_user.id not in ADMIN_IDS: return
    if state: await state.clear()
    await message.answer("Вот прямая ссылка на Google Таблицу:", reply_markup=builders.open_sheet_inline())


async def send_reminder():
    user_ids = [364213802, 154491963]
    for user_id in user_ids:
        try:
            await bot.send_message(user_id, "🔔 Напоминание: не забудьте записать рабочие часы за сегодня! ✨")
        except Exception as e:
            pass


# --- ЗАПУСК ---

async def main():
    scheduler = AsyncIOScheduler(timezone=timezone("Europe/Moscow"))
    scheduler.add_job(send_reminder, "cron", hour=19, minute=0)
    scheduler.start()
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен")