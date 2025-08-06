
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def truncate_summary_table(table_str, max_lines=5):
    lines = table_str.strip().split("\n")
    if len(lines) <= 2:
        return table_str
    header = lines[:2]
    body = [line for line in lines[2:] if "nan" not in line.lower()]
    return "\n".join(header + body[:max_lines])

def generate_report(analysis_data: dict) -> str:
    cleaned_data = {}

    for region, content in analysis_data.items():
        # ✅ Đảm bảo content là dict và có bảng
        if not isinstance(content, dict):
            continue
        if "summary_table" not in content:
            continue

        cleaned_data[region] = {
            "group_by": content.get("group_by", ""),
            "summary_table": truncate_summary_table(content.get("summary_table", "")),
            "description": content.get("description", "")
        }

    if not cleaned_data:
        return "⚠️ Không có bảng nào hợp lệ để tạo báo cáo."

    limited_data = json.dumps(cleaned_data, ensure_ascii=False, indent=2)
    if len(limited_data) > 7000:
        limited_data = limited_data[:7000] + "... (đã rút gọn)"

    prompt = f"""
Dưới đây là dữ liệu phân tích đã được trích xuất từ các bảng trong file Excel.

Nhiệm vụ của bạn:
Hãy viết một BẢN BÁO CÁO TỔNG HỢP CHUYÊN NGHIỆP BẰNG TIẾNG VIỆT, theo đúng cấu trúc bên dưới cho MỖI REGION.

Mỗi Region hãy trình bày đầy đủ 4 phần:
1. Tổng quan dữ liệu
2. Chi tiết thống kê
3. Nhận định
4. Đề xuất

KHÔNG sao chép lại JSON. KHÔNG trình bày dạng mã. KHÔNG markdown.
Viết như người làm báo cáo kỹ thuật trình bày nội bộ hoặc gửi lãnh đạo.

Dữ liệu phân tích:
=== PHÂN TÍCH BẮT ĐẦU ===
{limited_data}
=== PHÂN TÍCH KẾT THÚC ===
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Bạn là trợ lý chuyên viết báo cáo tổng hợp từ dữ liệu phân tích bảng biểu."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ Lỗi khi sinh báo cáo từ GPT: {e}"
