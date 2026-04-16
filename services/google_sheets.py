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
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        self.sheet.append_row([date_str, hours, now])

    def get_month_report(self, month_year: str):
        # month_year должен быть в формате "04.2026"
        records = self.sheet.get_all_records()
        total = 0
        for row in records:
            if month_year in str(row.get('Дата')):
                total += float(row.get('Часы', 0))
        return total

# Создаем экземпляр сразу
gs_service = GoogleSheetsService()