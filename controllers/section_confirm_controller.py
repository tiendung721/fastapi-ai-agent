from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
import pandas as pd
import time

from common.session_store import SessionStore
from common.models import Section
from data_processing.validators import to_zero_based, validate_sections_zero_based, IndexErrorDetail

# Học rule & lưu rule
from data_processing.rule_learning_gpt import learn_rule_from_sections
from data_processing.rule_memory import get_fingerprint, save_rule_for_fingerprint
from data_processing.rule_based_extractor import extract_sections_with_rule
from data_processing.chat_memory import memory

# ★ Promote candidate (đề xuất học từ chat)
from data_processing.rule_learning_from_chat import promote_best_candidates

router = APIRouter()
store = SessionStore()


def _read_df(file_path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
    ext = (file_path or "").lower().split(".")[-1]
    if ext == "csv":
        return pd.read_csv(file_path)
    try:
        return pd.read_excel(file_path, sheet_name=sheet_name)
    except TypeError:
        return pd.read_excel(file_path)


def _pick_sections_from_input_or_session(
    sections_in: Optional[List[Dict]],
    session_obj,
) -> List[Dict]:
    if sections_in and len(sections_in) > 0:
        return sections_in
    auto_sections = getattr(session_obj, "auto_sections", None)
    if auto_sections and len(auto_sections) > 0:
        return [s.model_dump() if hasattr(s, "model_dump") else s.__dict__ for s in auto_sections]
    raise HTTPException(status_code=400, detail="Thiếu 'sections' và session cũng không có auto_sections.")


@router.post("/confirm_sections")
def confirm_sections(
    session_id: str,
    sections: Optional[List[Dict]] = None,
    sheet_name: Optional[str] = None,
    user_id: Optional[str] = "default_user",
):
    # 1) Lấy session
    data = store.get(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Session không tồn tại")

    # 1.1) Khóa double-confirm
    if getattr(data, "confirming", False):
        raise HTTPException(status_code=409, detail="Confirm đang chạy. Vui lòng thử lại sau.")
    setattr(data, "confirming", True)
    store.upsert(data)

    try:
        # 2) Đọc DataFrame
        try:
            df = _read_df(data.file_path, sheet_name=sheet_name)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Không đọc được file: {e}")
        if df.shape[0] == 0:
            raise HTTPException(status_code=400, detail="File/sheet rỗng")

        # 3) Lấy sections (raw) từ payload hoặc từ session.auto_sections
        try:
            sections_raw = _pick_sections_from_input_or_session(sections, data)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Không thể xác định sections: {e}")

        # 4) ✅ CHỈ VALIDATE 0‑BASED, KHÔNG CONVERT (tránh “trừ 1” nhầm)
        #    Nếu validate fail, mới thử fallback convert 1->0 một lần.
        try:
            sections_zb = validate_sections_zero_based(sections_raw, nrows=df.shape[0])
            index_base = "zero"
        except IndexErrorDetail as ie_primary:
            # Fallback an toàn: chỉ thử nếu người dùng lỡ gửi 1‑based.
            try:
                sections_try = to_zero_based(sections_raw, nrows=df.shape[0])
                sections_zb = validate_sections_zero_based(sections_try, nrows=df.shape[0])
                index_base = "one->zero_auto"
            except Exception:
                return {"ok": False, "code": ie_primary.code, "error": str(ie_primary)}

        # 5) Lưu confirmed_sections vào session (GIỮ NGUYÊN 0‑BASED)
        data.confirmed_sections = [Section(**s) for s in sections_zb]
        if not getattr(data, "user_id", None):
            try:
                data.user_id = user_id
            except Exception:
                pass
        store.upsert(data)

        # 6) Học rule (structured → fallback overrides)
        auto_learned = False
        rule_version: Optional[str] = None
        learn_method: Optional[str] = None
        fp_used: Optional[str] = None
        promoted: bool = False

        try:
            # 6.1) fingerprint
            try:
                fp_used = get_fingerprint(df, sheet_name=sheet_name)
            except TypeError:
                fp_used = get_fingerprint(df)

            # 6.2) NHÁNH 1: structured bằng GPT (ưu tiên)
            try:
                learned_rule = learn_rule_from_sections(
                    file_path=data.file_path,
                    sections=sections_zb,
                    sheet_name=sheet_name
                )
                trial = extract_sections_with_rule(df, learned_rule) or []
                # Dù rule có trả gì, ép về & validate 0‑based trước khi chấp nhận
                trial = to_zero_based(trial, nrows=df.shape[0])
                trial = validate_sections_zero_based(trial, nrows=df.shape[0])

                if len(trial) > 0:
                    try:
                        save_rule_for_fingerprint(fp_used, learned_rule, user_id=user_id)
                    except TypeError:
                        save_rule_for_fingerprint(fp_used, learned_rule)
                    auto_learned = True
                    learn_method = "structured_gpt"
            except Exception:
                pass

            # 6.3) NHÁNH 2: Fallback overrides (GIỮ 0‑BASED, KHÔNG trừ 1)
            if not auto_learned:
                overrides = {"sections": []}
                headers = {int(s["header_row"]) for s in sections_zb}
                if len(headers) == 1:
                    overrides["header_row"] = int(list(headers)[0])  # 0‑based

                for idx, s in enumerate(sections_zb, start=1):
                    fields = {
                        "start_row": int(s["start_row"]),   # 0‑based
                        "end_row": int(s["end_row"]),       # 0‑based (inclusive)
                        "header_row": int(s["header_row"]), # 0‑based
                    }
                    if s.get("label"):
                        fields["label"] = s["label"]
                    overrides["sections"].append({
                        "selector": {"by": "index", "value": f"S{idx}"},
                        "fields": fields
                    })

                rule_overrides = {
                    "version": int(time.time()),
                    "updated_at": int(time.time()),
                    "overrides": overrides
                }

                try:
                    save_rule_for_fingerprint(fp_used, rule_overrides, user_id=user_id)
                except TypeError:
                    save_rule_for_fingerprint(fp_used, rule_overrides)

                auto_learned = True
                learn_method = "overrides_fallback"
                rule_version = str(rule_overrides["version"])

            # 6.4) Promote
            try:
                promoted = promote_best_candidates(user_id, fp_used)
            except Exception:
                promoted = False

        except Exception:
            auto_learned = False
            promoted = False
            learn_method = None

        # 7) Memory & 8) Trả kết quả
        try:
            memory.add_record(user_id or "anonymous", {
                "event": "confirm",
                "session_id": session_id,
                "sections_count": len(sections_zb),
                "auto_learned_rule": bool(auto_learned),
                "rule_version": rule_version,
                "learn_method": learn_method,
                "index_base": index_base,
                "timestamp": int(time.time())
            })
        except Exception:
            pass

        return {
            "ok": True,
            "code": "CONFIRMED",
            "data": {
                "count": len(sections_zb),
                "sections": sections_zb,       # ← GIỮ NGUYÊN 0‑BASED BẠN GỬI
                "fingerprint": fp_used,
                "learn_method": learn_method
            },
            "auto_learned_rule": auto_learned,
            "rule_version": rule_version,
            "promoted": promoted
        }

    finally:
        setattr(data, "confirming", False)
        store.upsert(data)
