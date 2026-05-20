import asyncio
import logging
import io
from datetime import datetime

import matplotlib.pyplot as plt
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from config_reader import config
from keyboards import builders
from services.google_sheets import gs_service

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone


# 1. ОПРЕДЕЛЯЕМ СОСТОЯНИЯ
class RecordHours(StatesGroup):
    choosing_date = State()
    manual_date = State()
    entering_hours = State()


class AddClient(StatesGroup):
    entering_name = State()
    choosing_type = State()


logging.basicConfig(level=logging.INFO)
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()


# --- БАЗОВЫЕ КОМАНДЫ И СБРОСЫ ---

@dp.message(Command("start"))
@dp.message(F.text == "⬅️ Главное меню")
async def cmd_start(message: types.Message, state: FSMContext = None):
    if state:
        await state.clear()
    await message.answer("Главное меню:", reply_markup=builders.main_menu())


# Универсальный перехватчик "Отмены" для любых сценариев
@dp.message(F.text == "❌ Отмена")
async def cancel_any_action(message: types.Message, state: FSMContext = None):
    if state:
        current_state = await state.get_state()
        await state.clear()

        # Если отменили добавление клиента, возвращаем в меню клиентов
        if current_state and "AddClient" in current_state:
            await message.answer("Добавление клиента отменено.", reply_markup=builders.clients_menu())
            return

    # Во всех остальных случаях возвращаем в главное меню
    await message.answer("Действие отменено.", reply_markup=builders.main_menu())


# --- РАЗДЕЛ: КЛИЕНТЫ ---

@dp.message(F.text == "👥 Клиенты")
async def open_clients_section(message: types.Message, state: FSMContext = None):
    if state:
        await state.clear()
    await message.answer("Управление базой клиентов:", reply_markup=builders.clients_menu())


@dp.message(F.text == "📋 Список клиентов")
async def show_clients_list(message: types.Message):
    await message.answer("⏳ Загружаю список клиентов...")
    clients = gs_service.get_active_clients()

    if not clients:
        await message.answer("У тебя пока нет активных клиентов. Нажми '➕ Добавить клиента'.")
        return

    text = "👥 **Активные клиенты:**\n\n" + "\n".join([f"• {name}" for name in clients])
    await message.answer(text, parse_mode="Markdown")


@dp.message(F.text == "➕ Добавить клиента")
async def start_add_client(message: types.Message, state: FSMContext):
    await state.set_state(AddClient.entering_name)
    # Даем клавиатуру с отменой, чтобы пользователь мог передумать сразу
    builder = types.ReplyKeyboardBuilder()
    builder.button(text="❌ Отмена")
    await message.answer("Введите имя клиента (или имена пары/название группы):",
                         reply_markup=builder.as_markup(resize_keyboard=True))


@dp.message(AddClient.entering_name)
async def process_client_name(message: types.Message, state: FSMContext):
    await state.update_data(client_name=message.text)
    await state.set_state(AddClient.choosing_type)
    await message.answer(f"Какого типа клиент '{message.text}'?", reply_markup=builders.client_type_selection())


@dp.message(AddClient.choosing_type, F.text.in_({"Индив", "Пара", "Группа"}))
async def process_client_type(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client_name = data['client_name']
    client_type = message.text

    gs_service.add_new_client(client_name, client_type)

    await message.answer(f"✅ Клиент сохранен!\n👤 {client_name} ({client_type})", reply_markup=builders.clients_menu())
    await state.clear()


# --- ЛОГИКА ЗАПИСИ ЧАСОВ ---

@dp.message(F.text == "Записать часы")
async def start_record(message: types.Message, state: FSMContext):
    await state.set_state(RecordHours.choosing_date)
    await message.answer("За какую дату записываем?", reply_markup=builders.date_selection())


@dp.message(RecordHours.choosing_date, F.text != "Другая дата", F.text != "Аналитика", F.text != "Сверить часы",
            F.text != "Открыть таблицу 📝", F.text != "👥 Клиенты")
async def process_date(message: types.Message, state: FSMContext):
    try:
        datetime.strptime(message.text, "%d.%m.%Y")
        await state.update_data(chosen_date=message.text)
        await state.set_state(RecordHours.entering_hours)
        builder = types.ReplyKeyboardBuilder()
        builder.button(text="❌ Отмена")
        await message.answer(f"Выбрана дата: {message.text}\nСколько часов ты отработала?",
                             reply_markup=builder.as_markup(resize_keyboard=True))
    except ValueError:
        await message.answer("❌ Напиши дату цифрами (ДД.ММ.ГГГГ) или выбери на кнопках)")


@dp.message(RecordHours.choosing_date, F.text == "Другая дата")
async def manual_date_entry(message: types.Message, state: FSMContext):
    await state.set_state(RecordHours.manual_date)
    builder = types.ReplyKeyboardBuilder()
    builder.button(text="❌ Отмена")
    await message.answer("Введи дату в формате ДД.ММ.ГГГГ\nНапример: 12.04.2026",
                         reply_markup=builder.as_markup(resize_keyboard=True))


@dp.message(RecordHours.manual_date)
async def process_manual_date(message: types.Message, state: FSMContext):
    try:
        datetime.strptime(message.text, "%d.%m.%Y")
        await state.update_data(chosen_date=message.text)
        await state.set_state(RecordHours.entering_hours)
        builder = types.ReplyKeyboardBuilder()
        builder.button(text="❌ Отмена")
        await message.answer(f"Дата {message.text} принята. Сколько часов ты отработала?",
                             reply_markup=builder.as_markup(resize_keyboard=True))
    except ValueError:
        await message.answer("❌ Ошибка в формате!\nНапиши дату вот так: 16.04.2026")


@dp.message(RecordHours.entering_hours)
async def process_hours(message: types.Message, state: FSMContext):
    try:
        hours = float(message.text.replace(",", "."))
        if hours <= 0 or hours > 24:
            await message.answer("❌ Введено странное количество часов. Попробуй еще раз)")
            return
        data = await state.get_data()
        gs_service.append_hours(data['chosen_date'], hours)
        await message.answer(f"✅ Записала! {data['chosen_date']} — {hours} ч.", reply_markup=builders.main_menu())
        await state.clear()
    except ValueError:
        await message.answer("❌ Нужно ввести число (например: 5 или 1.5)")


# --- ЛОГИКА СВЕРКИ И АНАЛИТИКИ ---

@dp.message(F.text == "Сверить часы")
async def check_hours_start(message: types.Message, state: FSMContext = None):
    if state:
        await state.clear()
    await message.answer("За какой месяц хочешь посмотреть отчет?", reply_markup=builders.month_selection())


@dp.message(F.text.regexp(r'\d{2}\.\d{4}'))
async def process_report(message: types.Message):
    await message.answer(f"⏳ Считаю часы за {message.text}...")
    total = gs_service.get_month_report(message.text)
    await message.answer(f"📊 В месяце {message.text} отработано: {total} ч.", reply_markup=builders.main_menu())


@dp.message(F.text == "Аналитика")
async def send_analytics(message: types.Message, state: FSMContext = None):
    if state:
        await state.clear()
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
    if state:
        await state.clear()
    await message.answer("Вот прямая ссылка на Google Таблицу:", reply_markup=builders.open_sheet_inline())


async def send_reminder():
    user_ids = [364213802, 154491963]
    for user_id in user_ids:
        try:
            await bot.send_message(user_id, "🔔 Напоминание: не забудьте записать рабочие часы за сегодня! ✨")
            logging.info(f"Уведомление успешно отправлено пользователю {user_id}")
        except Exception as e:
            logging.error(f"Не удалось отправить уведомление пользователю {user_id}: {e}")


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