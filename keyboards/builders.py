from aiogram.utils.keyboard import ReplyKeyboardBuilder
from datetime import datetime, timedelta

def main_menu():
    builder = ReplyKeyboardBuilder()
    builder.button(text="Записать часы")
    builder.button(text="Сверить часы")
    builder.adjust(2) # 2 кнопки в ряд
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