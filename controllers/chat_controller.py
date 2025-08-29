# controllers/chat_controller.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import pandas as pd

from common.session_store import SessionStore
from common.models import Section
from data_processing.chat_memory import memory
from services.intent_llm import parse_intent_llm  # ← dùng LLM để hiểu câu nói

# ★ Học từ chat: ghi candidate
from data_processing.rule_learning_from_chat import upsert_candidate
from data_processing.rule_memory import get_fingerprint

router = APIRouter()
store = SessionStore()

# ====== Helpers đọc dữ liệu & áp dụng thay đổi ======

def _read_df(file_path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
    ext = (file_path or "").lower().split(".")[-1]
    if ext == "csv":
        return pd.read_csv(file_path)
    try:
        return pd.read_excel(file_path, sheet_name=sheet_name, header=None)

    except TypeError:
        return pd.read_excel(file_path)

def _idx_from_sid(sid: str) -> int:
    """ 'S1' -> 0 ; 's2' -> 1 ; '1' -> 0 """
    if isinstance(sid, int):
        return sid - 1
    s = str(sid).strip().upper()
    if s.startswith("S"):
        s = s[1:]
    try:
        return int(s) - 1
    except Exception:
        return -1

def _merge_sections(sections: List[Section], sids: List[str]) -> List[Section]:
    if len(sids) != 2:
        return sections
    i1, i2 = _idx_from_sid(sids[0]), _idx_from_sid(sids[1])
    if not (0 <= i1 < len(sections) and 0 <= i2 < len(sections)):
        return sections
    s1, s2 = sections[i1], sections[i2]
    start = min(s1.start_row, s2.start_row)
    end = max(s1.end_row, s2.end_row)
    header = s1.header_row if s1.header_row == s2.header_row else min(s1.header_row, s2.header_row)
    label = s1.label or f"Section {i1+1}"
    merged = Section(start_row=start, end_row=end, header_row=header, label=label)
    new = [sec for k, sec in enumerate(sections) if k not in (i1, i2)]
    new.insert(min(i1, i2), merged)
    return new

def _set_header_row(sections: List[Section], header_row: int) -> List[Section]:
    out: List[Section] = []
    for s in sections:
        d = s.model_dump() if hasattr(s, "model_dump") else s.__dict__
        d = {**d, "header_row": int(header_row)}
        out.append(Section(**d))
    return out

def _rename_section(sections: List[Section], sid: str, label: str) -> List[Section]:
    idx = _idx_from_sid(sid)
    if 0 <= idx < len(sections):
        d = sections[idx].model_dump() if hasattr(sections[idx], "model_dump") else sections[idx].__dict__
        d = {**d, "label": str(label)}
        sections[idx] = Section(**d)
    return sections

def _remove_section(sections: List[Section], sid: str) -> List[Section]:
    idx = _idx_from_sid(sid)
    if 0 <= idx < len(sections):
        return [s for i, s in enumerate(sections) if i != idx]
    return sections

def _set_start_row(sections: List[Section], sid: str, val: int) -> List[Section]:
    idx = _idx_from_sid(sid)
    if 0 <= idx < len(sections):
        sections[idx].start_row = int(val)
    return sections

def _set_end_row(sections: List[Section], sid: str, val: int) -> List[Section]:
    idx = _idx_from_sid(sid)
    if 0 <= idx < len(sections):
        sections[idx].end_row = int(val)
    return sections

def _set_range(sections: List[Section], sid: str, a: int, b: int) -> List[Section]:
    idx = _idx_from_sid(sid)
    if 0 <= idx < len(sections):
        sections[idx].start_row = int(a)
        sections[idx].end_row = int(b)
    return sections

def _set_group_by_all(sections: List[Section], col: str) -> List[Section]:
    for s in sections:
        if hasattr(s, "group_by"):
            s.group_by = col
    return sections

def _set_group_by(sections: List[Section], sid: str, col: str) -> List[Section]:
    idx = _idx_from_sid(sid)
    if 0 <= idx < len(sections):
        if hasattr(sections[idx], "group_by"):
            sections[idx].group_by = col
    return sections

# ====== API models ======

class ChatRequest(BaseModel):
    session_id: str
    message: str
    sheet_name: Optional[str] = None

class ChatResponse(BaseModel):
    assistant_reply: str
    intent: str
    arguments: Dict[str, Any]
    preview: Dict[str, Any]

# Endpoint chính: dùng LLM NLU + ghi candidate

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    data = store.get(req.session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Session không tồn tại")
    user_id = getattr(data, "user_id", None) or "anonymous"

    # lưu hội thoại người dùng
    memory.add_record(user_id, {"role": "user", "session_id": req.session_id, "content": req.message})

    # 1) Dùng LLM để trích intent + arguments
    parsed = parse_intent_llm(req.message)  
    intent: str = parsed.get("intent", "unknown")
    args: Dict[str, Any] = parsed.get("arguments", {}) or {}
    confidence: float = float(parsed.get("confidence", 0.75))

    sections: List[Section] = getattr(data, "auto_sections", []) or []
    reply = ""

    # 2) Áp dụng intent (vừa chỉnh preview, vừa gom 'operations' để học)
    operations: List[Dict[str, Any]] = []

    if intent == "set_header_row":
        hdr = int(args.get("header_row", 0))
        sections = _set_header_row(sections, hdr)
        operations.append({"op": "update_all", "fields": {"header_row": hdr}})
        reply = f"Đã đặt header_row = {hdr} cho tất cả sections."

    elif intent == "merge_sections":
        sids = args.get("section_ids", [])
        before = len(sections)
        sections = _merge_sections(sections, sids)
        if len(sections) < before:
            operations.append({"op": "merge", "section_ids": sids})
            reply = f"Đã gộp {', '.join(map(str, sids))}."
        else:
            reply = "Không gộp được sections. Kiểm tra lại chỉ số."

    elif intent == "rename_section":
        sid = args.get("section_id"); label = args.get("label", "")
        sections = _rename_section(sections, sid, label)
        operations.append({"op": "rename", "selector": {"by": "index", "value": sid}, "fields": {"label": label}})
        reply = f"Đã đổi tên {sid} thành “{label}”." if sid else "Thiếu section_id."

    elif intent == "remove_section":
        sid = args.get("section_id")
        new_sections = _remove_section(sections, sid)
        if len(new_sections) < len(sections):
            sections = new_sections
            operations.append({"op": "delete", "selector": {"by": "index", "value": sid}})
            reply = f"Đã bỏ {sid}."
        else:
            reply = f"Không tìm thấy {sid}."

    elif intent == "set_start_row":
        sid = args.get("section_id"); val = int(args.get("start_row", 0))
        sections = _set_start_row(sections, sid, val)
        operations.append({"op": "update", "selector": {"by": "index", "value": sid}, "fields": {"start_row": val}})
        reply = f"Đã đặt start_row của {sid} = {val}."

    elif intent == "set_end_row":
        sid = args.get("section_id"); val = int(args.get("end_row", 0))
        sections = _set_end_row(sections, sid, val)
        operations.append({"op": "update", "selector": {"by": "index", "value": sid}, "fields": {"end_row": val}})
        reply = f"Đã đặt end_row của {sid} = {val}."

    elif intent == "set_section_range":
        sid = args.get("section_id"); a = int(args.get("start_row", 0)); b = int(args.get("end_row", 0))
        sections = _set_range(sections, sid, a, b)
        operations.append({"op": "update", "selector": {"by": "index", "value": sid}, "fields": {"start_row": a, "end_row": b}})
        reply = f"Đã đặt khoảng dòng {sid}: {a} → {b}."

    elif intent == "set_group_by_all":
        col = str(args.get("column", "")).strip()
        sections = _set_group_by_all(sections, col)
        operations.append({"op": "update_all", "fields": {"group_by": col}})
        reply = f"Đã đặt group_by = “{col}” cho tất cả sections."

    elif intent == "set_group_by":
        sid = args.get("section_id"); col = str(args.get("column", "")).strip()
        sections = _set_group_by(sections, sid, col)
        operations.append({"op": "update", "selector": {"by": "index", "value": sid}, "fields": {"group_by": col}})
        reply = f"Đã đặt group_by của {sid} = “{col}”."

    elif intent == "show_preview":
        reply = "Đây là preview hiện tại."

    elif intent == "confirm":
        reply = "Bạn có thể gọi /confirm_sections để lưu rule từ các section đã chỉnh."

    else:
        reply = "Mình chưa hiểu yêu cầu này. Bạn thử nói ngắn gọn, ví dụ: 'gộp 1 và 2', 'S1 từ 10 đến 32', 'đặt header 7'."

    # 3) Lưu lại thay đổi vào session (preview sống)
    data.auto_sections = sections
    store.upsert(data)

    # 4)  Ghi CANDIDATE để “học dần” (không chặn luồng nếu lỗi)
    try:
        df = _read_df(data.file_path, sheet_name=req.sheet_name)
        fp = get_fingerprint(df)
        patch_spec = {
            "intent": "edit_sections",
            "operations": operations
        }
        if operations:
            upsert_candidate(user_id, fp, patch_spec, confidence)
    except Exception:
        pass

    # 5) Trả preview sau chỉnh
    preview = {
        "used_rule": getattr(data, "used_rule", False),
        "index_base": "zero",  # thêm dòng này
        "auto_sections": [s.model_dump() for s in sections]
    }

    # lưu phản hồi assistant
    memory.add_record(user_id, {
        "role": "assistant",
        "session_id": req.session_id,
        "intent": intent,
        "reply": reply
    })

    return ChatResponse(
        assistant_reply=reply,
        intent=intent,
        arguments=args,
        preview=preview
    )
