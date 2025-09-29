# controllers/section_confirm_controller.py

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import pandas as pd
import time
import json

from common.session_store import SessionStore
from common.models import Section
from data_processing.validators import to_zero_based, validate_sections_zero_based, IndexErrorDetail


from data_processing.rule_learning_gpt import learn_rule_from_sections
from data_processing.rule_memory import get_fingerprint, save_rule_for_fingerprint
from data_processing.rule_based_extractor import extract_sections_with_rule
from data_processing.chat_memory import memory


from data_processing.rule_learning_from_chat import promote_best_candidates

router = APIRouter()
store = SessionStore()



class SectionIn(BaseModel):
    header_row: int
    start_row: int
    end_row: int
    label: Optional[str] = None


class ConfirmRequest(BaseModel):
    session_id: str
    user_id: Optional[str] = "default_user"
    sheet_name: Optional[str] = None
    sections: Optional[List[SectionIn]] = None



def _read_df(file_path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
    """
    Đọc file mà KHÔNG coi dòng nào là header để:
    - df.index = 0 <-> Excel row 1
    - Tránh lệch +2 khi quy đổi giữa FE (1-based) và BE (0-based)
    """
    ext = (file_path or "").lower().split(".")[-1]
    if ext == "csv":
        return pd.read_csv(file_path, header=None)

    
    if sheet_name is None or str(sheet_name).strip() == "":
        return pd.read_excel(file_path, sheet_name=0, header=None)

    try:
        return pd.read_excel(file_path, sheet_name=sheet_name, header=None)
    except TypeError:
        
        return pd.read_excel(file_path, header=None)


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
    payload: ConfirmRequest = Body(
        ...,
        example={
            "session_id": "12355837-919e-4913-920d-0d9ca07e3acd",
            "user_id": "dung123",
            "sheet_name": "Sheet1",
            "sections": [
                {"header_row": 5, "start_row": 6, "end_row": 32, "label": "Bang chinh"},
                {"header_row": 5, "start_row": 34, "end_row": 49, "label": "Du an thang 2"},
            ],
        },
    )
):
    
    session_id: str = payload.session_id
    user_id: str = payload.user_id or "default_user"
    sheet_name: Optional[str] = payload.sheet_name
    sections_in: Optional[List[Dict]] = (
        [s.model_dump() for s in payload.sections] if payload.sections else None
    )

    if not session_id:
        raise HTTPException(status_code=422, detail="session_id là bắt buộc")

    
    data = store.get(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Session không tồn tại")

    
    if getattr(data, "confirming", False):
        raise HTTPException(status_code=409, detail="Confirm đang chạy. Vui lòng thử lại sau.")
    setattr(data, "confirming", True)
    store.upsert(data)

    try:
        
        try:
            df = _read_df(data.file_path, sheet_name=sheet_name)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Không đọc được file: {e}")
        if df.shape[0] == 0:
            raise HTTPException(status_code=400, detail="File/sheet rỗng")

        
        sections_raw: Optional[List[Dict]] = _pick_sections_from_input_or_session(sections_in, data)

        
        try:
            sections_zb = validate_sections_zero_based(sections_raw, nrows=df.shape[0])
            index_base = "zero"
        except IndexErrorDetail as ie_primary:
            
            try:
                sections_try = to_zero_based(sections_raw, nrows=df.shape[0])
                sections_zb = validate_sections_zero_based(sections_try, nrows=df.shape[0])
                index_base = "one->zero_auto"
            except Exception:
                return {"ok": False, "code": ie_primary.code, "error": str(ie_primary)}

        
        data.confirmed_sections = [Section(**s) for s in sections_zb]
        if not getattr(data, "user_id", None):
            try:
                data.user_id = user_id
            except Exception:
                pass
        store.upsert(data)

        
        auto_learned = False
        rule_version: Optional[str] = None
        learn_method: Optional[str] = None
        fp_used: Optional[str] = None
        promoted: bool = False

        try:
            
            try:
                fp_used = get_fingerprint(df, sheet_name=sheet_name)
            except TypeError:
                fp_used = get_fingerprint(df)

            
            try:
                learned_rule = learn_rule_from_sections(
                    file_path=data.file_path,
                    sections=sections_zb,
                    sheet_name=sheet_name,
                )
                trial = extract_sections_with_rule(df, learned_rule) or []
                
                trial = to_zero_based(trial, nrows=df.shape[0])
                trial = validate_sections_zero_based(trial, nrows=df.shape[0])

                if len(trial) > 0:
                    try:
                        save_rule_for_fingerprint(fp_used, learned_rule, user_id=user_id)
                    except TypeError:
                        
                        save_rule_for_fingerprint(fp_used, learned_rule)
                    auto_learned = True
                    learn_method = "structured_gpt"
                    try:
                        rule_version = str(learned_rule.get("version"))
                    except Exception:
                        rule_version = None
            except Exception:
                pass

            
            if not auto_learned:
                overrides = {"sections": []}
                headers = {int(s["header_row"]) for s in sections_zb}
                if len(headers) == 1:
                    overrides["header_row"] = int(list(headers)[0])  

                for idx, s in enumerate(sections_zb, start=1):
                    fields = {
                        "start_row": int(s["start_row"]),  
                        "end_row": int(s["end_row"]),       
                        "header_row": int(s["header_row"]), 
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
                    "overrides": overrides,
                }

                try:
                    save_rule_for_fingerprint(fp_used, rule_overrides, user_id=user_id)
                except TypeError:
                    save_rule_for_fingerprint(fp_used, rule_overrides)

                auto_learned = True
                learn_method = "overrides_fallback"
                rule_version = str(rule_overrides["version"])

            
            try:
                try:
                   
                    promoted = promote_best_candidates(user_id=user_id, fingerprint=fp_used, threshold=0.75)
                except TypeError:
                    
                    promoted = promote_best_candidates(user_id, fp_used)
            except Exception:
                promoted = False

        except Exception:
            auto_learned = False
            promoted = False
            learn_method = None

        
        try:
            memory.add_record(user_id or "anonymous", {
                "event": "confirm",
                "session_id": session_id,
                "sections_count": len(sections_zb),
                "auto_learned_rule": bool(auto_learned),
                "rule_version": rule_version,
                "learn_method": learn_method,
                "index_base": index_base,
                "timestamp": int(time.time()),
            })
        except Exception:
            pass

        return {
            "ok": True,
            "code": "CONFIRM_OK",
            "data": {
                "count": len(sections_zb),
                "sections": sections_zb,       
                "fingerprint": fp_used,
                "learn_method": learn_method,
            },
            "auto_learned_rule": auto_learned,
            "rule_version": rule_version,
            "promoted": promoted,
        }

    finally:
        setattr(data, "confirming", False)
        store.upsert(data)
