from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from datetime import datetime, timedelta
from config_reader import config

def main_menu():
    builder = ReplyKeyboardBuilder()
    builder.button(text="Записать часы")
    builder.button(text="Сверить часы")
    builder.button(text="Аналитика")
    builder.button(text="👥 Клиенты") # Новый раздел
    builder.button(text="... Назад") # Вспомогательная кнопка сброса
    builder.button(text="Открыть таблицу 📝")
    builder.adjust(2, 2, 2)
    return builder.as_markup(resize_keyboard=True)

# Меню управления клиентами
def clients_menu():
    builder = ReplyKeyboardBuilder()
    builder.button(text="📋 Список клиентов")
    builder.button(text="➕ Добавить клиента")
    builder.button(text="⬅️ Главное меню")
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)

# Выбор типа клиента
def client_type_selection():
    builder = ReplyKeyboardBuilder()
    builder.button(text="Индив")
    builder.button(text="Пара")
    builder.button(text="Группа")
    builder.button(text="❌ Отмена")
    builder.adjust(3, 1)
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
    builder.button(text=now.strftime("%m.%Y"))
    last_month = now.replace(day=1) - timedelta(days=1)
    builder.button(text=last_month.strftime("%m.%Y"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def open_sheet_inline():
    builder = InlineKeyboardBuilder()
    sheet_url = f"https://docs.google.com/spreadsheets/d/{config.SPREADSHEET_ID}"
    builder.button(text="Перейти к Google Таблице 🚀", url=sheet_url)
    return builder.as_markup()