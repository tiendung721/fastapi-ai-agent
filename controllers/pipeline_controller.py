from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import pandas as pd
from common.session_store import SessionStore
from data_processing.validators import validate_sections
from data_processing.analyzer import run_analysis
from data_processing.planner import build_report
from data_processing.rule_learning_gpt import learn_rule_from_sections
from data_processing.rule_memory import get_fingerprint, save_rule_for_fingerprint
from data_processing.exporter import save_report_excel  # ✅ Thêm exporter
from data_processing.chat_memory import memory
import time

router = APIRouter()
store = SessionStore()

def _load_df(file_path: str, sheet_name: Optional[str] = None):
    ext = (file_path or "").lower().split(".")[-1]
    if ext == "csv":
        return pd.read_csv(file_path)
    return pd.read_excel(file_path, sheet_name=sheet_name)

def _pick_sections(data):
    if data.confirmed_sections and len(data.confirmed_sections) > 0:
        return [s.model_dump() for s in data.confirmed_sections], True
    if data.auto_sections and len(data.auto_sections) > 0:
        return [s.model_dump() for s in data.auto_sections], False
    return [], False

@router.post("/run_final")
def run_final(
    session_id: str,
    sheet_name: Optional[str] = None,
    force: bool = Query(False),
    user_id: Optional[str] = "default_user"
):
    """
    - Ưu tiên chạy với confirmed_sections; nếu chưa confirm và force=false → yêu cầu xác nhận.
    - Nếu force=true → dùng auto_sections.
    - Tự học rule nếu dùng auto_sections.
    - Xuất file báo cáo Excel sau khi hoàn tất.
    """
    data = store.get(session_id)
    if not data:
        raise HTTPException(status_code=404, detail=" Session ID không tồn tại.")
    df = _load_df(data.file_path, sheet_name=sheet_name)

    sections, is_confirmed = _pick_sections(data)
    if not sections:
        raise HTTPException(status_code=400, detail=" Không có sections (auto hoặc confirmed).")

    sections = validate_sections(sections, nrows=df.shape[0])

    if (not is_confirmed) and (not force):
        return {
            "ok": False,
            "code": "NEED_CONFIRM",
            "message": "Chưa xác nhận sections; thêm force=true để chạy tạm bằng auto."
        }

    # 1️⃣ Phân tích dữ liệu
    analysis = run_analysis(df, sections, params=None)

    # 2️⃣ Sinh báo cáo text
    report = build_report(analysis)

    # 3️⃣ Xuất file Excel
    try:
        export_path = save_report_excel(user_id, report, folder="output")
    except Exception as e:
        export_path = None

    # 4️⃣ Tự học rule nếu dùng auto_sections
    auto_learn = False
    if not is_confirmed:
        try:
            fp = get_fingerprint(df)
            learned_rule = learn_rule_from_sections(
                file_path=data.file_path,
                sections=sections,
                sheet_name=sheet_name
            )
            save_rule_for_fingerprint(fp, learned_rule, user_id=user_id)
            auto_learn = True
        except Exception as e:
            return {
                "ok": True,
                "code": "FINAL_OK",
                "data": {
                    "analysis": analysis,
                    "report": report,
                    "export_file": export_path
                },
                "warn": f"Auto-learn rule (force/auto_sections) gặp lỗi, đã bỏ qua: {e}"
            }
        
    memory.add_record(user_id or "anonymous", {
        "event": "final",
        "session_id": session_id,
        "sections_count": analysis.get("sections_count") if isinstance(analysis, dict) else None,
        "total_rows": analysis.get("total_rows") if isinstance(analysis, dict) else None,
        "export_file": export_path,
        "timestamp": int(time.time())
    })


    return {
        "ok": True,
        "code": "FINAL_OK",
        "data": {
            "analysis": analysis,
            "report": report,
            "export_file": export_path
        },
        "auto_learned_rule": auto_learn
    }
