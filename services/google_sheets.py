import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from config_reader import config


class GoogleSheetsService:
    def __init__(self):
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(config.GOOGLE_KEY_PATH, scope)
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open_by_key(config.SPREADSHEET_ID).sheet1

    def append_hours(self, date_str: str, hours: float):
        # Добавляем: Дата, Часы, Время записи
        self.sheet.append_row([date_str, hours])

    def get_month_report(self, month_year: str):
        records = self.sheet.get_all_records()
        total = 0
        for row in records:
            # .strip() удаляет случайные пробелы в начале и конце
            # .get() ищет ключ, игнорируя лишние пробелы в названии колонки
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
        records = self.sheet.get_all_records()
        stats = {}
        for row in records:
            # Очищаем дату от пробелов
            date_val = str(row.get('Дата', '')).strip()
            try:
                parts = date_val.split(".")
                if len(parts) < 3: continue
                month_year = f"{parts[1]}.{parts[2]}"

                # Очищаем часы от пробелов и меняем запятые
                hours_str = str(row.get('Часы', 0)).replace(',', '.').strip()
                hours = float(hours_str)

                stats[month_year] = stats.get(month_year, 0) + hours
            except (ValueError, IndexError):
                continue
        return stats

# Создаем экземпляр сразу
gs_service = GoogleSheetsService()