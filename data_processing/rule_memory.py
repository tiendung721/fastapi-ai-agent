import os
import json
import hashlib
from typing import Optional
import re

RULE_DIR = "rule_memory"
os.makedirs(RULE_DIR, exist_ok=True)


def get_fingerprint(df, sheet_name: Optional[str] = None) -> str:
    """
    Tạo fingerprint dựa trên:
    - Danh sách headers (lower + strip)
    - (Tùy chọn) sheet_name để phân biệt rule theo sheet
    """
    headers = [str(col).strip().lower() for col in df.columns]
    base_str = "|".join(headers)
    if sheet_name:
        base_str = f"{sheet_name.strip().lower()}||{base_str}"
    return hashlib.md5(base_str.encode()).hexdigest()


def _safe_user_id(user_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", user_id or "default_user")


def _get_rule_file_path(fingerprint: str, user_id: str = "default_user") -> str:
    safe_uid = _safe_user_id(user_id)
    return os.path.join(RULE_DIR, f"{safe_uid}_{fingerprint}.json")


def save_rule_for_fingerprint(fingerprint: str, rule: dict, user_id: str = "default_user") -> None:
    file_path = _get_rule_file_path(fingerprint, user_id)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(rule, f, indent=2, ensure_ascii=False)
    except Exception as e:
        raise RuntimeError(f"Lỗi lưu rule: {e}")


def get_rule_for_fingerprint(fingerprint: str, user_id: str = "default_user") -> Optional[dict]:
    file_path = _get_rule_file_path(fingerprint, user_id)
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] Không đọc được rule {file_path}: {e}")
        return None
