import os
import json
from typing import Dict, List
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

def _render_group_summary_table(group_by: str, summary: Dict[str, int]) -> str:
    """
    Tạo bảng markdown từ group_summary cho phần trình bày.
    """
    if not group_by or not summary:
        return ""
    lines = [f"| {group_by} | Số lượng |", "| --- | --- |"]
    for k, v in summary.items():
        lines.append(f"| {k} | {int(v)} |")
    return "\n".join(lines)

def _compact_numeric(numeric: Dict[str, Dict[str, float]], k: int = 3) -> Dict[str, Dict[str, float]]:
    """
    Lấy gọn một vài cột numeric để gợi ý trong prompt, tránh quá dài.
    """
    out = {}
    for col in list(numeric.keys())[:k]:
        out[col] = {m: float(numeric[col].get(m, 0)) for m in ["count", "mean", "min", "median", "max"]}
    return out

def _prepare_sections_for_llm(analysis_result: Dict) -> List[Dict]:
    """
    Chuyển đổi mỗi section thành payload gọn gàng để GPT tường thuật.
    """
    payload = []
    for sec in analysis_result.get("sections", []):
        payload.append({
            "label": sec.get("label"),
            "rows": sec.get("rows"),
            "cols": sec.get("cols"),
            "group_by": sec.get("group_by"),
            "group_summary_table": _render_group_summary_table(sec.get("group_by"), sec.get("group_summary") or {}),
            "quick_notes": sec.get("quick_notes", []),
            "numeric_compact": _compact_numeric(sec.get("numeric", {}), k=3),
        })
    return payload

def build_report(analysis_result: Dict) -> str:
    """
    Tạo báo cáo tiếng Việt từ output của analyzer (phiên bản mới).
    - Không yêu cầu analyzer tạo sẵn summary_table nữa.
    - Dùng group_summary để dựng bảng đơn giản + mô tả tự nhiên nhờ GPT.
    """
    if not analysis_result or not analysis_result.get("ok"):
        return " Phân tích không hợp lệ hoặc thiếu dữ liệu."

    sections_payload = _prepare_sections_for_llm(analysis_result)
    if not sections_payload:
        return " Không có vùng (section) hợp lệ để lập báo cáo."

    # Giới hạn độ dài JSON đưa vào prompt để tránh quá tải ngữ cảnh
    limited = json.dumps(sections_payload, ensure_ascii=False)
    if len(limited) > 8000:
        limited = limited[:8000] + "... (đã rút gọn)"

    prompt = f"""
Bạn là chuyên gia lập báo cáo phân tích dữ liệu bảng. Dưới đây là các vùng dữ liệu đã được phân tích sơ bộ.

YÊU CẦU:
1) Viết báo cáo tiếng Việt, không chèn mã hay JSON.
2) Cấu trúc gồm:
   - Tổng quan (dữ liệu, số vùng, tổng số dòng)
   - Thống kê nổi bật cho từng vùng (nêu rõ group_by, kèm 1 bảng tóm tắt nếu có)
   - Nhận định (rủi ro/chất lượng dữ liệu, xu hướng)
   - Đề xuất/khuyến nghị khả thi
3) Không lặp lại JSON. Viết như báo cáo nội bộ chuyên nghiệp, rõ ràng, súc tích.

THÔNG TIN TỔNG HỢP:
- Số vùng: {analysis_result.get('sections_count')}
- Tổng số dòng: {analysis_result.get('total_rows')}

DỮ LIỆU CHI TIẾT CHO TỪNG VÙNG (đã rút gọn):
{limited}
"""

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Bạn là trợ lý chuyên viết báo cáo tổng hợp từ dữ liệu bảng biểu."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Lỗi khi sinh báo cáo từ GPT: {e}"
