import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from config_reader import config
from keyboards import builders
from services.google_sheets import gs_service


# Состояния для FSM
class RecordHours(StatesGroup):
    choosing_date = State()
    entering_hours = State()


logging.basicConfig(level=logging.INFO)
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()


# Обработка команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я помогу тебе вести учет рабочих часов.",
        reply_markup=builders.main_menu()
    )


# Нажали "Записать часы"
@dp.message(F.text == "Записать часы")
async def start_record(message: types.Message, state: FSMContext):
    await state.set_state(RecordHours.choosing_date)
    await message.answer("За какую дату записываем?", reply_markup=builders.date_selection())


# Выбрали дату
@dp.message(RecordHours.choosing_date)
async def process_date(message: types.Message, state: FSMContext):
    await state.update_data(chosen_date=message.text)
    await state.set_state(RecordHours.entering_hours)
    await message.answer("Сколько часов ты сегодня работала?", reply_markup=types.ReplyKeyboardRemove())


# Ввели часы
@dp.message(RecordHours.entering_hours)
async def process_hours(message: types.Message, state: FSMContext):
    try:
        hours = float(message.text.replace(",", "."))
        data = await state.get_data()

        # Запись в таблицу
        gs_service.append_hours(data['chosen_date'], hours)

        await message.answer(f"Записала! {data['chosen_date']} — {hours} ч.", reply_markup=builders.main_menu())
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введи число (например, 5 или 1.5)")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())