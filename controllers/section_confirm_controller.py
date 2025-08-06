from fastapi import APIRouter
from pydantic import BaseModel
import pandas as pd
from data_processing.rule_learning_gpt import learn_rule_from_user_sections
from data_processing.rule_memory import save_rule_for_fingerprint, get_fingerprint
from controllers.extractor_controller import CACHE

router = APIRouter()

class ConfirmSectionRequest(BaseModel):
    session_id: str
    sections: list

@router.post("/confirm-section")
async def confirm_section(data: ConfirmSectionRequest):
    session_id = data.session_id
    sections = data.sections

    if session_id not in CACHE:
        return {"error": "❌ Session ID không tồn tại."}

    file_path = CACHE[session_id]["file_path"]
    df = pd.read_excel(file_path)
    user_id = CACHE[session_id]["user_id"]

    try:
        rule = learn_rule_from_user_sections(df, sections)
        fingerprint = get_fingerprint(df)
        save_rule_for_fingerprint(fingerprint, rule, user_id=user_id)

        CACHE[session_id]["sections"] = sections
        CACHE[session_id]["user_confirmed"] = True

        return {
            "message": "✅ Rule đã được học và xác nhận.",
            "applied_rule": rule,
            "updated_sections": sections
        }
    except Exception as e:
        return {"error": f"❌ Lỗi khi học rule: {str(e)}"}
