# extractor_controller.py
from fastapi import APIRouter, UploadFile, File, Form
import pandas as pd
import os, shutil, uuid

from data_processing.extractor import extract_rule_with_gpt
from data_processing.rule_based_extractor import (
    get_header_fingerprint, find_rule, save_rule, extract_sections_by_rule
)

router = APIRouter()
UPLOAD_DIR = "uploads"
CACHE = {}
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/extractor-preview")
async def extractor_preview(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    feedback: str = Form("")  # Góp ý người dùng (optional)
):
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    df = pd.read_excel(file_path).dropna(how="all")
    headers = df.columns.tolist()
    fingerprint = get_header_fingerprint(headers)

    rule = find_rule(headers)
    if not rule:
        # GPT học rule từ file + góp ý
        rule = extract_rule_with_gpt(file_path, feedback)
        save_rule(headers, rule)

    sections = extract_sections_by_rule(df, rule)

    CACHE[file_id] = {
        "user_id": user_id,
        "file_path": file_path,
        "headers": headers,
        "fingerprint": fingerprint,
        "sections": sections,
        "source": "rule"
    }
    return {"session_id": file_id, "sections": sections, "source": "rule"}
