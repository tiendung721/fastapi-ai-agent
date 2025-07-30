# 🚀 FastAPI AI Agent – Phân tích file Excel bằng GPT

Đây là một hệ thống AI hoàn chỉnh sử dụng **FastAPI** và **OpenAI Chat Completion API** để phân tích dữ liệu trong các file Excel. Hệ thống mô phỏng hành vi của Assistant API nhưng **không dùng assistant_id, thread_id**, mà hoạt động linh hoạt hơn.

---

## 🔧 Tính năng nổi bật

- ✅ Cho phép tải lên file Excel `.xlsx`
- ✅ GPT tự động nhận diện và chia vùng dữ liệu (sections)
- ✅ GPT phân tích dữ liệu theo cột được chọn (`group_by`)
- ✅ GPT sinh báo cáo chuyên nghiệp bằng tiếng Việt
- ✅ Xuất báo cáo ra file `.xlsx`
- ✅ Cho phép người dùng xác nhận hoặc góp ý kết quả chia vùng
- ✅ Ghi nhớ cấu trúc bảng để học hỏi từ những file tương tự
- ✅ Quản lý lịch sử người dùng riêng biệt

---

## 📂 Cấu trúc thư mục

```
project/
├── main.py                     # FastAPI router chính
├── extractor_fastapi.py        # Gọi GPT chia vùng dữ liệu
├── analyzer_fastapi.py         # GPT phân tích dữ liệu theo cột
├── planner_fastapi.py          # GPT sinh báo cáo tiếng Việt
├── extractor_memory.py         # Ghi nhớ mẫu chia vùng
├── chat_memory.py              # Lưu lịch sử tương tác người dùng
├── report_exporter.py          # Xuất báo cáo ra file Excel
├── uploads/                    # File Excel người dùng tải lên
├── output/                     # File báo cáo sinh ra
├── memory_store/               # Cơ sở dữ liệu mẫu học được (JSON)
├── .env                        # Lưu OpenAI API key (không đưa lên GitHub)
```

---

## 🚀 Hướng dẫn sử dụng

### 1. Clone project

```bash
git clone https://github.com/tiendung721/fastapi-ai-agent.git
cd fastapi-ai-agent
```

### 2. Cài thư viện

```bash
pip install -r requirements.txt
```

### 3. Tạo file `.env`

Tạo file `.env` và thêm dòng:

```
OPENAI_API_KEY=your_openai_key_here
```

### 4. Chạy server FastAPI

```bash
uvicorn main:app --reload
```

Vào trình duyệt: [http://localhost:8000/docs](http://localhost:8000/docs) để thử API.

---

## 🧪 Luồng hoạt động mẫu

1. `POST /extractor-preview`: Tải file Excel → GPT gợi ý chia vùng
2. `POST /extractor-confirm`: Xác nhận hoặc chỉnh lại chia vùng
3. `POST /run-final`: Phân tích toàn bộ → GPT sinh báo cáo
4. `GET /history/{user_id}`: Xem lại lịch sử báo cáo
5. `GET /download-report?filename=...`: Tải file báo cáo `.xlsx`

---

## 📌 Ghi chú

- Không sử dụng Assistant API
- Toàn bộ hoạt động phân tích và sinh báo cáo đều qua **Completion API**
- Có khả năng ghi nhớ và cải thiện từ phản hồi người dùng
- Phù hợp tích hợp với hệ thống frontend riêng hoặc web client

---


