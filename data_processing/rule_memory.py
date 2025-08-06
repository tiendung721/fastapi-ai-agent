import os
import json
import hashlib

RULE_DIR = "rule_memory"
os.makedirs(RULE_DIR, exist_ok=True)

def get_fingerprint(df):
    # Bạn có thể nâng cấp fingerprint theo header fingerprint hoặc thống kê vùng dữ liệu
    headers = [str(col).strip().lower() for col in df.columns]
    fingerprint = hashlib.md5("".join(headers).encode()).hexdigest()
    return fingerprint

def _get_rule_file_path(fingerprint, user_id="default_user"):
    return os.path.join(RULE_DIR, f"{user_id}_{fingerprint}.json")

def save_rule_for_fingerprint(fingerprint, rule, user_id="default_user"):
    file_path = _get_rule_file_path(fingerprint, user_id)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(rule, f, indent=2, ensure_ascii=False)

def get_rule_for_fingerprint(fingerprint, user_id="default_user"):
    file_path = _get_rule_file_path(fingerprint, user_id)
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None
