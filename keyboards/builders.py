from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from datetime import datetime, timedelta


def main_menu():
    builder = ReplyKeyboardBuilder()
    builder.button(text="Записать часы")
    builder.button(text="Сверить часы")
    builder.button(text="Аналитика")
    builder.button(text="Открыть таблицу 📝")
    builder.adjust(2, 2)  # Теперь кнопки будут красиво лежать 2х2
    return builder.as_markup(resize_keyboard=True)


# Создаем специальную инлайн-кнопку со ссылкой
def open_sheet_inline():
    builder = InlineKeyboardBuilder()
    # Сюда вставляешь полную ссылку на твою Google Таблицу
    sheet_url = "https://docs.google.com/spreadsheets/d/1lJtqnCpCUHmURX4JmWa5vJYy-kXqz67hUDR1Z_wK5N0/edit?gid=1867670094#gid=1867670094"

    builder.button(text="Перейти к Google Таблице 🚀", url=sheet_url)
    return builder.as_markup()
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