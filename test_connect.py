import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Настройки доступа
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)
client = gspread.authorize(creds)

# Открываем таблицу по ID (возьми его из своего .env или браузера)
sheet_id = "1lJtqnCpCUHmURX4JmWa5vJYy-kXqz67hUDR1Z_wK5N0"
sheet = client.open_by_key(sheet_id).sheet1

# Попробуем что-то записать в ячейку A1
sheet.update_acell('A1', 'Связь установлена!')
print("Проверь таблицу! В ячейке A1 должен появиться текст.")