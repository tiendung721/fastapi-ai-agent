# controllers/rules_controller.py
from fastapi import APIRouter, Body, Query
from pydantic import BaseModel
from typing import List, Dict, Optional
import os, json

router = APIRouter()

RULES_PATH = os.getenv("RULES_PATH", os.path.join(os.getenv("OUTPUT_DIR", "output"), "rules.json"))
os.makedirs(os.path.dirname(RULES_PATH), exist_ok=True)

def _load_rules() -> Dict[str, Dict]:
    if os.path.exists(RULES_PATH):
        try:
            with open(RULES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_rules(obj: Dict[str, Dict]) -> None:
    with open(RULES_PATH, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def _key(user_id: str, sheet_name: Optional[str]) -> str:
    return f"{user_id}::{sheet_name or ''}"

class Section(BaseModel):
    header_row: int
    start_row: int
    end_row: int
    label: Optional[str] = ""

class SaveRuleIn(BaseModel):
    user_id: str
    sheet_name: Optional[str] = None
    sections: List[Section]

@router.post("/rules/save")
def rules_save(payload: SaveRuleIn):
    rules = _load_rules()
    rules[_key(payload.user_id, payload.sheet_name)] = {
        "sections": [s.dict() for s in payload.sections]
    }
    _save_rules(rules)
    return {"ok": True, "code": "RULE_SAVED"}

@router.get("/rules/get")
def rules_get(user_id: str = Query(...), sheet_name: Optional[str] = Query(None)):
    rules = _load_rules()
    rule = rules.get(_key(user_id, sheet_name))
    return {"ok": True, "data": rule or {}}
