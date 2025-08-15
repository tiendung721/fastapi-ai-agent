from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
import pandas as pd
import time 

from common.session_store import SessionStore
from common.models import Section
from data_processing.validators import to_one_based, validate_sections, IndexErrorDetail

# Học rule & lưu rule
from data_processing.rule_learning_gpt import learn_rule_from_sections
from data_processing.rule_memory import get_fingerprint, save_rule_for_fingerprint
from data_processing.rule_based_extractor import extract_sections_with_rule
from data_processing.chat_memory import memory


router = APIRouter()
store = SessionStore()

def _read_df(file_path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
    ext = (file_path or "").lower().split(".")[-1]
    if ext == "csv":
        return pd.read_csv(file_path)
    return pd.read_excel(file_path, sheet_name=sheet_name)

@router.post("/confirm_sections")
def confirm_sections(
    session_id: str,
    sections: List[Dict],
    sheet_name: Optional[str] = None,
    user_id: Optional[str] = "default_user",
):
    """
    - Chuẩn hóa & validate sections (1-based).
    - Lưu confirmed_sections vào SessionStore.
    - Tự học rule ngay sau confirm; chỉ lưu rule nếu DRY-RUN áp lại rule cho ra section hợp lệ.
    - Trả về count + danh sách sections đã xác nhận + cờ auto_learned_rule.
    """
    # 1) Lấy session
    data = store.get(session_id)
    if not data:
        raise HTTPException(status_code=404, detail=" Session không tồn tại")

    # 2) Đọc dữ liệu để validate theo kích thước thực tế
    try:
        df = _read_df(data.file_path, sheet_name=sheet_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Không đọc được file: {e}")
    if df.shape[0] == 0:
        raise HTTPException(status_code=400, detail="File/sheet rỗng")

    # 3) Chuẩn hóa + validate 1-based
    try:
        sections = to_one_based(sections, nrows=df.shape[0])
        sections = validate_sections(sections, nrows=df.shape[0])
    except IndexErrorDetail as ie:
        # Trả về đúng code lỗi của validator (ví dụ: SECTIONS_EMPTY/INDEX_OUT_OF_RANGE)
        return {"ok": False, "code": ie.code, "error": str(ie)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Sections không hợp lệ: {e}")

    # 4) Lưu confirmed_sections vào session (Pydantic)
    data.confirmed_sections = [Section(**s) for s in sections]
    # Ghi user_id nếu trước đó chưa có (để preview lần sau tra đúng kho rule theo user)
    if not getattr(data, "user_id", None):
        try:
            data.user_id = user_id
        except Exception:
            pass
    store.upsert(data)

    # 5) Học & DRY-RUN rule (không chặn luồng nếu lỗi)
    auto_learned = False
    try:
        # Tạo fingerprint (hỗ trợ cả version có/không có sheet_name)
        try:
            fp = get_fingerprint(df, sheet_name=sheet_name)  # nếu hàm có tham số sheet_name
        except TypeError:
            fp = get_fingerprint(df)  # tương thích với version cũ

        # Học rule từ sections đã xác nhận
        learned_rule = learn_rule_from_sections(
            file_path=data.file_path,
            sections=sections,
            sheet_name=sheet_name
        )

        # ✅ DRY-RUN: áp thử rule lên df, chỉ lưu nếu có section hợp lệ
        trial = extract_sections_with_rule(df, learned_rule) or []
        trial = to_one_based(trial, nrows=df.shape[0])
        trial = validate_sections(trial, nrows=df.shape[0])

        if len(trial) > 0:
            save_rule_for_fingerprint(fp, learned_rule, user_id=user_id)
            auto_learned = True
        # else: rule chưa đủ tốt → KHÔNG lưu, tránh gây lỗi SECTIONS_EMPTY về sau

    except Exception:
        # Bất kỳ lỗi nào trong quá trình học/DRY-RUN sẽ không chặn confirm
        auto_learned = False

    memory.add_record(user_id or "anonymous", {
        "event": "confirm",
        "session_id": session_id,
        "sections_count": len(sections),
        "auto_learned_rule": bool(auto_learned),
        "timestamp": int(time.time())
    })


    # 6) Trả về kết quả (kèm danh sách sections đã xác nhận)
    return {
        "ok": True,
        "code": "CONFIRMED",
        "data": {
            "count": len(sections),
            "sections": sections
        },
        "auto_learned_rule": auto_learned
    }
