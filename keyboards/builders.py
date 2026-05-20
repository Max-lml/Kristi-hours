from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from datetime import datetime, timedelta
from config_reader import config

# МЕНЮ ДЛЯ АДМИНИСТРАТОРОВ (Ты и Кристина)
def admin_main_menu():
    builder = ReplyKeyboardBuilder()
    builder.button(text="➕ Добавить запись")
    builder.button(text="📅 Расписание")
    builder.button(text="💰 Финансы")
    builder.button(text="👥 Клиенты")
    builder.button(text="Записать часы")
    builder.button(text="Сверить часы")
    builder.button(text="Аналитика")
    builder.button(text="Открыть таблицу 📝")
    builder.adjust(1, 2, 2, 2, 1)
    return builder.as_markup(resize_keyboard=True)

# МЕНЮ ДЛЯ КЛИЕНТОВ (Ученики и посторонние)
def client_main_menu():
    builder = ReplyKeyboardBuilder()
    builder.button(text="📅 Расписание занятий") # Единственная доступная кнопка
    return builder.as_markup(resize_keyboard=True)

# Урезанное меню расписания для клиентов (без кнопки "Активные дни", чтобы не светить даты чужих уроков)
def client_schedule_menu():
    builder = ReplyKeyboardBuilder()
    builder.button(text="На сегодня 🗓")
    builder.button(text="На завтра 🌅")
    builder.button(text="Выбрать дату 📆")
    builder.button(text="⬅️ В меню")
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)

# ОСТАЛЬНЫЕ КНОПКИ АДМИНКА (БЕЗ ИЗМЕНЕНИЙ)
def schedule_menu():
    builder = ReplyKeyboardBuilder()
    builder.button(text="На сегодня 🗓")
    builder.button(text="На завтра 🌅")
    builder.button(text="Выбрать дату 📆")
    builder.button(text="Активные дни ✨")
    builder.button(text="⬅️ Главное меню")
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True)

def active_dates_buttons(dates_list):
    builder = ReplyKeyboardBuilder()
    for date_str in dates_list:
        builder.button(text=f"📅 {date_str}")
    builder.button(text="❌ Отмена")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def clients_menu():
    builder = ReplyKeyboardBuilder()
    builder.button(text="📋 Список клиентов")
    builder.button(text="➕ Добавить клиента")
    builder.button(text="🗄 В архив")
    builder.button(text="💎 Пополнить абонемент")
    builder.button(text="⬅️ Главное меню")
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True)

def subscription_lessons_selection():
    builder = ReplyKeyboardBuilder()
    builder.button(text="4 занятия")
    builder.button(text="8 занятий")
    builder.button(text="12 занятий")
    builder.button(text="❌ Отмена")
    builder.adjust(3, 1)
    return builder.as_markup(resize_keyboard=True)

def clients_as_buttons(client_names):
    builder = ReplyKeyboardBuilder()
    for name in client_names:
        builder.button(text=name)
    builder.button(text="❌ Отмена")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def payment_type_selection():
    builder = ReplyKeyboardBuilder()
    builder.button(text="Разовая")
    builder.button(text="Абонемент")
    builder.button(text="В долг (Не оплачено)")
    builder.button(text="❌ Отмена")
    builder.adjust(2, 1, 1)
    return builder.as_markup(resize_keyboard=True)

def lesson_location_selection():
    builder = ReplyKeyboardBuilder()
    builder.button(text="Личный урок 👤")
    builder.button(text="Школа Сабины 🏫")
    builder.button(text="❌ Отмена")
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)

def schedule_date_selection():
    builder = ReplyKeyboardBuilder()
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    builder.button(text=today.strftime("%d.%m.%Y"))
    builder.button(text=tomorrow.strftime("%d.%m.%Y"))
    builder.button(text="Другая дата")
    builder.button(text="❌ Отмена")
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True)

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
    builder.button(text="❌ Отмена")
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True)

def month_selection():
    builder = ReplyKeyboardBuilder()
    now = datetime.now()
    builder.button(text=now.strftime("%m.%Y"))
    last_month = now.replace(day=1) - timedelta(days=1)
    builder.button(text=last_month.strftime("%m.%Y"))
    builder.button(text="❌ Отмена")
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)

def open_sheet_inline():
    builder = InlineKeyboardBuilder()
    sheet_url = f"https://docs.google.com/spreadsheets/d/{config.SPREADSHEET_ID}"
    builder.button(text="Перейти к Google Таблице 🚀", url=sheet_url)
    return builder.as_markup()