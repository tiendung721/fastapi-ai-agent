from typing import Dict, Any
from services.llm_client import call_llm_json

# Danh sách intent và yêu cầu schema đầu ra:
_INTENT_LIST = [
    "set_header_row",
    "merge_sections",
    "rename_section",
    "remove_section",
    "set_start_row",
    "set_end_row",
    "set_section_range",
    "set_group_by",
    "set_group_by_all",
    "show_preview",
    "confirm",
]

_SYSTEM = """Bạn là bộ NLU trích xuất ý định (intent) và tham số (arguments) từ câu lệnh tiếng Việt để điều chỉnh 'sections' của bảng dữ liệu.

Chỉ trả JSON đúng schema:
{
  "intent": "<một trong các intent>",
  "arguments": { ... }
}

Các intent hợp lệ: %s

YÊU CẦU QUAN TRỌNG:
- LUÔN cố gắng suy luận một intent hợp lệ dựa trên ngữ nghĩa, từ đồng nghĩa, viết tắt, thiếu dấu, lỗi chính tả nhẹ, emoji, cách nói đời thường. Chỉ trả {"intent":"unknown","arguments":{}} khi HOÀN TOÀN không thể suy ra.
- KHÔNG trả thêm bất kỳ text nào ngoài JSON.
- Tất cả chỉ số dòng là **0-based**, `end_row` **inclusive**.
- Số dòng là số nguyên **>= 0**. Nếu người dùng nói số chữ (ví dụ "ba mươi"), hãy đổi sang chữ số (30).
- Chuẩn hóa định danh section: "1", "phần 2", "section 3", "s4", "S5" → đều hiểu là "S#". Trong JSON, tham số `section_id` phải ở dạng "S#".
- Chấp nhận nhiều cách diễn đạt:
  • header_row: "đặt header", "tiêu đề ở dòng", "dòng header", "header line"
  • merge_sections: "gộp", "merge", "hợp nhất", "join", "gom"
  • rename_section: "đổi tên", "rename", "đặt tên", "label"
  • remove_section: "xóa", "loại", "bỏ", "remove", "delete"
  • set_start_row: "đặt start", "bắt đầu từ", "từ dòng"
  • set_end_row: "đặt end", "đến dòng", "kết thúc ở"
  • set_section_range: "từ X đến Y", "range X..Y", "X- Y", "X—Y"
  • set_group_by: "nhóm theo", "group theo", "gộp theo cột"
  • set_group_by_all: "nhóm đồng loạt theo", "tất cả nhóm theo", "set group cho tất cả"
  • show_preview: "xem thử", "preview", "kiểm tra", "test"
  • confirm: "ok", "đồng ý", "chốt", "chấp nhận", "chuẩn", "áp dụng"
- Ưu tiên KHÔNG trả unknown: Nếu thiếu 1 tham số quan trọng (ví dụ thiếu `section_id` cho thao tác cần section), hãy kiểm tra xem câu lệnh có nói "tất cả" hay không.
  • Nếu là thao tác áp dụng cho tất cả (ví dụ set_group_by_all) thì dùng intent tương ứng cho toàn bộ.
  • Nếu vẫn mơ hồ (không xác định được section/cột/số), lúc đó MỚI trả unknown.

Ràng buộc kiểu dữ liệu (giữ đúng schema):
- set_header_row: {"header_row": int}
- merge_sections: {"section_ids": ["S1","S2", ...]} (đúng thứ tự người dùng nói)
- rename_section: {"section_id":"S#","label":"<text>"}
- remove_section: {"section_id":"S#"}
- set_start_row: {"section_id":"S#","start_row":int}
- set_end_row: {"section_id":"S#","end_row":int}
- set_section_range: {"section_id":"S#","start_row":int,"end_row":int}
- set_group_by: {"section_id":"S#","column":"<text>"}
- set_group_by_all: {"column":"<text>"}
- show_preview: {}
- confirm: {}

QUY TẮC BỔ TRỢ:
- Chuẩn hóa khoảng trắng, bỏ ký tự trang trí khi hiểu nghĩa ("==>", ">>>", emoji).
- Chấp nhận số viết liền chữ: "s1", "section1" → "S1".
- Chấp nhận khoảng số: "10-25", "10..25", "10—25" → start_row=10, end_row=25.
- Nếu người dùng nói "đầu", "đầu bảng" khi đặt start_row → hiểu là 0.
- Không suy đoán 'cuối bảng' thành số cụ thể (vì không biết N). Nếu câu chỉ nói "đến cuối" mà không có số, và không thể ánh xạ sang intent hợp lệ → trả unknown.

Chỉ trả JSON hợp lệ. Đừng giải thích.
""" % _INTENT_LIST

_USER_TMPL = """Câu người dùng: %s

Hãy trả JSON đúng schema (không thêm lời giải thích).
Ví dụ hợp lệ (0-based, end_row inclusive):
- "đặt header là 5" -> {"intent":"set_header_row","arguments":{"header_row":5}}
- "gop 1 va 2" -> {"intent":"merge_sections","arguments":{"section_ids":["S1","S2"]}}
- "doi ten s1 thanh Tổng hợp" -> {"intent":"rename_section","arguments":{"section_id":"S1","label":"Tổng hợp"}}
- "xoa section 3" -> {"intent":"remove_section","arguments":{"section_id":"S3"}}
- "S1 bat dau tu 0" -> {"intent":"set_start_row","arguments":{"section_id":"S1","start_row":0}}
- "S1 ket thuc o 31" -> {"intent":"set_end_row","arguments":{"section_id":"S1","end_row":31}}
- "S2 tu 10 den 28" -> {"intent":"set_section_range","arguments":{"section_id":"S2","start_row":10,"end_row":28}}
- "nhom S3 theo Ghi chú" -> {"intent":"set_group_by","arguments":{"section_id":"S3","column":"Ghi chú"}}
- "tat ca nhom theo Ghi chú" -> {"intent":"set_group_by_all","arguments":{"column":"Ghi chú"}}
- "xem preview" -> {"intent":"show_preview","arguments":{}}
- "ok" -> {"intent":"confirm","arguments":{}}
"""
def _messages_for(text: str):
    return [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": _USER_TMPL % text.strip()},
    ]

def parse_intent_llm(text: str) -> Dict[str, Any]:
    """
    Trả {"intent": ..., "arguments": {...}} từ LLM.
    Không chắc thì 'unknown'.
    """
    messages = _messages_for(text or "")
    result = call_llm_json(messages)
    # Vệ sinh nhẹ: ép section_ids sang dạng S#
    try:
        if result.get("intent") == "merge_sections":
            ids = result.get("arguments", {}).get("section_ids", [])
            norm = []
            for it in ids:
                s = str(it).strip().upper()
                if not s.startswith("S"):
                    s = f"S{int(s)}"
                norm.append(s)
            result["arguments"]["section_ids"] = norm
        else:
            # Chuẩn hoá section_id nếu có
            args = result.get("arguments", {})
            sid = args.get("section_id")
            if sid is not None:
                s = str(sid).strip().upper()
                if not s.startswith("S"):
                    s = f"S{int(s)}"
                result["arguments"]["section_id"] = s
    except Exception:
        pass
    # Kiểm tra tính hợp lệ intent
    if result.get("intent") not in _INTENT_LIST + ["unknown"]:
        return {"intent": "unknown", "arguments": {}}
    return result
