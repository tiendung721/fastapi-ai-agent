from fastapi import APIRouter, UploadFile, File, Form
import os, shutil, uuid
import pandas as pd
from data_processing.section_detector import detect_sections_auto
from data_processing.rule_memory import get_rule_for_fingerprint, get_fingerprint
from data_processing.rule_based_extractor import extract_sections_with_rule

router = APIRouter()

UPLOAD_DIR = "uploaded_files"
CACHE = {}
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/extractor-preview")
async def extractor_preview(
    file: UploadFile = File(...),
    user_id: str = Form(...)
):
    session_id = str(uuid.uuid4())
    file_ext = os.path.splitext(file.filename)[1]
    file_path = os.path.join(UPLOAD_DIR, f"{session_id}{file_ext}")
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    df = pd.read_excel(file_path)
    fingerprint = get_fingerprint(df)
    rule = get_rule_for_fingerprint(fingerprint)

    if rule:
        sections = extract_sections_with_rule(df, rule)
        used_rule = True
    else:
        sections = detect_sections_auto(df)
        used_rule = False

    CACHE[session_id] = {
        "file_path": file_path,
        "sections": sections,
        "user_confirmed": False,
        "user_id": user_id
    }

    return {
        "message": "📄 Đã xử lý file thành công.",
        "session_id": session_id,
        "user_id": user_id,
        "used_rule": used_rule,
        "sections": sections
    }
