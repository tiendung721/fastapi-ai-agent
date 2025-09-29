from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import pandas as pd
import time

from common.session_store import SessionStore
from data_processing.validators import validate_sections_zero_based, to_zero_based
from data_processing.analyzer import run_analysis
from data_processing.planner import build_report
from data_processing.rule_learning_gpt import learn_rule_from_sections
from data_processing.rule_memory import get_fingerprint, save_rule_for_fingerprint
from data_processing.exporter import save_report_excel
from data_processing.chat_memory import memory
from data_processing.rule_learning_from_chat import promote_best_candidates


router = APIRouter()
store = SessionStore()

def _load_df(file_path: str, sheet_name: Optional[str] = None):
    ext = (file_path or "").lower().split(".")[-1]
    if ext == "csv":
        return pd.read_csv(file_path, header=None) 
    try:
        return pd.read_excel(file_path, sheet_name=sheet_name, header=None)  
    except TypeError:
        return pd.read_excel(file_path, header=None)  

def _pick_sections(data) -> tuple[list[dict], bool]:
    if data.confirmed_sections and len(data.confirmed_sections) > 0:
        return [s.model_dump() for s in data.confirmed_sections], True
    if data.auto_sections and len(data.auto_sections) > 0:
        return [s.model_dump() for s in data.auto_sections], False
    return [], False

class FinalIn(BaseModel):
    user_id: str
    session_id: str
    sheet_name: Optional[str] = None
    force: bool = False

@router.post("/final")
def run_final(payload: FinalIn) -> Dict[str, Any]:
    data = store.get(payload.session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Session ID không tồn tại.")

    df = _load_df(data.file_path, sheet_name=payload.sheet_name)

    sections, is_confirmed = _pick_sections(data)
    if not sections:
        return {
            "ok": False,
            "code": "NO_SECTIONS",
            "error": "Không có sections (auto hoặc confirmed). Hãy /preview và/hoặc /chat trước.",
        }

    
    try:
        if is_confirmed:
            sections = validate_sections_zero_based(sections, nrows=df.shape[0])
        else:
            sections = to_zero_based(sections, nrows=df.shape[0])
            sections = validate_sections_zero_based(sections, nrows=df.shape[0])
    except Exception as e:
        return {"ok": False, "code": "INVALID_SECTIONS", "error": f"Sections không hợp lệ: {e}"}

    if (not is_confirmed) and (not payload.force):
        return {
            "ok": False,
            "code": "NEED_CONFIRM",
            "error": "Chưa xác nhận sections; gửi force=true để chạy tạm bằng auto hoặc hãy /confirm_sections.",
        }

    analysis = run_analysis(df, sections, params=None)
    report = build_report(analysis)

    export_path = None
    try:
        export_path = save_report_excel(
            report=report,
            session_id=payload.session_id,
            filename_prefix=payload.user_id  
        )
    except Exception as e:
        export_path = None

    # Lưu RULE
    auto_learned_rule = False
    warn = None
    fp = None
    try:
        fp = get_fingerprint(df, sheet_name=payload.sheet_name)
    except TypeError:
        fp = get_fingerprint(df)

    if is_confirmed:
        try:
            structured_rule = {
                "version": "1.2",
                "type": "structured",
                "index_base": "zero",
                "header_row": int(sections[0]["header_row"]) if sections else 0,
                "sections": sections,
            }
            save_rule_for_fingerprint(fp, structured_rule, user_id=payload.user_id)
        except Exception as e:
            warn = (warn or "") + f" | Lưu structured rule gặp lỗi: {e}"
    else:
        try:
            learned_rule = learn_rule_from_sections(
                file_path=data.file_path,
                sections=sections,
                sheet_name=payload.sheet_name,
            )
            
            if isinstance(learned_rule, dict):
                if isinstance(learned_rule.get("sections"), list):
                    learned_rule["sections"] = validate_sections_zero_based(
                        to_zero_based(learned_rule["sections"], nrows=df.shape[0]),
                        nrows=df.shape[0]
                    )
                if isinstance(learned_rule.get("header_row"), int) and learned_rule.get("index_base") != "zero":
                    hr = max(0, int(learned_rule["header_row"]) - 1)
                    learned_rule["header_row"] = hr
                learned_rule["index_base"] = "zero"
                learned_rule["version"] = "1.2"
            save_rule_for_fingerprint(fp, learned_rule, user_id=payload.user_id)
            auto_learned_rule = True
        except Exception as e:
            warn = (warn or "") + f" | Auto-learn rule (force/auto_sections) gặp lỗi, đã bỏ qua: {e}"

    promoted = False
    try:
        if fp is None:
            fp = get_fingerprint(df, sheet_name=payload.sheet_name)
        promoted = promote_best_candidates(payload.user_id, fp)
    except Exception:
        promoted = False

    try:
        memory.add_record(
            payload.user_id or "anonymous",
            {
                "event": "final",
                "session_id": payload.session_id,
                "used_confirmed_sections": is_confirmed,
                "sections_count": analysis.get("sections_count") if isinstance(analysis, dict) else None,
                "total_rows": analysis.get("total_rows") if isinstance(analysis, dict) else None,
                "export_file": export_path,
                "timestamp": int(time.time()),
            },
        )
    except Exception:
        pass

    resp = {
        "ok": True,
        "code": "FINAL_OK",
        "data": {
            "analysis": analysis,
            "report": report,
            "export": {"excel_path": export_path},
        },
        "used_confirmed_sections": is_confirmed,
        "auto_learned_rule": auto_learned_rule,
        "promoted": promoted,
        "index_base": "zero",
    }
    if warn:
        resp["warn"] = warn.strip(" |")
    return resp
