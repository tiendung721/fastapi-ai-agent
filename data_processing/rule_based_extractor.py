import pandas as pd

def extract_sections_with_rule(df: pd.DataFrame, rule: dict) -> list:
    """
    Dò tìm các section trong file Excel dựa vào rule đã học (start_keywords, end_keywords).
    """
    sections = []
    current_start = None

    for i, row in df.iterrows():
        row_text = " ".join(str(x).lower() for x in row if pd.notna(x))

        
        if any(kw in row_text for kw in rule.get("start_keywords", [])):
            current_start = i

        
        elif current_start is not None and (
            any(kw in row_text for kw in rule.get("end_keywords", [])) or row_text.strip() == ""
        ):
            header_row = current_start + 1
            label = None

            
            section_text = " ".join(
                str(x).lower()
                for row_idx in range(current_start, i)
                for x in df.iloc[row_idx] if pd.notna(x)
            )
            for condition, name in rule.get("label_keywords", {}).items():
                if "chứa" in condition:
                    keyword = condition.split("chứa")[1].strip(" '\"")
                    if keyword in section_text:
                        label = name
                        break

            sections.append({
                "start_row": current_start,
                "end_row": i - 1,
                "header_row": header_row,
                "label": label or "Bảng chưa gán"
            })
            current_start = None

    return sections
