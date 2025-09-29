# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from common.session_store import SessionStore
from data_processing.validators import validate_sections_zero_based, IndexErrorDetail

router = APIRouter()
store = SessionStore()

class Section(BaseModel):
    start_row: int
    end_row: int
    header_row: int
    label: Optional[str] = ""

class SectionsPayload(BaseModel):
    sections: List[Section]

def _get_working_sections(data) -> List[Dict[str, Any]]:
   
    secs = getattr(data, "confirmed_sections", None) or getattr(data, "auto_sections", None) or []
    return [dict(x) for x in secs]

@router.get("/sessions/{session_id}/sections")
def get_sections(session_id: str):
    data = store.get(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Session không tồn tại")
    return {"ok": True, "data": {"sections": _get_working_sections(data)}}

@router.put("/sessions/{session_id}/sections")
def replace_sections(session_id: str, payload: SectionsPayload):
    data = store.get(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Session không tồn tại")
    try:
        validate_sections_zero_based([s.dict() for s in payload.sections], nrows=10**9)
    except IndexErrorDetail as e:
        raise HTTPException(status_code=400, detail={"code": e.code, "message": str(e)})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    data.confirmed_sections = [s.dict() for s in payload.sections]
    store.upsert(data)
    return {"ok": True, "data": {"sections": data.confirmed_sections}}

@router.post("/sessions/{session_id}/sections")
def add_section(session_id: str, section: Section):
    data = store.get(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Session không tồn tại")
    working = _get_working_sections(data)
    working.append(section.dict())
    try:
        validate_sections_zero_based(working, nrows=10**9)
    except IndexErrorDetail as e:
        raise HTTPException(status_code=400, detail={"code": e.code, "message": str(e)})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    data.confirmed_sections = working
    store.upsert(data)
    return {"ok": True, "data": {"sections": working}}

@router.delete("/sessions/{session_id}/sections/{index}")
def delete_section(session_id: str, index: int):
    data = store.get(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Session không tồn tại")
    working = _get_working_sections(data)
    if not (0 <= index < len(working)):
        raise HTTPException(status_code=404, detail="index out of range")
    del working[index]
    try:
        validate_sections_zero_based(working, nrows=10**9)
    except IndexErrorDetail as e:
        raise HTTPException(status_code=400, detail={"code": e.code, "message": str(e)})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    data.confirmed_sections = working
    store.upsert(data)
    return {"ok": True, "data": {"sections": working}}
