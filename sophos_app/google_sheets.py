import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from typing import Dict

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/spreadsheets"]


def update_google_sheet(attendance_dict: Dict[str, str], creds_path: str) -> None:
    """Update Google Sheet with checkmarks for employees who were in office."""
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key("1P3xcHBdCsv5ipolDBp2BNc5iUYmqMsAtCCl0F4JtEk4").worksheet("Sheet1")

    # Get all existing values from the sheet
    data = sheet.get_all_values()
    headers = data[0]
    names = [row[0].strip() for row in data[1:]]

    # Determine today's column index (1-indexed for gspread)
    today = datetime.now().strftime("%Y-%m-%d")
    if today in headers:
        col_index = headers.index(today) + 1
    else:
        col_index = len(headers) + 1
        sheet.update_cell(1, col_index, today)

    # Update tick for each Office attendee
    for i, employee_name in enumerate(names, start=2):
        status = attendance_dict.get(employee_name)
        if status == "Office":
            sheet.update_cell(i, col_index, "✔")