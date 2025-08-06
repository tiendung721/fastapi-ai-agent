# 🤖 Agent_FastAPI – Hệ thống AI Agent xử lý dữ liệu bảng

`Agent_FastAPI` là một hệ thống AI Agent hoàn chỉnh sử dụng kiến trúc **2 Plane: Control Plane và Data Plane** để xử lý, phân tích và sinh báo cáo từ các file dữ liệu không theo định dạng cố định (Excel, CSV...). Hệ thống hỗ trợ tự động học cách trích xuất dữ liệu, phân tích theo chiều, phản hồi người dùng, và cải thiện chất lượng phân tích qua mỗi lần tương tác.

---

## 📐 Kiến trúc tổng thể – 2 Plane

### 🎮 Control Plane – Tầng điều phối
- Điều phối các tác vụ xử lý, quản lý API, khởi chạy agent và xử lý phản hồi người dùng.
- Các thành phần chính:
  - `main.py`: khởi động FastAPI
  - `controllers/extractor_controller.py`
  - `controllers/pipeline_controller.py`
  - `controllers/section_confirm_controller.py`
  - `controllers/history_controller.py`

### 📦 Data Plane – Tầng xử lý dữ liệu
- Xử lý dữ liệu thực tế: trích xuất, phân tích, sinh báo cáo, lưu kết quả.
- Các thành phần chính:
  - `data_processing/rule_based_extractor.py`
  - `data_processing/rule_learning_gpt.py`
  - `data_processing/rule_memory.py`
  - `data_processing/analyzer.py`
  - `data_processing/planner.py`
  - `data_processing/exporter.py`
  - `data_processing/chat_memory.py`

---

## 🔁 Pipeline xử lý

1. **Sources (Người dùng upload file)**:
   - Giao diện frontend hoặc API upload file `.xlsx`, `.csv`.

2. **Ingestions**:
   - Nếu là file chưa từng thấy: gọi `rule_learning_gpt.py` để sinh rule từ GPT.
   - Nếu đã có rule: nạp từ `rule_memory.py`.

3. **Transformations**:
   - Phân tích bảng bằng `analyzer.py`.
   - Tính toán thống kê chiều dữ liệu: tần suất, entropy, đa dạng.

4. **Schema Mapping**:
   - Dùng `planner.py` ánh xạ chiều chính (`group_by`) và sinh báo cáo phân tích.
   - Tạo bảng thống kê theo yêu cầu.

5. **Staging & Destinations**:
   - Báo cáo được lưu vào file Excel (`.xlsx`) bằng `exporter.py`.
   - Gửi trả về người dùng frontend hoặc lưu nội bộ/S3.

6. **Error Handling & Feedback**:
   - Module `section_confirm_controller.py` hiển thị lỗi khi trích xuất/ánh xạ sai.
   - Người dùng xác nhận rule mới → lưu vào `rule_memory.py`.

---

## 🧠 Khả năng học & cải tiến
- Hệ thống ghi nhớ các phản hồi của người dùng và tự cải thiện rule chia section cho các file tương tự.
- Mỗi `user_id` có bộ rule riêng → tối ưu hóa trải nghiệm từng người.

---

## 📁 Cấu trúc thư mục

```
Agent_FastAPI/
├── main.py
├── .env
├── .gitignore
├── README.md
├── user_history.json
├── controllers/
│   ├── extractor_controller.py
│   ├── history_controller.py
│   ├── pipeline_controller.py
│   └── section_confirm_controller.py
├── data_processing/
│   ├── analyzer.py
│   ├── chat_memory.py
│   ├── exporter.py
│   ├── planner.py
│   ├── rule_based_extractor.py
│   ├── rule_learning_gpt.py
│   ├── rule_memory.py
│   └── section_detector.py
└── output/
    ├── extracted.json
    ├── analysis_result.json
    └── report.xlsx
```

---

## 🚀 Hướng dẫn khởi chạy

```bash
# Cài đặt thư viện
pip install -r requirements.txt

# Chạy FastAPI server
uvicorn main:app --reload

# Truy cập docs API tại:
http://localhost:8000/docs
```

---

## 💡 Công nghệ sử dụng

- [x] OpenAI GPT-4o API — học rule tự động
- [x] FastAPI — xây dựng API backend
- [x] Pandas, OpenPyXL — xử lý bảng dữ liệu
- [x] JSON/Excel — lưu trữ đầu ra và kết quả phân tích


---





