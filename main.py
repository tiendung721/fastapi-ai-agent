# main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import os

# ⬇ import các router (đổi tên module cho khớp dự án của bạn)
from controllers.extractor_controller import router as extractor_router
from controllers.section_confirm_controller import router as confirm_router
from controllers.chat_controller import router as chat_router
from controllers.pipeline_controller import router as pipeline_router  # chứa /final (đã gộp)
from controllers.rules_controller import router as rules_router

# (Tùy chọn) Nếu bạn có file history_controller.py với /history/{user_id}
try:
    from controllers.history_controller import router as history_router
except Exception:
    history_router = None

APP_NAME = "AI Agent Backend"
APP_DESC = "API cho phép người dùng tương tác với AI Agent để xử lý dữ liệu, xác nhận sections và xuất báo cáo."
APP_VER = "2.0.0"

app = FastAPI(title=APP_NAME, description=APP_DESC, version=APP_VER)

# 1) CORS cho frontend
# - FE cũ (Vite): 5173
# - FE mới (Streamlit): 8501
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8501",
    "http://127.0.0.1:8501",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):(5173|8501)",
    allow_credentials=True,
    allow_methods=["*"],   # gồm cả OPTIONS
    allow_headers=["*"],
)

# 2) Static files (xuất báo cáo Excel/PDF để FE tải)
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=OUTPUT_DIR), name="static")

# 3) Healthcheck đơn giản
@app.get("/health")
def health():
    return {"ok": True, "service": APP_NAME, "version": APP_VER}

# 4) Chuẩn hóa lỗi không mong muốn (fallback)
@app.exception_handler(Exception)
async def unhandled_exc_handler(request: Request, exc: Exception):
    # Không lộ chi tiết nội bộ; FE chỉ cần biết "lỗi chung"
    return JSONResponse(
        status_code=500,
        content={"ok": False, "code": "UNHANDLED_ERROR", "error": str(exc)},
    )

# 5) Đăng ký router
#    - extractor: /upload, /preview, /session/{id} (nếu có)
#    - confirm:   /confirm_sections
#    - chat:      /chat
#    - pipeline:  /final  (đã gộp)
#    - history:   /history/{user_id} (nếu có)
app.include_router(extractor_router, prefix="", tags=["extractor"])
app.include_router(rules_router, prefix="", tags=["rules"])
app.include_router(chat_router,      prefix="", tags=["chat"])
app.include_router(confirm_router,   prefix="", tags=["confirm"])
app.include_router(pipeline_router,  prefix="", tags=["final"])

if history_router is not None:
    app.include_router(history_router, prefix="", tags=["history"])

# 6) Trang chủ gợi ý
@app.get("/")
def index():
    endpoints = ["/upload", "/preview", "/chat", "/confirm_sections", "/final", "/health", "/static/<file>"]
    if history_router is not None:
        endpoints.extend(["/history/{user_id} (GET)", "/history/{user_id} (DELETE)"])
    return {
        "ok": True,
        "message": "AI Agent Backend is running.",
        "endpoints": endpoints
    }
