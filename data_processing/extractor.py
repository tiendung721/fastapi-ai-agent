# extractor.py
import os
import json
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def read_excel_as_markdown(file_path):
    df = pd.read_excel(file_path)
    df = df.dropna(how='all')
    if len(df) > 100:
        df = df.head(100)
    return df.to_markdown(index=False), df.columns.tolist()

def extract_rule_with_gpt(file_path: str, user_feedback: str = ""):
    markdown_table, headers = read_excel_as_markdown(file_path)
    prompt = f"""
Tôi gửi bạn bảng dữ liệu Excel dưới dạng markdown:

{markdown_table}

Người dùng góp ý: {user_feedback}

🎯 Hãy phân tích bảng và rút ra quy tắc nhận biết các vùng dữ liệu (sections).
✅ Trả về 1 JSON object có dạng:
{{
  "start_keywords": ["..."],
  "end_keywords": ["..."],
  "label_keywords": {{
    "chứa '...'" : "tên nhãn"
  }}
}}

⚠️ Không chia bảng trực tiếp. Chỉ suy luận quy tắc. Không thêm mô tả hay markdown.
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Bạn là AI chuyên học quy tắc từ bảng dữ liệu Excel."},
            {"role": "user", "content": prompt}
        ]
    )
    text = response.choices[0].message.content.strip().strip("` \n")
    if text.startswith("json"):
        text = text.replace("json", "", 1).strip()
    return json.loads(text)
