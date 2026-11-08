# 📝 Ứng dụng Kiểm tra Trắc nghiệm Trực tuyến

> Đồ án môn Lập trình Mạng - Mô hình Client-Server TCP

## 📋 Mô tả

Ứng dụng desktop cho phép tổ chức và thực hiện kiểm tra trắc nghiệm trực tuyến thông qua giao thức TCP. Hỗ trợ 3 vai trò: **Admin**, **Giáo viên**, **Sinh viên**.

## 🛠️ Công nghệ sử dụng

- **Ngôn ngữ**: Python 3.10+
- **Giao thức**: TCP Socket (JSON protocol với length-prefix framing)
- **Giao diện**: CustomTkinter
- **CSDL**: MySQL 8.0
- **Thư viện**: PyMySQL, bcrypt, Pillow

## ⚙️ Cài đặt

### 1. Cài đặt MySQL
- Tải và cài đặt MySQL 8.0: https://dev.mysql.com/downloads/
- Hoặc dùng XAMPP: https://www.apachefriends.org/

### 2. Tạo database và áp dụng migration

Chạy từ thư mục gốc dự án. Với database mới, nạp schema rồi áp dụng lần lượt bốn migration bên dưới. Với database đã có dữ liệu, chỉ áp dụng các migration còn thiếu, theo cùng thứ tự.

```powershell
mysql -u root -p --execute="SOURCE database/schema.sql"
mysql -u root -p --database=quiz_app --execute="SOURCE database/migrations/add_proctoring.sql"
mysql -u root -p --database=quiz_app --execute="SOURCE database/migrations/add_camera_proctoring.sql"
mysql -u root -p --database=quiz_app --execute="SOURCE database/migrations/add_camera_evidence.sql"
mysql -u root -p --database=quiz_app --execute="SOURCE database/migrations/add_camera_phone_detection.sql"
```

### 3. Cài đặt thư viện Python
```bash
python -m pip install -r requirements.txt
```

### 4. Cấu hình
Chỉnh sửa file `config.ini`:
```ini
[database]
host = localhost
port = 3306
user = root
password = your_password
db_name = quiz_app

[server]
host = 0.0.0.0
port = 9999

[client]
server_host = 127.0.0.1
server_port = 9999
```

## 🚀 Chạy ứng dụng

### Chạy Server
```bash
python -m server.main
```

### Chạy Client
```bash
python -m client.main
```

## Môn học và giám sát

- Ba môn ban đầu là dữ liệu mẫu. **Giáo viên → Quản lý đề thi → Thêm môn học** tạo môn do giáo viên đang đăng nhập phụ trách. Môn mới xuất hiện trong danh sách chọn khi tạo đề. **Admin → Quản lý môn học** quản lý môn và phân công giáo viên.
- Màn hình thi phóng to trong vùng làm việc Windows, giữ nút **X** và Taskbar. Rời cửa sổ từ 2,5 giây tạo cảnh báo. Các cảnh báo hiện giữa màn hình, có nút **Tiếp tục làm bài**. [Giám sát cửa sổ và heartbeat](docs/ANTI_CHEAT_PHASE1.md)
- Đề yêu cầu webcam có bước kiểm tra trước khi thi. Camera phát hiện thiếu khuôn mặt, nhiều khuôn mặt, ảnh khó quan sát và mất tín hiệu. Mô hình YOLOX bổ sung nhận diện điện thoại theo nhiều góc. [Giám sát camera](docs/ANTI_CHEAT_PHASE2_CAMERA.md)
- Với đề bật **Bắt buộc lưu ảnh bằng chứng**, học viên chấp nhận điều kiện khi bật camera. Ảnh cảnh báo được gửi qua TLS và giáo viên phụ trách bấm **👁** để xem. [Cài TLS, tải mô hình điện thoại và demo hai Client](docs/CAMERA_EVIDENCE.md)

### Cài hỗ trợ webcam trên máy học viên

```powershell
python -m pip install --only-binary=:all: -r requirements-camera.txt
```

Trên Windows, bật quyền truy cập camera cho ứng dụng desktop trong **Settings → Privacy & security → Camera**. Để nhận diện điện thoại, tải thêm mô hình ONNX theo [hướng dẫn ảnh bằng chứng](docs/CAMERA_EVIDENCE.md#cảnh-báo-điện-thoại). Với Python Launcher trên Windows, có thể dùng `py` thay cho `python`.

## 👤 Tài khoản mặc định

| Vai trò | Username | Password |
|---------|----------|----------|
| Admin | admin | admin123 |
| Giáo viên | teacher1 | admin123 |
| Giáo viên | teacher2 | admin123 |
| Sinh viên | student1 | admin123 |
| Sinh viên | student2 | admin123 |
| Sinh viên | student3 | admin123 |

> **Lưu ý**: Mật khẩu mặc định khi reset bởi Admin là `123456`

## 📁 Cấu trúc dự án

```
QuizApp/
├── common/                 # Module dùng chung
│   ├── protocol.py         # TCP protocol (length-prefix + JSON)
│   └── models.py           # Data models
├── server/                 # Module server
│   ├── main.py             # Entry point server
│   ├── client_handler.py   # Xử lý từng client
│   ├── database.py         # Kết nối MySQL
│   ├── dao/                # Data Access Objects
│   │   ├── user_dao.py
│   │   ├── subject_dao.py
│   │   ├── question_dao.py
│   │   ├── exam_dao.py
│   │   └── result_dao.py
│   └── service/            # Business Logic
│       ├── auth_service.py
│       ├── user_service.py
│       ├── question_service.py
│       └── exam_service.py
├── client/                 # Module client
│   ├── main.py             # Entry point client
│   ├── network.py          # Kết nối TCP server
│   └── ui/                 # Giao diện
│       ├── login_frame.py
│       ├── admin/          # Dashboard Admin
│       ├── teacher/        # Dashboard Giáo viên
│       └── student/        # Dashboard Sinh viên
├── database/
│   └── schema.sql          # Database schema + dữ liệu mẫu
├── config.ini              # Cấu hình
├── requirements.txt        # Dependencies
└── README.md
```

## 🔌 Giao thức TCP

Mỗi message được đóng gói: `[4 bytes length][JSON payload]`

**Request**: `{"command": "LOGIN", "token": "...", "data": {...}}`

**Response**: `{"status": "SUCCESS/ERROR", "message": "...", "data": ...}`

## 👥 Tác giả

- Thành viên 1 - MSSV
- Thành viên 2 - MSSV
