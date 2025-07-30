# report_exporter.py
import os
from openpyxl import Workbook
from datetime import datetime

def save_report_excel(user_id: str, report_text: str, folder: str = "output") -> str:
    os.makedirs(folder, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{user_id}_{timestamp}.xlsx"
    path = os.path.join(folder, filename)

    wb = Workbook()
    ws = wb.active
    ws.title = "Báo cáo"

    for i, line in enumerate(report_text.splitlines(), start=1):
        ws.cell(row=i, column=1).value = line

    wb.save(path)
    return path
