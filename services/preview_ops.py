from typing import Dict, Any, List

def set_header_row(preview: Dict[str, Any], header_row: int):
    preview["header_row"] = header_row
    
# tuỳ kiến trúc cũ: nếu cần thì reset sections khi đổi header
def merge_sections(preview: Dict[str, Any], section_ids: List[str]):
    secs = preview.get("sections", [])
    id_map = {s["section_id"]: s for s in secs}
    if len(section_ids) < 2: return
    first = id_map.get(section_ids[0])
    for sid in section_ids[1:]:
        s = id_map.get(sid)
        if not (first and s):
            continue
        # mở rộng biên
        first["start_row"] = min(first["start_row"], s["start_row"])
        first["end_row"] = max(first["end_row"], s["end_row"])
        first["rows"] = first["end_row"] - first["start_row"] + 1
        # xoá section s
        secs[:] = [x for x in secs if x["section_id"] != sid]

# chuẩn hoá lại thứ tự id nếu cần
def set_group_by(preview: Dict[str, Any], column: str, section_id: str | None = None):
    secs = preview.get("sections", [])
    if section_id:
        for s in secs:
            if s["section_id"] == section_id:
                s["group_by"] = column
    else:
        for s in secs:
            s["group_by"] = column

def rename_section(preview: Dict[str, Any], section_id: str, label: str):
    for s in preview.get("sections", []):
        if s["section_id"] == section_id:
            s["label"] = label

def remove_section(preview: Dict[str, Any], section_id: str):
    secs = preview.get("sections", [])
    preview["sections"] = [s for s in secs if s["section_id"] != section_id]