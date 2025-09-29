# -*- coding: utf-8 -*-
"""
exporter.py
- Ghi Excel vào thư mục OUTPUT (mặc định ./output, có thể đổi bằng biến môi trường OUTPUT_DIR)
- Trả về dict {path, filename, url, mime} để FE hiển thị nút tải.
- Hỗ trợ 2 kiểu đầu vào:
  (A) report_sheets: dict[str, pandas.DataFrame]  -> ghi nhiều sheet
  (B) report_text:   str                          -> ghi 1 sheet "Báo cáo" theo từng dòng
"""
from __future__ import annotations
import os, time
from pathlib import Path
from typing import Dict, Optional, Any

import pandas as pd
from openpyxl import Workbook

MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _output_dir() -> str:
    """
    Trả về thư mục output, tự tạo nếu chưa có.
    Ưu tiên env OUTPUT_DIR, fallback ./output
    """
    d = os.getenv("OUTPUT_DIR", os.path.join(os.getcwd(), "output"))
    Path(d).mkdir(parents=True, exist_ok=True)
    return d


def save_report_excel(
    report: Dict[str, pd.DataFrame] | str,
    session_id: str,
    filename_prefix: Optional[str] = None,
) -> Dict[str, Any]:
    """
    report:
      - dict {sheet_name: DataFrame} hoặc
      - str  (text nhiều dòng)
    session_id: dùng cho tên file
    filename_prefix: nếu truyền, sẽ gắn trước session_id trong tên file

    return:
      { "path": <absolute or relative path>,
        "filename": <basename>,
        "url": "/static/<filename>",
        "mime": MIME_XLSX }
    """
    out_dir = _output_dir()
    ts = time.strftime("%Y%m%d_%H%M%S")
    base = f"{filename_prefix.strip()}_" if filename_prefix else ""
    filename = f"{base}{session_id}_{ts}.xlsx"
    path = os.path.join(out_dir, filename)

    
    if isinstance(report, dict):
        
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            for sheet, df in report.items():
                safe_sheet = (sheet or "Sheet1")[:31]
                
                df.to_excel(writer, sheet_name=safe_sheet, index=False, header=False)
    elif isinstance(report, str):
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Báo cáo"
        for i, line in enumerate(report.splitlines(), start=1):
            ws.cell(row=i, column=1).value = line
        wb.save(path)
    else:
        raise TypeError("report must be dict[str, DataFrame] or str")

    return {
        "path": path,
        "filename": filename
    }
