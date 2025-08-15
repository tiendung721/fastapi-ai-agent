from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional, List, Dict
import os, shutil, uuid
import pandas as pd

from data_processing.section_detector import detect_sections_auto
from data_processing.rule_memory import get_rule_for_fingerprint, get_fingerprint
from data_processing.rule_based_extractor import extract_sections_with_rule
from data_processing.chat_memory import memory
import time

# Session & models & validate
from common.session_store import SessionStore
from common.models import SessionData, Section
from data_processing.validators import to_one_based, validate_sections, IndexErrorDetail

router = APIRouter()
UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

store = SessionStore()


def _read_df(file_path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
    """
    Đọc CSV/XLSX thành DataFrame. Ưu tiên sheet_name nếu là Excel.
    """
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".csv":
            return pd.read_csv(file_path)
        return pd.read_excel(file_path, sheet_name=sheet_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Không đọc được file: {e}")


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user_id: Optional[str] = Form(None)
):
    """
    Nhận file đầu vào, lưu thành /uploaded_files/{session_id}.{ext}
    và khởi tạo SessionData trong SessionStore.
    """
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".xlsx", ".xls", ".csv"]:
        raise HTTPException(status_code=400, detail="Chỉ nhận .xlsx/.xls/.csv")

    session_id = str(uuid.uuid4())
    saved_path = os.path.join(UPLOAD_DIR, f"{session_id}{ext}")

    try:
        with open(saved_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi lưu file: {e}")

    # Lưu session (kèm user_id nếu có)
    store.upsert(SessionData(session_id=session_id, user_id=user_id, file_path=saved_path))

    return {
        "ok": True,
        "code": "UPLOAD_OK",
        "data": {"session_id": session_id, "file_path": saved_path}
    }


@router.post("/preview")
async def preview(
    session_id: str = Form(...),
    sheet_name: Optional[str] = Form(None)
):
    """
    - Lấy session & đọc dữ liệu
    - Ưu tiên áp RULE (theo user_id + fingerprint). Không có rule (hoặc rule không match) thì detect auto
    - Chuẩn hóa & validate 1-based
    - Lưu auto_sections vào SessionStore
    """
    # 1) Lấy session
    data = store.get(session_id)
    if not data:
        raise HTTPException(status_code=404, detail=" Session không tồn tại")

    # 2) Đọc dữ liệu
    df = _read_df(data.file_path, sheet_name=sheet_name)
    if df.shape[0] == 0:
        raise HTTPException(status_code=400, detail="File/sheet rỗng")

    # 3) Dò sections (ưu tiên rule đã học → không có/không match thì auto)
    uid = getattr(data, "user_id", None) or "default_user"

    # Tương thích 2 phiên bản get_fingerprint (có/không có sheet_name)
    try:
        fp = get_fingerprint(df, sheet_name=sheet_name)
    except TypeError:
        fp = get_fingerprint(df)

    rule = None
    try:
        rule = get_rule_for_fingerprint(fp, user_id=uid)
    except Exception:
        # an toàn: nếu đọc rule lỗi thì coi như không có rule
        rule = None

    used_rule = False
    try:
        if rule:
            sections = extract_sections_with_rule(df, rule) or []
            if len(sections) > 0:
                used_rule = True
            else:
                # 🔁 FALLBACK: rule không cho section nào → quay về auto
                sections = detect_sections_auto(df)
        else:
            sections = detect_sections_auto(df)
    except Exception:
        # Nếu extractor phát sinh lỗi → fallback auto
        sections = detect_sections_auto(df)

    # 4) CHUẨN HÓA + VALIDATE 1-based
    try:
        sections = to_one_based(sections, nrows=df.shape[0])
        sections = validate_sections(sections, nrows=df.shape[0])
    except IndexErrorDetail as ie:
        # Trả mã lỗi & thông tin chi tiết index
        return {"ok": False, "code": ie.code, "error": str(ie)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Sections không hợp lệ: {e}")

    # 5) LƯU auto_sections vào session (Pydantic → ràng buộc chặt)
    data.auto_sections = [Section(**s) for s in sections]
    # Ghi lại user_id (nếu trước đó null) để lần sau tra đúng kho rule theo user
    if not getattr(data, "user_id", None):
        try:
            data.user_id = uid
        except Exception:
            pass
    store.upsert(data)

    memory.add_record(uid or "anonymous", {
        "event": "preview",
        "session_id": session_id,
        "used_rule": bool(used_rule),
        "sections_count": len(sections),
        "nrows": int(df.shape[0]),
        "timestamp": int(time.time())
    })


    # 6) Trả về: luôn kèm nrows + used_rule để client dễ debug
    return {
        "ok": True,
        "code": "PREVIEW_OK",
        "data": {
            "auto_sections": sections,
            "nrows": int(df.shape[0]),
            "used_rule": used_rule
        }
    }
