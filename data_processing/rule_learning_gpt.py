import os
from openai import OpenAI
import json
import pandas as pd

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def learn_rule_with_gpt(section_text: str) -> dict:
    prompt = f"""
Bạn là một AI giúp sinh rule để trích xuất bảng từ file Excel.

Dưới đây là một bảng dữ liệu người dùng đã xác nhận là hợp lệ:
--------------------------
{section_text}
--------------------------

Hãy phân tích và trả về rule dưới dạng JSON với format:

{{
  "start_keywords": [...],
  "end_keywords": [...],
  "header_includes": [...],
  "label_keywords": {{
    "chứa 'xxx'": "Tên bảng"
  }}
}}

Chỉ trả về JSON hợp lệ, không thêm lời giải thích.
"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Bạn là một AI chuyên giúp trích xuất rule từ bảng dữ liệu Excel."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    content = response.choices[0].message.content
    try:
        return json.loads(content)
    except:
        raise ValueError(f"❌ GPT trả về nội dung không hợp lệ:\n\n{content}")

def learn_rule_from_user_sections(df, sections):
    all_text = []
    for s in sections:
        try:
            region = df.iloc[s["start_row"]:s["end_row"] + 1]
            text = region.to_csv(index=False)
            all_text.append(text)
        except Exception as e:
            print(f"Lỗi khi xử lý section {s}: {e}")

    combined_text = "\n\n".join(all_text)
    return learn_rule_with_gpt(combined_text)