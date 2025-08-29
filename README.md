# Agent_FastAPI — Tài liệu README chính thức

> **Phiên bản**: 2.0 • **Nền tảng**: FastAPI • **Chức năng**: Trích xuất → Phân tích → Lập báo cáo từ file Excel/CSV, có học rule theo người dùng

---

## 1) Tổng quan

Hệ thống triển khai pipeline 3 bước:
1. **Preview (tự phát hiện section / áp dụng rule đã học)**  
2. **Confirm (xác nhận &/hoặc học rule mới theo user_id + fingerprint)**  
3. **Final (phân tích + lập báo cáo + xuất file)**

Dữ liệu phiên làm việc (session), lịch sử người dùng và rule được lưu bền vững để chạy lại/tiếp tục.

---

## 2) Cấu trúc thư mục & file chính

```
Agent_FastAPI/
├─ main.py                        # Đăng ký router, cấu hình FastAPI
├─ .env                           # OPENAI_API_KEY, OPENAI_MODEL=...
├─ session_store.sqlite3          # Lưu session (df path, sections, used_rule...)
├─ user_history.json              # Lưu lịch sử thao tác theo user_id
├─ common/
│  ├─ models.py                   # Pydantic: Section, SessionData
│  └─ session_store.py            # Lớp SessionStore (SQLite)
├─ controllers/
│  ├─ extractor_controller.py     # /upload, /preview
│  ├─ section_confirm_controller.py # /confirm_sections
│  ├─ pipeline_controller.py      # /run_final
│  └─ history_controller.py       # /history/{user_id} (GET/DELETE)
├─ data_processing/
│  ├─ section_detector.py         # detect_sections_auto(): heuristic chia section
│  ├─ rule_based_extractor.py     # extract_sections_with_rule(): cắt theo rule
│  ├─ rule_learning_gpt.py        # learn_rule_from_sections(): học rule (OpenAI)
│  ├─ rule_memory.py              # Lưu/tải rule theo (user_id, fingerprint)
│  ├─ rule_schema.py              # Pydantic schema cho rule
│  ├─ validators.py               # Kiểm tra index 1-based, hợp lệ section
│  ├─ analyzer.py                 # Chuẩn hóa region -> phân tích -> summary
│  ├─ auto_group_by.py            # Heuristic chọn cột group_by
│  ├─ planner.py                  # Sinh báo cáo (LLM) từ kết quả phân tích
│  ├─ exporter.py                 # Xuất báo cáo Excel (xlsx)
│  └─ chat_memory.py              # Bộ nhớ lịch sử người dùng (JSON)
└─ rule_memory/                   # Thư mục chứa rule đã học theo fingerprint/user
```

---

## 3) Dữ liệu & Lưu trữ

- **Session (SQLite: `session_store.sqlite3`)**  
  Bảng `sessions(session_id TEXT PRIMARY KEY, data TEXT, updated_at INTEGER)`.  
  `data` là JSON chứa:
  - `session_id`, `user_id`, `file_path`
  - `auto_sections` (danh sách `Section`)
  - `confirmed_sections` (nếu đã confirm)
  - `used_rule` (rule áp dụng trong preview, nếu có)

- **History (`user_history.json`)**  
  Lưu vết thao tác theo `user_id` bằng `data_processing/chat_memory.py`:
  - Ghi lại các mốc: UPLOAD_OK, PREVIEW_OK, CONFIRMED, FINAL_OK kèm thời gian.

- **Rule Memory (`rule_memory/`)**  
  Lưu theo **(user_id, fingerprint)**.  
  `fingerprint` được tạo từ danh sách header (đã chuẩn hóa) và (tuỳ chọn) `sheet_name`.  
  Đường dẫn file mẫu: `rule_memory/{fingerprint}/{user_id}.json`.

---

## 4) Heuristic phát hiện Section (auto)

Trong `data_processing/section_detector.py`:
- **Header row**: hàng có ≥2 ô text (>=2 ký tự) và **không có** số → xem là tiêu đề.
- **Data row**: hàng có ≥2 ô có dữ liệu.
- **Blank row**: kết thúc section hiện tại.
- Kết quả trả về danh sách `Section` (1-based): `start_row`, `end_row`, `header_row`, `label` (tùy chọn).

> Lưu ý: Mọi index là **1-based**. `validators.to_one_based` và `validate_sections` đảm bảo an toàn chỉ số.

---

## 5) Pipeline & Luồng gọi lớp

### Bước 1 — Upload & Preview
- **Endpoint**: `POST /upload` (form-data: `file: UploadFile`, `user_id: str`)  
  - Lưu tệp vào ổ đĩa, tạo `session_id`, ghi `SessionStore`.
  - Trả `session_id`.
- **Endpoint**: `POST /preview` (form-data: `session_id: str`, `sheet_name: Optional[str]`)  
  - Đọc `df` từ `session`.
  - Tính `fingerprint = get_fingerprint(df, sheet_name)`.
  - **Nếu có rule**: `extract_sections_with_rule(df, rule)` → `sections`, `used_rule=True`.  
  - **Nếu chưa có rule**: `detect_sections_auto(df)` → `sections`, `used_rule=False`.
  - Lưu `auto_sections` và ghi lịch sử `PREVIEW_OK`.
  - **Response**:
    ```json
    {
      "ok": true,
      "code": "PREVIEW_OK",
      "data": { "auto_sections": [...], "nrows": 123, "used_rule": false }
    }
    ```

### Bước 2 — Confirm Sections (và tự học rule nếu cần)
- **Endpoint**: `POST /confirm_sections` (JSON body)
  - Input: `session_id`, `user_id`, `sections: List[Section]`, `sheet_name (optional)`.
  - Gọi `validate_sections` để đảm bảo 1-based và hợp lệ trong kích thước `df`.
  - **Tự học rule** (nếu cấu hình hoặc nếu chưa có rule):
    - `learn_rule_from_sections(df, sections)` → sinh rule (qua OpenAI).
    - `save_rule_for_fingerprint(fingerprint, rule, user_id)`.
    - Ghi `auto_learned_rule = true/false`.
  - Cập nhật `SessionStore.confirmed_sections`, ghi lịch sử `CONFIRMED`.
  - **Response**:
    ```json
    { "ok": true, "code": "CONFIRMED", "data": { "count": N, "sections": [...] }, "auto_learned_rule": true }
    ```

### Bước 3 — Final (Phân tích → Báo cáo → Xuất file)
- **Endpoint**: `POST /run_final` (query/body có `session_id`, `user_id`, `sheet_name (optional)`)
  - Lấy `df` + `confirmed_sections` từ session (nếu chưa confirm sẽ lỗi).
  - **Analyzer** (`data_processing/analyzer.py`):
    - Chuẩn hoá từng region theo `header_row` & `end_row`.
    - Tự chọn `group_by` (heuristic `auto_group_by.py`).
    - Tính summary (tần suất, phân bố...) cho từng section.
  - **Planner** (`data_processing/planner.py`):
    - Gọi OpenAI sinh **báo cáo tiếng Việt** từ kết quả phân tích.
  - **Exporter** (`data_processing/exporter.py`):
    - Xuất file Excel (report.xlsx) gồm: metadata + nội dung báo cáo dạng text.
  - Ghi lịch sử `FINAL_OK`.
  - **Response**:
    ```json
    {
      "ok": true,
      "code": "FINAL_OK",
      "data": {
        "analysis": {...},       // JSON phân tích theo section
        "report": "nội dung...", // Báo cáo dạng text
        "export_file": "path/to/report.xlsx"
      },
      "auto_learned_rule": false
    }
    ```

### Lịch sử
- **GET `/history/{user_id}`** → trả mảng các bản ghi lịch sử đã lưu.
- **DELETE `/history/{user_id}`** → xoá lịch sử của người dùng.

Sơ đồ gọi lớp (rút gọn):

```
main.py
 ├─ controllers/extractor_controller.py
 │    ├─ section_detector.detect_sections_auto
 │    ├─ rule_memory.get_fingerprint / get_rule_for_fingerprint
 │    ├─ rule_based_extractor.extract_sections_with_rule
 │    └─ validators.to_one_based / validate_sections
 ├─ controllers/section_confirm_controller.py
 │    ├─ rule_learning_gpt.learn_rule_from_sections  (nếu cần)
 │    └─ rule_memory.save_rule_for_fingerprint
 └─ controllers/pipeline_controller.py
      ├─ analyzer.run_analysis
      ├─ planner.build_report
      └─ exporter.save_report_excel
```

---

## 6) Cài đặt & Khởi chạy

### Yêu cầu
- Python 3.10+
- Các thư viện trong `requirements.txt`
- Biến môi trường:
  - `OPENAI_API_KEY` (bắt buộc nếu dùng học rule / planner)
  - `OPENAI_MODEL` (mặc định `gpt-4o`)

### Cài đặt
```bash
pip install -r requirements.txt
```

### Chạy server
```bash
uvicorn main:app --reload
```
Mặc định: `http://127.0.0.1:8000`

---

## 7) Quy ước dữ liệu (chuẩn 1-based)

- Tất cả `start_row`, `end_row`, `header_row` đều 1-based theo **sheet gốc**.
- `validate_sections` sẽ:
  - Chuyển về 1-based nếu đầu vào 0-based.
  - Kiểm tra ràng buộc: `1 ≤ header_row ≤ start_row ≤ end_row ≤ n_rows`.

---

## 8) Gợi ý tích hợp Frontend / Client

Trình tự gọi API khuyến nghị:
1. `POST /upload` → lấy `session_id`
2. `POST /preview` (kèm `session_id`) → hiển thị `auto_sections`
3. Cho phép người dùng chỉnh sửa → gửi `POST /confirm_sections`
4. `POST /run_final` → hiển thị báo cáo & link tải Excel

---

## 9) Câu hỏi thường gặp (FAQ)

- **Có chạy nhiều sheet cùng lúc không?**  
  Code hiện hỗ trợ truyền `sheet_name` để tạo `fingerprint` riêng. Có thể gọi lặp theo từng sheet.  
- **Mất server/restart có mất rule/lịch sử không?**  
  - `rule_memory/` và `user_history.json` là file trên đĩa → **không mất**.  
  - Session trong SQLite sẽ mất nếu bạn tự xoá DB, còn mặc định thì giữ.
- **`used_rule: false` nghĩa là gì ở preview?**  
  Preview dùng heuristic `detect_sections_auto` (không áp dụng rule). Khi đã học/lưu rule, lần sau sẽ là `true`.

---

## 10) Phát triển mở rộng

- Bổ sung `sheet_name` vào tất cả bước để huấn luyện/áp dụng rule theo từng sheet.
- Nâng cấp `get_fingerprint` bằng kích thước bảng, số sheet, checksum mẫu header.
- Thêm kiểm thử tự động (pytest) cho `validators`, `analyzer`, `section_detector`.
- Exporter: ghi thêm từng region ra nhiều sheet hoặc cả bảng thống kê.

---

© 2025 Agent_FastAPI
