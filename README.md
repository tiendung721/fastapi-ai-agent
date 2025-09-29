# Agent_FastAPI

> **AI Excel Agent + FastAPI/Streamlit** — Tự động phát hiện & chia *section* trong Excel/CSV, có cổng API và UI để xem trước, chỉnh sửa và xác nhận.  

---

## 1) Tổng quan

Dự án này hiện thực một **Excel Agent** có khả năng:
- Phát hiện các **khối/section** trong file Excel/CSV bằng heuristic Python.
- **Gate anomaly** để tự động gọi LLM trong các ca khó (tùy chọn).
- Cung cấp **API FastAPI** cho BE (upload, preview, confirm, history…).
- Cung cấp **UI Streamlit** cho FE (upload → preview/chỉnh sửa → run final → history).



---

## 2) Cấu trúc thư mục (rút gọn)

```
Agent_FastAPI/
├── .env
├── .gitignore
├── common/
│   ├── models.py
│   ├── retry.py
│   └── session_store.py
├── controllers/
│   ├── chat_controller.py
│   ├── extractor_controller.py
│   ├── history_controller.py
│   ├── pipeline_controller.py
│   ├── rules_controller.py
│   ├── section_confirm_controller.py
│   └── sections_controller.py
├── data/
│   ├── 2025_Báo_cáo_công việc.xlsx
│   ├── dat_hang.xlsx
│   ├── data_test.xlsx
│   └── san_luong.xlsx
├── data_processing/
│   ├── analyzer.py
│   ├── auto_group_by.py
│   ├── chat_memory.py
│   ├── exporter.py
│   ├── planner.py
│   ├── rule_based_extractor.py
│   ├── rule_learning_from_chat.py
│   ├── rule_learning_gpt.py
│   ├── rule_memory.py
│   ├── rule_schema.py
│   ├── section_detector.py
│   └── validators.py
├── main.py
├── output/
├── rule_candidates/
├── rule_memory/
├── services/
│   ├── intent_llm.py
│   ├── llm_client.py
│   ├── memory_store.py
│   ├── preview_ops.py
│   └── rule_synthesizer.py
├── session_store.sqlite3
├── streamlit_app/
│   ├── .env
│   ├── app.py
│   ├── requirements.txt
│   └── src/
│       ├── api.py
│       ├── state.py
│       ├── ui.py
│       └── utils.py
├── uploaded_files/
└── user_history.json
```
---

## 3) Các thành phần chính

- **FastAPI backend**: các module có import `fastapi` và định nghĩa `app = FastAPI(...)`.
- **Streamlit UI**: file có `import streamlit as st` như:
  - streamlit_app/app.py
  - streamlit_app/src/state.py
  - streamlit_app/src/ui.py


---

## 4) API (FastAPI) — Route đã phát hiện

| Method | Path | File | Handler |
|---|---|---|---|
| DELETE | `/history/{user_id}` | `controllers/history_controller.py` | `clear_history` |
| DELETE | `/sessions/{session_id}/sections/{index}` | `controllers/sections_controller.py` | `delete_section` |
| GET | `/` | `main.py` | `index` |
| GET | `/health` | `main.py` | `health` |
| GET | `/history/{user_id}` | `controllers/history_controller.py` | `get_history` |
| GET | `/rules/get` | `controllers/rules_controller.py` | `rules_get` |
| GET | `/sessions/{session_id}/sections` | `controllers/sections_controller.py` | `get_sections` |
| POST | `/chat` | `controllers/chat_controller.py` | `chat` |
| POST | `/confirm_sections` | `controllers/section_confirm_controller.py` | `confirm_sections` |
| POST | `/final` | `controllers/pipeline_controller.py` | `run_final` |
| POST | `/preview` | `controllers/extractor_controller.py` | `preview` |
| POST | `/rules/save` | `controllers/rules_controller.py` | `rules_save` |
| POST | `/sessions/{session_id}/sections` | `controllers/sections_controller.py` | `add_section` |
| POST | `/upload` | `controllers/extractor_controller.py` | `upload_file` |
| PUT | `/sessions/{session_id}/sections` | `controllers/sections_controller.py` | `replace_sections` |

> ⚠️ Trình quét regex có thể bỏ sót các route gắn vào `APIRouter()` hoặc các file import động. Vui lòng bổ sung bằng tay nếu thiếu.

---


Gợi ý file `.env.example`:
```
# Backend
OPENAI_API_KEY=
BF_TOKEN=
LOG_LEVEL=INFO
# ... thêm các biến bạn dùng
```

---

## 5) Cài đặt

### 5.1 Yêu cầu
- Python 3.10+ (khuyến nghị 3.10/3.11)
- pip / venv
- (Tùy chọn) Visual Studio Build Tools trên Windows nếu build native packages
- (Tùy chọn) CUDA/cuDNN nếu dùng tăng tốc GPU

### 5.2 Tạo môi trường & cài dependency

```bash
# Tạo venv
python -m venv .venv
# Kích hoạt
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

# Cài đặt các gói
pip install --upgrade pip wheel setuptools
pip install -r requirements.txt
```

---

## 6) Chạy nhanh (Quickstart)

### 6.1 Chạy Backend (FastAPI)
```bash
# Ví dụ uvicorn – cập nhật đường dẫn module:app tương ứng trong repo của bạn
uvicorn app.serve:app --host 0.0.0.0 --port 8000 --reload
```
- Mặc định API docs tại: `http://localhost:8000/docs` (Swagger).

### 6.2 Chạy UI (Streamlit)
```bash
# Cập nhật đường dẫn file UI nếu khác
streamlit run streamlit_app/app.py
```

### 6.3 Quy trình sử dụng
1. **Upload** file `.xlsx/.xls/.csv` ở UI.
2. **Preview & Adjust**: xem/điều chỉnh các section đã phát hiện.
3. **Chat/LLM Assist**: LLM có thể được gọi khi điểm anomaly vượt ngưỡng.
4. **Run Final**: xác nhận và gửi về BE.
5. **History**: xem lại các phiên làm việc.

---

## 7) Hướng dẫn tích hợp LLM (tùy chọn)

- Đặt `OPENAI_API_KEY` trong `.env` để bật gọi LLM khi `anomaly_score` vượt ngưỡng.
- Có thể cấu hình ngưỡng `--anomaly` trong CLI (nếu script hỗ trợ) hoặc trong config BE.

---


## 8) Roadmap gợi ý

- [ ] Trích xuất schema section ổn định hơn (xử lý header hợp nhất, merged cells).
- [ ] Bộ test unit cho các case Excel khó.
- [ ] Endpoint xác nhận section trả về JSON chuẩn + lưu lịch sử.
- [ ] Xử lý dữ liệu group_by đa dạng hơn.
- [ ] Cải thiện chất lượng kết quả dữ liệu output.

---

