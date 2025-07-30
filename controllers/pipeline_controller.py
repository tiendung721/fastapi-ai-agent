from fastapi import APIRouter, Form
from data_processing.analyzer import analyze_sections_with_gpt
from data_processing.planner import generate_report
from data_processing.exporter import save_report_excel
from data_processing.chat_memory import memory

router = APIRouter()
from controllers.extractor_controller import CACHE

@router.post("/run-final")
async def run_full_pipeline(session_id: str = Form(...)):
    data = CACHE.get(session_id)
    if not data:
        return {"error": "Session ID không tồn tại hoặc chưa xác nhận."}

    file_path = data["file_path"]
    sections = data["sections"]
    user_id = data["user_id"]

    analysis = analyze_sections_with_gpt(file_path, sections)
    report = generate_report(analysis)
    excel_path = save_report_excel(user_id, report)

    memory.add_record(user_id, {
        "file": file_path.split("/")[-1],
        "sections": sections,
        "analysis": analysis,
        "report": report,
        "report_file": excel_path.split("/")[-1]
    })

    return {
        "session_id": session_id,
        "sections": sections,
        "analysis": analysis,
        "report": report,
        "report_file": excel_path.split("/")[-1]
    }
