# analyzer_fastapi.py
import pandas as pd
import json
import os
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_region_table(df, start_row, end_row, header_row):
    header = df.iloc[header_row - 1]
    data = df.iloc[start_row - 1:end_row].copy()
    data.columns = header
    data = data.reset_index(drop=True)
    return data

def analyze_section(markdown_table: str, group_by_column: str):
    prompt = (
        f"Tôi gửi bạn bảng dữ liệu dạng markdown dưới đây.\n"
        f"Hãy phân tích bảng này theo cột **'{group_by_column}'** bằng cách:\n"
        "- Nhóm theo cột đó (`group_by`)\n"
        "- Sinh bảng tổng hợp và mô tả ngắn gọn bằng tiếng Việt\n"
        "Trả về đúng định dạng JSON, không có mô tả thêm. Ví dụ:\n"
        "{\"group_by\": \"Tên nhân viên\", \"summary_table\": \"| Tên | Số công |...\", \"description\": \"Mô tả ngắn\"}\n\n"
        f"{markdown_table}"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Bạn là AI chuyên phân tích bảng dữ liệu Excel."},
                {"role": "user", "content": prompt}
            ]
        )
        text = response.choices[0].message.content.strip().strip("`")
        if text.startswith("json"):
            text = text.replace("json", "", 1).strip()
            return json.loads(text)
        else:
            return {"error": "GPT không trả về JSON hợp lệ.", "raw": text}
    except Exception as e:
        return {"error": str(e)}

def analyze_sections_with_gpt(file_path: str, sections: list):
    if not os.path.exists(file_path):
        return {"error": "❌ Không tìm thấy file Excel."}
    
    df = pd.read_excel(file_path)
    results = {}
    
    for idx, section in enumerate(sections):
        region_id = f"Region_{idx+1}"
        try:
            region_df = extract_region_table(df, section["start_row"], section["end_row"], section["header_row"])
            if region_df.empty:
                results[region_id] = {"error": "🔍 Dữ liệu rỗng"}
                continue

            group_by = region_df.columns[0]  
            markdown = region_df.head(100).to_markdown(index=False)
            analysis = analyze_section(markdown, group_by)
            results[region_id] = analysis
        except Exception as e:
            results[region_id] = {"error": str(e)}
    
    return results
