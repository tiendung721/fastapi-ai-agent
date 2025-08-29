# services/rule_synthesizer.py
from typing import Dict, Any


# NGUYÊN TẮC đơn giản giai đoạn này:
# - Rule = snapshot của preview cuối cùng sau khi user đã chỉnh qua chat
# - Có thể cộng thêm metadata từ events nếu cần


def synthesize_rule(final_preview: Dict[str, Any], events: list[dict] | None = None) -> Dict[str, Any]:
    rule = {
        "header_row": final_preview.get("header_row", 0),
        "sections": final_preview.get("sections", []),
        "notes": {
            "learned_from_chat": True,
            "events_count": len(events or [])
        }
    }
    return rule