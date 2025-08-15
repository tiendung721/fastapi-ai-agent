from typing import List, Dict

class IndexErrorDetail(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)

_DEF_MIN = 1

def to_one_based(sections: List[Dict], nrows: int) -> List[Dict]:
    """Chuyển 0-based → 1-based an toàn; nếu đã 1-based thì giữ nguyên."""
    out = []
    for s in sections:
        sr = s.get("start_row")
        er = s.get("end_row")
        hr = s.get("header_row")
        if sr is not None and sr < _DEF_MIN: sr += 1
        if er is not None and er < _DEF_MIN: er += 1
        if hr is not None and hr < _DEF_MIN: hr += 1
        out.append({**s, "start_row": sr, "end_row": er, "header_row": hr})
    return out

def validate_sections(sections: List[Dict], nrows: int) -> List[Dict]:
    if not sections:
        raise IndexErrorDetail("SECTIONS_EMPTY", "Không có section nào để xử lý")
    checked = []
    for s in sections:
        sr = int(s["start_row"])
        er = int(s["end_row"])
        hr = int(s["header_row"])
        if not (1 <= hr <= sr <= er <= nrows):
            raise IndexErrorDetail(
                "INDEX_OUT_OF_RANGE",
                f"header_row={hr}, start_row={sr}, end_row={er}, nrows={nrows}"
            )
        checked.append(s)
    return checked
