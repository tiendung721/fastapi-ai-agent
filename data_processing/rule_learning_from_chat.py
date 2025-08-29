# data_processing/rule_learning_from_chat.py
from typing import Dict, Any, List
import time, json, os

from data_processing.rule_memory import (
    get_rule_for_fingerprint,
    save_rule_for_fingerprint,
)

CAND_DIR = "rule_candidates"
os.makedirs(CAND_DIR, exist_ok=True)

# Ngưỡng promote (có thể tinh chỉnh)
PROMOTE_SUPPORT = 2       # số lần lặp lại tối thiểu
PROMOTE_CONF = 0.7        # độ tin cậy tối thiểu

def _cand_path(user_id: str, fp: str) -> str:
    safe_user = str(user_id).replace("/", "_")
    safe_fp = str(fp).replace("/", "_")
    return os.path.join(CAND_DIR, f"{safe_user}__{safe_fp}.json")

def load_candidates(user_id: str, fp: str) -> List[Dict[str, Any]]:
    p = _cand_path(user_id, fp)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_candidates(user_id: str, fp: str, arr: List[Dict[str, Any]]):
    with open(_cand_path(user_id, fp), "w", encoding="utf-8") as f:
        json.dump(arr, f, ensure_ascii=False, indent=2)

def upsert_candidate(user_id: str, fp: str, patch_spec: Dict[str, Any], confidence: float = 0.7):
    """
    Lưu 1 'đề xuất' học rule từ chat (chưa áp ngay).
    patch_spec dạng:
    {
      "intent": "edit_sections",
      "operations": [{ "op": "update"|"rename"|..., "selector": {...}, "fields": {...} }],
      ... (meta khác)
    }
    """
    items = load_candidates(user_id, fp)
    key = json.dumps(patch_spec, sort_keys=True, ensure_ascii=False)
    now = int(time.time())

    for it in items:
        if it.get("key") == key:
            it["support_count"] = it.get("support_count", 0) + 1
            it["confidence"] = max(it.get("confidence", 0.0), float(confidence or 0.0))
            it["last_seen"] = now
            save_candidates(user_id, fp, items)
            return

    items.append({
        "key": key,
        "patch_spec": patch_spec,
        "support_count": 1,
        "confidence": float(confidence or 0.0),
        "created_at": now,
        "last_seen": now,
        # "promoted_at": ...
    })
    save_candidates(user_id, fp, items)

def _can_promote(item: Dict[str, Any]) -> bool:
    return item.get("support_count", 0) >= PROMOTE_SUPPORT and item.get("confidence", 0.0) >= PROMOTE_CONF

def _merge_rule_simple(base_rule: Dict[str, Any], patch_spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge 'an toàn' các thay đổi phổ biến từ chat vào rule hiện có.
    - update header_row/start_row/end_row (biên nhỏ)
    - rename label
    Lưu ở dạng 'overrides' trong rule để áp sau khi autodetect (nếu bạn đã có schema rule riêng, map sang tương ứng).
    """
    if base_rule is None:
        base_rule = {}
    overrides = base_rule.get("overrides", {"header_row": None, "sections": []})

    ops = (patch_spec or {}).get("operations", [])
    for op in ops:
        name = op.get("op")
        sel = (op.get("selector") or {})
        fields = (op.get("fields") or {})
        if name == "update":
            # Ví dụ: {by:"label", value:"Dự án..."} + fields:{end_row:51}
            entry = {"selector": sel, "fields": {}}
            for k in ("header_row", "start_row", "end_row"):
                if k in fields:
                    entry["fields"][k] = int(fields[k])
            if entry["fields"]:
                overrides["sections"].append(entry)
        elif name == "rename":
            # Đổi nhãn section
            old = sel.get("value")
            new_label = fields.get("label")
            if old and new_label:
                overrides["sections"].append({
                    "selector": sel,
                    "fields": {"label": new_label}
                })

    base_rule["overrides"] = overrides
    # Tăng version đơn giản
    base_rule["version"] = int(base_rule.get("version", 0)) + 1
    base_rule["updated_at"] = int(time.time())
    return base_rule

def promote_best_candidates(user_id: str, fp: str) -> bool:
    """
    Xem các candidate đã đủ 'chín' chưa → promote vào rule.
    Trả về True nếu có thay đổi rule.
    """
    items = load_candidates(user_id, fp)
    if not items:
        return False

    base_rule = get_rule_for_fingerprint(fp, user_id=user_id) or {}
    changed = False
    now = int(time.time())

    for it in items:
        if it.get("promoted_at"):
            continue
        if _can_promote(it):
            patch_spec = it.get("patch_spec") or {}
            base_rule = _merge_rule_simple(base_rule, patch_spec)
            it["promoted_at"] = now
            changed = True

    if changed:
        save_rule_for_fingerprint(fp, base_rule, user_id=user_id)
        save_candidates(user_id, fp, items)
    return changed
