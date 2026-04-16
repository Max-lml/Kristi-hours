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


logging.basicConfig(level=logging.INFO)
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()


# --- БАЗОВЫЕ КОМАНДЫ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я помогу тебе вести учет рабочих часов.",
        reply_markup=builders.main_menu()
    )


# --- ЛОГИКА ЗАПИСИ ЧАСОВ ---

@dp.message(F.text == "Записать часы")
async def start_record(message: types.Message, state: FSMContext):
    await state.set_state(RecordHours.choosing_date)
    await message.answer("За какую дату записываем?", reply_markup=builders.date_selection())


# КЕЙС 1: Пользователь нажал "Другая дата"
@dp.message(RecordHours.choosing_date, F.text == "Другая дата")
async def manual_date_entry(message: types.Message, state: FSMContext):
    await state.set_state(RecordHours.manual_date)
    await message.answer(
        "Введи дату в формате ДД.ММ.ГГГГ\nНапример: 12.04.2026",
        reply_markup=types.ReplyKeyboardRemove()
    )


# КЕЙС 2: Пользователь нажал на кнопку с готовой датой или ввел текст вместо кнопки
@dp.message(RecordHours.choosing_date, F.text != "Другая дата")
async def process_date(message: types.Message, state: FSMContext):
    try:
        # Валидация: если введет "ор", упадем в except
        datetime.strptime(message.text, "%d.%m.%Y")

        await state.update_data(chosen_date=message.text)
        await state.set_state(RecordHours.entering_hours)
        await message.answer(
            f"Выбрана дата: {message.text}\nСколько часов ты отработала?",
            reply_markup=types.ReplyKeyboardRemove()
        )
    except ValueError:
        await message.answer("❌ Напиши дату цифрами (ДД.ММ.ГГГГ) или выбери на кнопках)")


# КЕЙС 3: Обработка ручного ввода даты
@dp.message(RecordHours.manual_date)
async def process_manual_date(message: types.Message, state: FSMContext):
    try:
        datetime.strptime(message.text, "%d.%m.%Y")
        await state.update_data(chosen_date=message.text)
        await state.set_state(RecordHours.entering_hours)
        await message.answer(f"Дата {message.text} принята. Сколько часов ты отработала?")
    except ValueError:
        await message.answer("❌ Ошибка в формате!\nНапиши дату вот так: 16.04.2026")


# ФИНАЛ: Ввод часов и сохранение
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
async def check_hours_start(message: types.Message):
    await message.answer(
        "За какой месяц хочешь посмотреть отчет?",
        reply_markup=builders.month_selection()
    )


@dp.message(F.text.regexp(r'\d{2}\.\d{4}'))
async def process_report(message: types.Message):
    await message.answer(f"⏳ Считаю часы за {message.text}...")
    total = gs_service.get_month_report(message.text)
    await message.answer(
        f"📊 В месяце {message.text} отработано: {total} ч.",
        reply_markup=builders.main_menu()
    )


@dp.message(F.text == "Аналитика")
async def send_analytics(message: types.Message):
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

async def send_reminder():
    # Создаем список ID (важно: без кавычек, так как это числа)
    user_ids = [364213802, 154491963]

    for user_id in user_ids:
        try:
            await bot.send_message(
                user_id,
                "🔔 Напоминание: не забудьте записать рабочие часы за сегодня! ✨"
            )
            logging.info(f"Уведомление успешно отправлено пользователю {user_id}")
        except Exception as e:
            # Если возникла ошибка (например, бот заблокирован), просто логируем её
            logging.error(f"Не удалось отправить уведомление пользователю {user_id}: {e}")


# --- ЗАПУСК ---

async def main():
    # Настраиваем планировщик
    scheduler = AsyncIOScheduler(timezone=timezone("Europe/Moscow"))
    # Добавляем задачу: каждый день (cron) в 21:00
    scheduler.add_job(send_reminder, "cron", hour=18, minute=55)
    scheduler.start()

    # Запуск бота
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен")