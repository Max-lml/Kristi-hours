from aiogram.utils.keyboard import ReplyKeyboardBuilder
from datetime import datetime, timedelta

def main_menu():
    builder = ReplyKeyboardBuilder()
    builder.button(text="Записать часы")
    builder.button(text="Сверить часы")
    builder.button(text="Аналитика") # <--- ДОБАВЛЯЕМ ТУТ
    builder.adjust(2, 1) # Делаем 2 кнопки в ряд, а Аналитику под ними
    return builder.as_markup(resize_keyboard=True)

def date_selection():
    builder = ReplyKeyboardBuilder()
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)

    builder.button(text=today.strftime("%d.%m.%Y"))
    builder.button(text=yesterday.strftime("%d.%m.%Y"))
    builder.button(text=tomorrow.strftime("%d.%m.%Y"))
    builder.button(text="Другая дата")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def month_selection():
    builder = ReplyKeyboardBuilder()
    now = datetime.now()
    # Текущий месяц
    builder.button(text=now.strftime("%m.%Y"))
    # Прошлый месяц (упрощенная логика)
    last_month = now.replace(day=1) - timedelta(days=1)
    builder.button(text=last_month.strftime("%m.%Y"))

    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)