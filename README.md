# Agent_FastAPI — Streamlit


## Cấu trúc thư mục (rút gọn)
```
agent_proj/
└── Agent_FastAPI
    ├── common
    │   ├── models.py
    │   ├── retry.py
    │   └── session_store.py
    ├── controllers
    │   ├── chat_controller.py
    │   ├── extractor_controller.py
    │   ├── history_controller.py
    │   ├── pipeline_controller.py
    │   ├── rules_controller.py
    │   └── section_confirm_controller.py
    ├── data
    │   ├── 2025_Báo_cáo_công việc.xlsx
    │   └── data_test.xlsx
    ├── data_processing
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
    ├── output
    ├── rule_candidates
    ├── rule_memory
    ├── services
    │   ├── intent_llm.py
    │   ├── llm_client.py
    │   ├── memory_store.py
    │   ├── preview_ops.py
    │   └── rule_synthesizer.py
    ├── streamlit_app
    │   ├── src
    │   │   ├── api.py
    │   │   ├── state.py
    │   │   ├── ui.py
    │   │   └── utils.py
    │   ├── .env
    │   ├── app.py
    │   └── requirements.txt
    ├── uploaded_files
    ├── .env
    ├── .gitignore
    ├── main.py
    ├── session_store.sqlite3
    └── user_history.json
```

## Thành phần chính

- **Frontend**: Ứng dụng Streamlit.  
- **Backend**: Ứng dụng FastAPI với các controller.  
- **Logic cốt lõi**: thư mục `data_processing/`, `services/`, `common/`.  


## Các Endpoint FastAPI (quét được)

- **POST** `/chat`  —  trong `controllers/chat_controller.py`
- **POST** `/upload`  —  trong `controllers/extractor_controller.py`
- **POST** `/preview`  —  trong `controllers/extractor_controller.py`
- **GET** `/history/{user_id}`  —  trong `controllers/history_controller.py`
- **DELETE** `/history/{user_id}`  —  trong `controllers/history_controller.py`
- **POST** `/final`  —  trong `controllers/pipeline_controller.py`
- **POST** `/rules/save`  —  trong `controllers/rules_controller.py`
- **GET** `/rules/get`  —  trong `controllers/rules_controller.py`
- **POST** `/confirm_sections`  —  trong `controllers/section_confirm_controller.py`
- **GET** `/health`  —  trong `main.py`
- **GET** `/`  —  trong `main.py`

## Sơ đồ Pipeline
```
Người dùng (Streamlit UI)
    │
    │ 1) Upload file / cấu hình
    ▼
Frontend (Streamlit) → gọi FastAPI endpoints:
    - /upload → trả về session_id
    - /preview → phân loại section (rule/GPT)
    - /confirm → người dùng xác nhận/chỉnh sửa section → học rule
    - /final → chạy analyzer → planner → trả về file/tóm tắt
    │
    ▼
Backend (FastAPI, controllers/*):
    - SessionStore quản lý trạng thái từng session
    - data_processing/* modules:
        * extractor (theo rule + GPT hỗ trợ)
        * analyzer (tính toán thống kê, group_by)
        * planner (tạo file Excel/tóm tắt)
        * rule_memory (lưu fingerprint & rule theo user_id)
        * chat_memory & intent_llm (học từ hội thoại)
    │
    ▼
Kết quả:
    - /outputs/<session_id>/... (xlsx, json, logs)
```

### Luồng xử lý chi tiết
1. **Upload** (Streamlit → FastAPI `/upload`): lưu file, tạo `session_id`, ghi nhận `user_id`.
2. **Preview** (Streamlit → `/preview`): đọc Excel/CSV; chạy **bộ phân loại section** (ưu tiên rule-based, fallback GPT); trả về danh sách section (0-based) gồm `header_row`, `start_row`, `end_row`, `label`.
3. **Confirm** (Streamlit → `/confirm`): người dùng chỉnh sửa section; hệ thống xác thực (`validators.py`), lưu vào `SessionStore`, **học rule** từ section (`rule_learning_gpt.py`), và **lưu rule theo fingerprint** (`rule_memory.py`).
4. **Final** (Streamlit → `/final`): chạy **extractor** với rule đã học → sinh JSON chuẩn; chạy **analyzer** để tính toán; sau đó **planner** tạo báo cáo Excel/tóm tắt; trả về file và summary.
5. **Chat Learning (tùy chọn)**: `/chat` phân tích intent (`services/intent_llm.py`), ghi nhận candidate (`rule_learning_from_chat.py`), và có thể **thăng hạng rule**.

## Frontend — Streamlit
- Ứng dụng tại thư mục `streamlit_app/`.
- Thành phần giao diện:
  - Upload file (Excel/CSV).
  - Nút: **Preview**, **Confirm**, **Run Final**.
  - Lưu `session_id`, `user_id`, danh sách section vào session state.
- Gọi FastAPI bằng `httpx` với API_BASE từ file `.env`.
- Hiển thị bảng, JSON section, link tải file kết quả.

### Cách chạy Streamlit
```bash
cd streamlit_app
python -m venv .venv && . .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# Đảm bảo file .env có API_BASE=http://localhost:8000 và USER_ID=ten_cua_ban
streamlit run app.py
```

## Backend — FastAPI
- Điểm vào: `main.py` (mount các router từ `controllers/`).
- Module chính:
  - `common/session_store.py` — lưu session (RAM/SQLite).
  - `common/models.py` — định nghĩa schema (Section, ...).
  - `data_processing/validators.py` — xác thực chỉ số 0-based.
  - `data_processing/rule_based_extractor.py` — trích xuất theo rule.
  - `data_processing/rule_learning_gpt.py` — sinh rule từ section confirm.
  - `data_processing/rule_memory.py` — fingerprint & lưu rule theo user.
  - `data_processing/chat_memory.py` — lưu hội thoại.
  - `services/intent_llm.py` — phân tích intent chat.
- Controllers tiêu biểu:
  - `/upload` — upload file, trả session_id.
  - `/preview` — sinh section gợi ý.
  - `/confirm` — xác nhận & học rule.
  - `/final` — chạy extractor → analyzer → planner → trả file & summary.
  - `/chat` — học từ hội thoại.

### Cách chạy FastAPI
```bash
python -m venv .venv && . .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
> Điều chỉnh module path (vd: `src.main:app`) nếu khác.

## Yêu cầu & Cấu hình
Các file cấu hình phát hiện:
- Agent_FastAPI/.env
- Agent_FastAPI/streamlit_app/.env
- Agent_FastAPI/streamlit_app/requirements.txt

Biến môi trường thường dùng:
- `API_BASE` — URL FastAPI để Streamlit gọi
- `OUTPUT_DIR` — thư mục xuất kết quả
- `OPENAI_API_KEY` — dùng nếu bật học rule qua GPT

## Ghi chú triển khai
Một số file chứa logic chính:
- common/session_store.py — quản lý session
- data_processing/analyzer.py — phân tích dữ liệu
- data_processing/planner.py — lập báo cáo
- data_processing/rule_based_extractor.py — extractor
- data_processing/rule_learning_gpt.py — học rule
- data_processing/rule_memory.py — lưu rule
- controllers/* — định nghĩa API endpoint
- streamlit_app/app.py — giao diện người dùng

---

