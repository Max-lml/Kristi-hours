import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
from config_reader import config


class GoogleSheetsService:
    def __init__(self):
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(config.GOOGLE_KEY_PATH, scope)
        self.client = gspread.authorize(creds)

        self.spreadsheet = self.client.open_by_key(config.SPREADSHEET_ID)

        self.sheet_old = self.spreadsheet.sheet1
        self.sheet_clients = self.spreadsheet.worksheet("Clients")
        self.sheet_schedule = self.spreadsheet.worksheet("Schedule")
        self.sheet_analytics = self.spreadsheet.worksheet("Analytics")

    # --- РАБОТА С КЛИЕНТАМИ И АБОНЕМЕНТАМИ ---

    def add_new_client(self, name: str, client_type: str):
        self.sheet_clients.append_row([name.strip(), client_type, "Актив", 0])

    def get_active_clients(self):
        records = self.sheet_clients.get_all_records()
        active_names = []
        for row in records:
            if str(row.get('Статус', '')).strip() == "Актив":
                active_names.append(str(row.get('Имя клиента', '')).strip())
        return active_names

    def archive_client(self, name: str):
        cell = self.sheet_clients.find(name.strip())
        if cell:
            self.sheet_clients.update_cell(cell.row, 3, "Архив")

    def top_up_subscription(self, name: str, lessons: int):
        cell = self.sheet_clients.find(name.strip())
        if cell:
            current_balance = int(self.sheet_clients.cell(cell.row, 4).value or 0)
            self.sheet_clients.update_cell(cell.row, 4, current_balance + lessons)

    def decrease_subscription(self, name: str):
        cell = self.sheet_clients.find(name.strip())
        if cell:
            current_balance = int(self.sheet_clients.cell(cell.row, 4).value or 0)
            if current_balance > 0:
                self.sheet_clients.update_cell(cell.row, 4, current_balance - 1)

    # --- РАБОТА С РАСПИСАНИЕМ И ЗАПИСЯМИ ---

    def append_schedule(self, date_str: str, time_str: str, name_or_event: str, entry_type: str, payment_type: str,
                        amount: float):
        self.sheet_schedule.append_row([
            date_str,
            time_str,
            name_or_event.strip(),
            entry_type,  # Например: "Урок (Личный)", "Урок (Школа)", "Личное дело"
            payment_type,
            amount
        ])
        if payment_type == "Абонемент":
            self.decrease_subscription(name_or_event)

    def get_schedule_for_date(self, target_date_str: str):
        records = self.sheet_schedule.get_all_records()
        day_events = []
        for row in records:
            if str(row.get('Дата', '')).strip() == target_date_str:
                day_events.append({
                    "time": str(row.get('Время', '')).strip(),
                    "title": str(row.get('Клиент/Дело', '')).strip(),
                    "type": str(row.get('Статус', '')).strip()
                })
        return sorted(day_events, key=lambda x: x['time'])

    def get_active_dates(self):
        records = self.sheet_schedule.get_all_records()
        dates_set = set()
        today_date = datetime.now().date()
        for row in records:
            date_val = str(row.get('Дата', '')).strip()
            try:
                event_date = datetime.strptime(date_val, "%d.%m.%Y").date()
                if event_date >= today_date:
                    dates_set.add(date_val)
            except ValueError:
                continue
        return sorted(list(dates_set), key=lambda d: datetime.strptime(d, "%d.%m.%Y"))

    # --- УМНЫЕ ФИНАНСЫ И ПОДРОБНЫЕ ДОЛГИ ---

    def get_detailed_financial_report(self):
        records = self.sheet_schedule.get_all_records()

        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday())

        personal_week = 0.0
        school_week = 0.0
        personal_month = 0.0
        school_month = 0.0

        debts_list = []
        total_debts = 0.0

        for row in records:
            status = str(row.get('Статус', '')).strip()
            # Если в статусе написано "Отмена" или "Отменено" — полностью игнорируем строку
            if "отмен" in status.lower():
                continue

            date_val = str(row.get('Дата', '')).strip()
            payment_type = str(row.get('Оплата', '')).strip()
            client_name = str(row.get('Клиент/Дело', '')).strip()

            try:
                amount_str = str(row.get('Сумма', 0)).replace(',', '.').strip()
                amount = float(amount_str) if amount_str else 0.0
            except ValueError:
                amount = 0.0

            # Сбор долгов
            if "долг" in payment_type.lower() or "не оплачено" in payment_type.lower():
                total_debts += amount
                debts_list.append(f"• {client_name} ({date_val}) — *{amount:.0f} руб.*")

            # Распределение по периодам и локациям
            try:
                event_date = datetime.strptime(date_val, "%d.%m.%Y")

                # Фильтр по месяцу
                if event_date.month == today.month and event_date.year == today.year:
                    if "школа" in status.lower():
                        school_month += amount
                    elif "личный" in status.lower() or "урок" in status.lower():
                        # Считаем и Разовые, и Абонементы, так как стоимость введена честно
                        personal_month += amount

                # Фильтр по неделе
                if start_of_week.date() <= event_date.date() <= today.date():
                    if "школа" in status.lower():
                        school_week += amount
                    elif "личный" in status.lower() or "урок" in status.lower():
                        personal_week += amount
            except ValueError:
                continue

        return {
            "personal_week": personal_week,
            "school_week": school_week,
            "personal_month": personal_month,
            "school_month": school_month,
            "total_debts": total_debts,
            "debts_details": "\n".join(debts_list) if debts_list else "Долгов нет 🎉"
        }

    # --- СТАРЫЕ МЕТОДЫ ДЛЯ ЧАСОВ ---
    def append_hours(self, date_str: str, hours: float):
        safe_hours = str(hours).replace(',', '.')
        self.sheet_old.append_row([date_str, safe_hours])

    def get_month_report(self, month_year: str):
        records = self.sheet_old.get_all_records()
        total = 0
        for row in records:
            date_val = str(row.get('Дата', '')).strip()
            parts = date_val.split('.')
            if len(parts) == 3:
                row_month_year = f"{parts[1]}.{parts[2]}"
                if row_month_year == month_year:
                    try:
                        val = str(row.get('Часы', 0)).replace(',', '.').strip()
                        total += float(val)
                    except ValueError:
                        continue
        return total

    def get_all_data_for_analytics(self):
        records = self.sheet_old.get_all_records()
        stats = {}
        for row in records:
            date_val = str(row.get('Дата', '')).strip()
            try:
                parts = date_val.split(".")
                if len(parts) < 3: continue
                month_year = f"{parts[1]}.{parts[2]}"
                hours_str = str(row.get('Часы', 0)).replace(',', '.').strip()
                stats[month_year] = stats.get(month_year, 0) + float(hours_str)
            except (ValueError, IndexError):
                continue
        return stats


gs_service = GoogleSheetsService()