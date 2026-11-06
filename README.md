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

### 2. Tạo Database
```bash
mysql -u root -p < database/schema.sql
```

### 3. Cài đặt thư viện Python
```bash
pip install -r requirements.txt
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
