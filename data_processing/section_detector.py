# section_detector.py
from __future__ import annotations
from typing import List, Dict, Any, Optional
import pandas as pd
import math
import re

def _is_header_row(row: pd.Series, min_text_cells: int = 2) -> bool:
    """
    Heuristic: dòng header có >= min_text_cells ô text (dài >=2),
    và hầu như không phải toàn số.
    """
    text_cells = 0
    num_cells = 0
    for cell in row:
        if pd.isna(cell):
            continue
        s = str(cell).strip()
        if s == "":
            continue
        if isinstance(cell, (int, float)) and not isinstance(cell, bool):
            # xem NaN
            if isinstance(cell, float) and math.isnan(cell):
                continue
            num_cells += 1
        else:
            if len(s) >= 2:
                text_cells += 1
    return text_cells >= min_text_cells and num_cells == 0

def _is_data_row(row: pd.Series, min_non_empty: int = 2) -> bool:
    """Hàng dữ liệu khi có ít nhất min_non_empty ô khác rỗng/NaN."""
    cnt = 0
    for cell in row:
        if pd.isna(cell):
            continue
        s = str(cell).strip()
        if s != "":
            cnt += 1
            if cnt >= min_non_empty:
                return True
    return False

def detect_sections_auto(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Phát hiện section tự động với **0-based** và **end_row inclusive**.
    Mỗi phần tử trả về có dạng:
      { "start_row": int, "end_row": int, "header_row": int, "label": "Section k" }
    """
    sections: List[Dict[str, Any]] = []
    n = len(df)
    if n == 0:
        return sections

    in_section = False
    header_row: Optional[int] = None
    start_row: Optional[int] = None
    section_id = 1

    for i in range(n):
        row = df.iloc[i]

        # Dòng trống hoàn toàn (kết thúc section hiện tại nếu có)
        if row.isna().all():
            if in_section and start_row is not None:
                end_row = i - 1  # inclusive 0-based
                if end_row >= start_row:
                    sections.append({
                        "start_row": start_row,
                        "end_row": end_row,
                        "header_row": header_row if header_row is not None else start_row,
                        "label": f"Section {section_id}"
                    })
                    section_id += 1
                # reset
                in_section = False
                header_row = None
                start_row = None
            continue

        if not in_section:
            # mở section nếu phát hiện header
            if _is_header_row(row):
                in_section = True
                header_row = i
                start_row = i + 1  # dữ liệu bắt đầu sau header
            # nếu chưa thấy header thì bỏ qua
            continue

        # đang trong section
        if not _is_data_row(row):
            # gặp một dòng không đủ dữ liệu → đóng section tới i-1
            if start_row is not None:
                end_row = i - 1
                if end_row >= start_row:
                    sections.append({
                        "start_row": start_row,
                        "end_row": end_row,
                        "header_row": header_row if header_row is not None else start_row,
                        "label": f"Section {section_id}"
                    })
                    section_id += 1
            # reset
            in_section = False
            header_row = None
            start_row = None
            continue

    # Nếu còn section dở dang tới cuối bảng
    if in_section and start_row is not None:
        end_row = n - 1
        if end_row >= start_row:
            sections.append({
                "start_row": start_row,
                "end_row": end_row,
                "header_row": header_row if header_row is not None else start_row,
                "label": f"Section {section_id}"
            })

    return sections
