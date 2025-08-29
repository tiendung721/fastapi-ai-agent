from typing import List, Dict

class IndexErrorDetail(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)

# ===========================
# ZERO-BASED HELPERS
# ===========================

def to_zero_based(sections: List[Dict], nrows: int) -> List[Dict]:
    """
    Chỉ đưa về 0‑based khi có DẤU HIỆU 1‑based RÕ RÀNG.
    Tiêu chí: nếu BẤT KỲ chỉ số nào (start/end/header) == nrows (vượt biên 0‑based),
    ta coi list này là 1‑based và trừ 1 cho cả bộ.
    Ngược lại: GIỮ NGUYÊN (tránh trừ nhầm gây lệch -1).
    """
    if not sections:
        return []

    # phát hiện 1-based: có ít nhất một end/start/header == nrows
    probably_one_based = False
    for s in sections:
        sr = int(s.get("start_row", 0))
        er = int(s.get("end_row", 0))
        hr = int(s.get("header_row", 0))
        if sr == nrows or er == nrows or hr == nrows:
            probably_one_based = True
            break

    out: List[Dict] = []
    for s in sections:
        sr = int(s.get("start_row", 0))
        er = int(s.get("end_row", 0))
        hr = int(s.get("header_row", 0))
        if probably_one_based:
            sr = max(0, sr - 1)
            er = max(0, er - 1)
            hr = max(0, hr - 1)
        out.append({
            "start_row": sr,
            "end_row": er,
            "header_row": hr,
            "label": s.get("label", "")
        })
    return out


def validate_sections_zero_based(sections: List[Dict], nrows: int) -> List[Dict]:
    """Clamp & validate cho 0‑based với end_row inclusive."""
    if not sections:
        raise IndexErrorDetail("SECTIONS_EMPTY", "Không có section nào để xử lý")
    checked: List[Dict] = []
    for s in sections:
        sr = int(s["start_row"])
        er = int(s["end_row"])
        hr = int(s["header_row"])
        if not (0 <= hr <= sr <= er <= nrows - 1):
            raise IndexErrorDetail(
                "INDEX_OUT_OF_RANGE",
                f"header_row={hr}, start_row={sr}, end_row={er}, nrows={nrows}"
            )
        checked.append({
            "start_row": sr,
            "end_row": er,
            "header_row": hr,
            "label": s.get("label", "")
        })
    return checked
