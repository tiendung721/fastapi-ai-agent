# section_detector.py
import pandas as pd

def detect_sections_auto(df: pd.DataFrame):
    sections = []
    in_section = False
    start_row = None
    header_row = None
    section_id = 1

    def is_header_row(row):
        text_cells = sum(1 for cell in row if isinstance(cell, str) and len(cell.strip()) >= 2)
        num_cells = sum(1 for cell in row if isinstance(cell, (int, float)))
        return text_cells >= 2 and num_cells == 0

    def is_data_row(row):
        text_or_num = sum(1 for cell in row if pd.notna(cell) and str(cell).strip() != "")
        return text_or_num >= 2

    for i in range(len(df)):
        row = df.iloc[i]

        # Dòng trống hoàn toàn
        if row.isnull().all():
            if in_section:
                sections.append({
                    "start_row": start_row + 1,
                    "end_row": i + 1,
                    "header_row": header_row + 1,
                    "label": f"Section {section_id}"
                })
                section_id += 1
                in_section = False
                start_row = None
                header_row = None
            continue

        if not in_section and is_header_row(row):
            in_section = True
            header_row = i
            start_row = i + 1  # Bắt đầu lấy data sau header
            continue

        if in_section and not is_data_row(row):
            # Ngắt nếu gặp dòng không còn dữ liệu hợp lệ
            sections.append({
                "start_row": start_row + 1,
                "end_row": i + 1,
                "header_row": header_row + 1,
                "label": f"Section {section_id}"
            })
            section_id += 1
            in_section = False
            start_row = None
            header_row = None

    # Nếu còn section chưa kết thúc
    if in_section and start_row is not None:
        sections.append({
            "start_row": start_row + 1,
            "end_row": len(df),
            "header_row": header_row + 1,
            "label": f"Section {section_id}"
        })

    return sections
