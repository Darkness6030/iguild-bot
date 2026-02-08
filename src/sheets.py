from contextlib import suppress

import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("assets/google_credentials.json", scope)
client = gspread.authorize(creds)


def add_to_google_sheet(sheet_name: str, data: dict) -> bool:
    worksheet = client.open(sheet_name).sheet1
    headers, values = list(data.keys()), list(data.values())

    with suppress(Exception):
        worksheet.update([headers], '1:1')
        worksheet.append_row(values)
        return True
    return False


def update_google_sheet(sheet_name: str, id_column: str, rows: list) -> bool:
    worksheet = client.open(sheet_name).sheet1
    records = worksheet.get_all_records()

    headers = list(rows[0].keys())
    existing_data = {row[id_column]: index for index, row in enumerate(records, 2)}

    with suppress(Exception):
        worksheet.update([headers], '1:1')

        for row in rows:
            row_id, values = row.get(id_column), list(row.values())
            if row_id in existing_data:
                worksheet.update([values], f'A{existing_data[row_id]}')
            else:
                worksheet.append_row(values)

        return True
    return False
