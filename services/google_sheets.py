import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config_reader import config


class GoogleSheetsService:
    def __init__(self):
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(config.GOOGLE_KEY_PATH, scope)
        self.client = gspread.authorize(creds)

        # Открываем всю книгу
        self.spreadsheet = self.client.open_by_key(config.SPREADSHEET_ID)

        # Подключаем отдельные листы (вкладки)
        self.sheet_old = self.spreadsheet.sheet1  # Твоя "новая" вкладка с часами
        self.sheet_clients = self.spreadsheet.worksheet("Clients")
        self.sheet_schedule = self.spreadsheet.worksheet("Schedule")
        self.sheet_analytics = self.spreadsheet.worksheet("Analytics")

    # --- РАБОТА С КЛИЕНТАМИ ---

    def add_new_client(self, name: str, client_type: str):
        """Добавляет клиента: Имя, Тип, Статус (Актив), Баланс абонемента (0)"""
        self.sheet_clients.append_row([name.strip(), client_type, "Актив", 0])

    def get_active_clients(self):
        """Возвращает список имен только активных клиентов"""
        records = self.sheet_clients.get_all_records()
        active_names = []
        for row in records:
            if str(row.get('Статус', '')).strip() == "Актив":
                active_names.append(str(row.get('Имя клиента', '')).strip())
        return active_names

    # --- СТАРЫЕ МЕТОДЫ ДЛЯ ЧАСОВ (РАБОТАЮТ С СТАРЫМ ЛИСТОМ) ---

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