from fastapi import FastAPI
from controllers.extractor_controller import router as extractor_router
from controllers.pipeline_controller import router as pipeline_router
from controllers.history_controller import router as history_router

app = FastAPI(
    title="AI Agent FastAPI - Control/Data Plane",
    description="Trích xuất - Phân tích - Báo cáo từ file Excel bằng GPT",
    version="2.0"
)

# Đăng ký router
app.include_router(extractor_router, prefix="")
app.include_router(pipeline_router, prefix="")
app.include_router(history_router, prefix="")
