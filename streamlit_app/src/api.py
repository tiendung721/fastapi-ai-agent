import os
import mimetypes
import httpx
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
import json as _json

load_dotenv()
BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

def _client() -> httpx.Client:
    return httpx.Client(timeout=120)

def _post(path: str, json: Dict[str, Any] | None = None, files=None, data=None, params=None) -> Dict[str, Any]:
    url = f"{BASE}{path}"
    with _client() as c:
        r = c.post(url, params=params, json=json, files=files, data=data)
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError:
            try:
                return r.json()
            except Exception:
                return {"ok": False, "code": "HTTP_ERROR", "error": r.text}
        try:
            parsed = r.json()
            if isinstance(parsed, dict):
                parsed.setdefault("ok", True)
            return parsed
        except Exception:
            return {"ok": True, "code": "NO_JSON", "data": None}

def _get(path: str) -> Dict[str, Any]:
    url = f"{BASE}{path}"
    with _client() as c:
        r = c.get(url)
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError:
            try:
                return r.json()
            except Exception:
                return {"ok": False, "code": "HTTP_ERROR", "error": r.text}
        try:
            return r.json()
        except Exception:
            return {"ok": False, "code": "BAD_JSON", "error": r.text}

def _delete(path: str) -> Dict[str, Any]:
    url = f"{BASE}{path}"
    with _client() as c:
        r = c.delete(url)
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError:
            try:
                return r.json()
            except Exception:
                return {"ok": False, "code": "HTTP_ERROR", "error": r.text}
        try:
            return r.json()
        except Exception:
            return {"ok": False, "code": "BAD_JSON", "error": r.text}



def upload_file(file, user_id: str = "default_user", sheet_name: Optional[str] = None) -> Dict[str, Any]:
    filename = getattr(file, "name", "upload.bin")
    data_bytes = file.getvalue()   # KHÔNG dùng getbuffer()
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    files = {"file": (filename, data_bytes, content_type)}
    form = {"user_id": user_id}
    if sheet_name:
        form["sheet_name"] = sheet_name
    return _post("/upload", files=files, data=form)

def preview(session_id: str, user_id: Optional[str] = None, sheet_name: Optional[str] = None) -> Dict[str, Any]:
    form: Dict[str, Any] = {"session_id": session_id, "id": session_id}
    if user_id:
        form["user_id"] = user_id
    if sheet_name:
        form["sheet_name"] = sheet_name
    return _post("/preview", data=form)

def confirm_sections(
    session_id: str,
    sections: List[Dict[str, Any]],
    user_id: Optional[str] = None,
    sheet_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Gửi xác nhận sections với các fallback để tương thích mọi BE:
      Try A: data + params đồng thời (Form + Query), sections là JSON string (Form)
      Try B: params + JSON body {"sections":[...]}
      Try C: pure JSON body (session_id, sections, user_id?, sheet_name?)
    Thành công nếu ok=True OR có message/data OR 2xx không JSON.
    """
    import json as _json
    sid = (str(session_id) if session_id is not None else "").strip()
    if not sid:
        return {"ok": False, "code": "MISSING_SESSION_ID", "error": "session_id trống ở FE"}

    
    formA: Dict[str, Any] = {
        "session_id": sid,
        "id": sid,  # alias phổ biến
        "sections": _json.dumps(sections),  # JSON string trong form
    }
    if user_id:
        formA["user_id"] = user_id
    if sheet_name:
        formA["sheet_name"] = sheet_name

    paramsA: Dict[str, Any] = {
        "session_id": sid,
        "id": sid,
    }
    if user_id:
        paramsA["user_id"] = user_id
    if sheet_name:
        paramsA["sheet_name"] = sheet_name

    rA = _post("/confirm_sections", data=formA, params=paramsA)
    if isinstance(rA, dict) and (rA.get("ok") is True or "message" in rA or "data" in rA):
        return rA

    
    rB = _post("/confirm_sections", params=paramsA, json={"sections": sections})
    if isinstance(rB, dict) and (rB.get("ok") is True or "message" in rB or "data" in rB):
        return rB

    
    bodyC: Dict[str, Any] = {"session_id": sid, "id": sid, "sections": sections}
    if user_id:
        bodyC["user_id"] = user_id
    if sheet_name:
        bodyC["sheet_name"] = sheet_name
    rC = _post("/confirm_sections", json=bodyC)
    return rC if isinstance(rC, dict) else {"ok": False, "code": "NO_VALID_RESPONSE", "error": str(rC)}


def chat(session_id: str, message: str, sheet_name: Optional[str] = None) -> Dict[str, Any]:
    sid = (str(session_id) if session_id is not None else "").strip()
    payload: Dict[str, Any] = {"session_id": sid, "message": message}
    if sheet_name:
        payload["sheet_name"] = sheet_name
    return _post("/chat", json=payload)

def run_final(session_id: str, user_id: str, sheet_name: Optional[str] = None) -> Dict[str, Any]:
    sid = (str(session_id) if session_id is not None else "").strip()
    payload: Dict[str, Any] = {"session_id": sid, "user_id": user_id}
    if sheet_name:
        payload["sheet_name"] = sheet_name
    return _post("/final", json=payload)

def get_history(user_id: str) -> Dict[str, Any]:
    return _get(f"/history/{user_id}")

def delete_history(user_id: str) -> Dict[str, Any]:
    return _delete(f"/history/{user_id}")

def health() -> Dict[str, Any]:
    return _get("/health")

def save_rule(user_id: str, sheet_name: Optional[str], sections: List[Dict[str, Any]]) -> Dict[str, Any]:
    payload = {"user_id": user_id, "sheet_name": sheet_name, "sections": sections}
    return _post("/rules/save", json=payload)


def sections_get(session_id: str) -> dict:
    with _client() as c:
        r = c.get(f"{BASE}/sessions/{session_id}/sections")
        return _json.loads(r.text)

def sections_replace(session_id: str, sections: list[dict]) -> dict:
    with _client() as c:
        r = c.put(f"{BASE}/sessions/{session_id}/sections", json={"sections": sections})
        return _json.loads(r.text)

def sections_add(session_id: str, section: dict) -> dict:
    with _client() as c:
        r = c.post(f"{BASE}/sessions/{session_id}/sections", json=section)
        return _json.loads(r.text)

def sections_delete(session_id: str, index: int) -> dict:
    with _client() as c:
        r = c.delete(f"{BASE}/sessions/{session_id}/sections/{index}")
        return _json.loads(r.text)

