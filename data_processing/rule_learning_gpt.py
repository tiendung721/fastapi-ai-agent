import json
import os
from typing import List, Dict, Any, Optional
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI, BadRequestError
from pydantic import ValidationError

from common.retry import with_backoff
from .rule_schema import LearnedRule

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

SYSTEM_PROMPT = """Bạn là công cụ trích xuất RULE chia section từ bảng Excel sau khi OCR.
Trả về JSON đúng schema:
{
  "label": str,
  "start_keywords": [str, ...],
  "end_keywords": [str, ...],
  "header_row": int
}
- Không trả lời thêm chữ nào ngoài JSON.
- Chọn header_row là dòng tiêu đề cột (1-based).
- start_keywords là cụm mở đầu vùng dữ liệu; end_keywords đánh dấu kết thúc.

YÊU CẦU QUAN TRỌNG:
- ƯU TIÊN dùng CỤM TỪ XUẤT HIỆN NGUYÊN VĂN trong bảng (tiêu đề, nhãn) làm start_keywords/end_keywords.
- Nếu không chắc ranh giới kết thúc, cho phép tiêu chí kết thúc là: dòng trống hoặc khối kế tiếp đổi header.
- Rule phải đủ tổng quát để áp cho file tương tự, nhưng KHÔNG được mơ hồ.
"""

def _extract_json_str(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("Không tìm thấy JSON hợp lệ trong phản hồi.")
    return text[start:end+1]

def _call_openai_json(user_prompt: str) -> str:
    """
    Trả về chuỗi JSON từ OpenAI.
    1) Thử Responses API + response_format.
    2) Nếu lỗi TypeError hoặc BadRequestError → fallback sang Chat Completions + response_format.
    3) Nếu vẫn lỗi → fallback cuối: Chat Completions không response_format nhưng ép prompt 'ONLY JSON'.
    """
    # 1) Responses API
    try:
        resp = client.responses.create(
            model=MODEL,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        return resp.output_text
    except TypeError:
        # SDK cũ không hỗ trợ response_format ở Responses API
        pass
    except BadRequestError:
        # Model không hỗ trợ JSON mode ở Responses API
        pass

    # 2) Chat Completions + response_format
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        return resp.choices[0].message.content
    except BadRequestError:
        pass

    # 3) Fallback cuối: không dùng JSON mode, ép prompt 'ONLY JSON'
    strict_prompt = user_prompt + "\n\nHãy trả lời CHỈ một JSON hợp lệ, không kèm giải thích."
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT + "\nChỉ trả về JSON hợp lệ."},
            {"role": "user", "content": strict_prompt}
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content

def learn_rule(prompt: str) -> dict:
    """
    Gọi OpenAI để sinh rule và parse về dict theo schema LearnedRule.
    """
    raw = with_backoff(lambda: _call_openai_json(prompt))
    try:
        data = LearnedRule.model_validate_json(raw)
        return data.model_dump()
    except ValidationError:
        js = json.loads(_extract_json_str(raw))
        data = LearnedRule(**js)
        return data.model_dump()

def _read_df(file_path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
    ext = (file_path or "").lower().split(".")[-1]
    if ext == "csv":
        return pd.read_csv(file_path)
    return pd.read_excel(file_path, sheet_name=sheet_name)

def _sample_table_context(df: pd.DataFrame, head_rows: int = 20, tail_rows: int = 20) -> str:
    head = df.head(head_rows).to_csv(index=False)
    tail = df.tail(tail_rows).to_csv(index=False)
    headers = [str(c) for c in df.columns]
    return (
        f"HEAD ({head_rows}):\n{head}\n\n"
        f"TAIL ({tail_rows}):\n{tail}\n\n"
        f"COLUMNS: {headers}\n"
    )

def _sections_hint(sections: List[Dict[str, Any]]) -> str:
    lines = []
    for s in sections:
        sr = s.get("start_row")
        er = s.get("end_row")
        hr = s.get("header_row")
        lb = s.get("label", "")
        lines.append(f"- label='{lb}', header_row={hr}, region=({sr}..{er}) [1-based]")
    return "\n".join(lines)

def learn_rule_from_sections(
    file_path: str,
    sections: List[Dict[str, Any]],
    sheet_name: Optional[str] = None,
    head_rows: int = 20,
    tail_rows: int = 20
) -> Dict[str, Any]:
    """
    Học rule dựa trên sections (đã confirm hoặc auto).
    - Đọc bảng, trích head/tail và headers làm ngữ cảnh.
    - Đưa gợi ý về vùng (header_row, start_row, end_row, label) vào prompt.
    - Gọi LLM để sinh rule tuân thủ schema LearnedRule.
    """
    df = _read_df(file_path, sheet_name=sheet_name)
    context = _sample_table_context(df, head_rows=head_rows, tail_rows=tail_rows)
    hint = _sections_hint(sections)

    user_prompt = f"""
Dưới đây là ngữ cảnh bảng và gợi ý các vùng section đã biết. Hãy suy luận rule tổng quát để có thể áp dụng cho các file tương tự.
YÊU CẦU:
- Trả về JSON theo schema đã nêu trong system prompt (không thêm text khác).
- Giá trị header_row là 1-based.
- Không suy diễn ngoài phạm vi dữ liệu; nếu không chắc chắn, chọn rule an toàn (ít false positive).

[CONTEXT]
{context}

[SECTIONS_HINT]
{hint}
""".strip()

    rule = learn_rule(user_prompt)
    if not isinstance(rule.get("header_row"), int) or rule["header_row"] <= 0:
        hr_list = [s.get("header_row") for s in sections if isinstance(s.get("header_row"), int)]
        rule["header_row"] = hr_list[0] if hr_list else 1
    return rule
