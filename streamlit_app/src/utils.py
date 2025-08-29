from typing import Dict

def to_one_based(sec: Dict) -> Dict:
    return {
        **sec,
        "header_row": sec["header_row"] + 1,
        "start_row": sec["start_row"] + 1,
        "end_row": sec["end_row"] + 1,
    }

def to_zero_based(sec: Dict) -> Dict:
    return {
        **sec,
        "header_row": sec["header_row"] - 1,
        "start_row": sec["start_row"] - 1,
        "end_row": sec["end_row"] - 1,
    }

def clamp_int(v, min_v=0):
    try:
        i = int(v)
        return max(min_v, i)
    except Exception:
        return min_v
