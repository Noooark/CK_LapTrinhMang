-- =====================================================
-- ỨNG DỤNG KIỂM TRA TRẮC NGHIỆM TRỰC TUYẾN
-- Database Schema - MySQL 8.0
-- =====================================================

CREATE DATABASE IF NOT EXISTS quiz_app
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE quiz_app;

-- Bảng người dùng
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    role ENUM('ADMIN', 'TEACHER', 'STUDENT') NOT NULL DEFAULT 'STUDENT',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Bảng môn học
CREATE TABLE IF NOT EXISTS subjects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    teacher_id INT,
    FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- Bảng câu hỏi
CREATE TABLE IF NOT EXISTS questions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    subject_id INT NOT NULL,
    content TEXT NOT NULL,
    option_a VARCHAR(500) NOT NULL,
    option_b VARCHAR(500) NOT NULL,
    option_c VARCHAR(500) NOT NULL,
    option_d VARCHAR(500) NOT NULL,
    correct_answer CHAR(1) NOT NULL,
    difficulty ENUM('EASY', 'MEDIUM', 'HARD') DEFAULT 'MEDIUM',
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Bảng đề thi
CREATE TABLE IF NOT EXISTS exams (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    subject_id INT NOT NULL,
    teacher_id INT NOT NULL,
    duration_minutes INT DEFAULT 30,
    total_questions INT DEFAULT 0,
    status ENUM('DRAFT', 'ACTIVE', 'ENDED') DEFAULT 'DRAFT',
    start_time DATETIME,
    end_time DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
    FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Bảng câu hỏi trong đề thi
CREATE TABLE IF NOT EXISTS exam_questions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    exam_id INT NOT NULL,
    question_id INT NOT NULL,
    order_number INT,
    FOREIGN KEY (exam_id) REFERENCES exams(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Bảng kết quả thi
CREATE TABLE IF NOT EXISTS exam_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    exam_id INT NOT NULL,
    student_id INT NOT NULL,
    correct_count INT DEFAULT 0,
    total_questions INT DEFAULT 0,
    score FLOAT DEFAULT 0.0,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_exam_student (exam_id, student_id),
    FOREIGN KEY (exam_id) REFERENCES exams(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Bảng chi tiết câu trả lời
CREATE TABLE IF NOT EXISTS exam_answers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    result_id INT NOT NULL,
    question_id INT NOT NULL,
    selected_answer CHAR(1),
    is_correct BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (result_id) REFERENCES exam_results(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =====================================================
-- DỮ LIỆU MẪU
-- =====================================================

-- Admin mặc định (password: admin123)
-- Bcrypt hash cho 'admin123'
INSERT INTO users (username, password, full_name, email, role) VALUES
('admin', '$2b$12$2gady2d2zH4pYgKbbCANsOmxaT34vNZsyGFEsvl7yML8H1leOTQaG', 'Quản trị viên', 'admin@quiz.app', 'ADMIN');

-- Giáo viên mẫu (password: admin123)
INSERT INTO users (username, password, full_name, email, role) VALUES
('teacher1', '$2b$12$2gady2d2zH4pYgKbbCANsOmxaT34vNZsyGFEsvl7yML8H1leOTQaG', 'Nguyễn Văn A', 'nguyenvana@quiz.app', 'TEACHER'),
('teacher2', '$2b$12$2gady2d2zH4pYgKbbCANsOmxaT34vNZsyGFEsvl7yML8H1leOTQaG', 'Trần Thị B', 'tranthib@quiz.app', 'TEACHER');

-- Sinh viên mẫu (password: admin123)
INSERT INTO users (username, password, full_name, email, role) VALUES
('student1', '$2b$12$2gady2d2zH4pYgKbbCANsOmxaT34vNZsyGFEsvl7yML8H1leOTQaG', 'Lê Hoàng C', 'lehoangc@quiz.app', 'STUDENT'),
('student2', '$2b$12$2gady2d2zH4pYgKbbCANsOmxaT34vNZsyGFEsvl7yML8H1leOTQaG', 'Phạm Minh D', 'phamminhd@quiz.app', 'STUDENT'),
('student3', '$2b$12$2gady2d2zH4pYgKbbCANsOmxaT34vNZsyGFEsvl7yML8H1leOTQaG', 'Võ Thanh E', 'vothanhe@quiz.app', 'STUDENT');

-- Môn học mẫu
INSERT INTO subjects (name, description, teacher_id) VALUES
('Lập trình Python', 'Môn học về ngôn ngữ lập trình Python cơ bản và nâng cao', 2),
('Mạng máy tính', 'Kiến thức nền tảng về mạng máy tính và giao thức TCP/IP', 3),
('Cơ sở dữ liệu', 'Thiết kế và quản lý cơ sở dữ liệu quan hệ với SQL', 2);

-- Câu hỏi mẫu - Lập trình Python
INSERT INTO questions (subject_id, content, option_a, option_b, option_c, option_d, correct_answer, difficulty) VALUES
(1, 'Python là ngôn ngữ lập trình thuộc loại nào?', 'Biên dịch (Compiled)', 'Thông dịch (Interpreted)', 'Cả hai', 'Không thuộc loại nào', 'B', 'EASY'),
(1, 'Kiểu dữ liệu nào KHÔNG có trong Python?', 'list', 'tuple', 'array', 'dict', 'C', 'EASY'),
(1, 'Kết quả của 3 ** 2 trong Python là?', '6', '9', '8', '5', 'B', 'EASY'),
(1, 'Phương thức nào dùng để thêm phần tử vào cuối list?', 'add()', 'insert()', 'append()', 'push()', 'C', 'MEDIUM'),
(1, 'List comprehension nào đúng cú pháp?', '[x for x in range(10)]', '[x : x in range(10)]', '{x for x in range(10)}', '(x for x in range(10))', 'A', 'MEDIUM'),
(1, 'Decorator trong Python dùng ký hiệu gì?', '#', '@', '&', '!', 'B', 'HARD'),
(1, 'Generator trong Python sử dụng từ khóa nào?', 'return', 'yield', 'generate', 'iter', 'B', 'HARD'),
(1, 'Thư viện nào dùng để lập trình socket trong Python?', 'networking', 'socket', 'tcp', 'net', 'B', 'MEDIUM');

-- Câu hỏi mẫu - Mạng máy tính
INSERT INTO questions (subject_id, content, option_a, option_b, option_c, option_d, correct_answer, difficulty) VALUES
(2, 'TCP thuộc tầng nào trong mô hình OSI?', 'Tầng mạng (Network)', 'Tầng giao vận (Transport)', 'Tầng ứng dụng (Application)', 'Tầng liên kết dữ liệu (Data Link)', 'B', 'EASY'),
(2, 'Địa chỉ IP v4 có bao nhiêu bit?', '16 bit', '32 bit', '64 bit', '128 bit', 'B', 'EASY'),
(2, 'Port mặc định của HTTP là?', '21', '25', '80', '443', 'C', 'EASY'),
(2, 'Giao thức nào đảm bảo truyền tin cậy?', 'UDP', 'TCP', 'ICMP', 'ARP', 'B', 'MEDIUM'),
(2, 'Subnet mask 255.255.255.0 có prefix length là?', '/8', '/16', '/24', '/32', 'C', 'MEDIUM'),
(2, 'Three-way handshake của TCP gồm các bước nào?', 'SYN - ACK - FIN', 'SYN - SYN-ACK - ACK', 'ACK - SYN - FIN', 'FIN - ACK - SYN', 'B', 'HARD');

-- Câu hỏi mẫu - Cơ sở dữ liệu
INSERT INTO questions (subject_id, content, option_a, option_b, option_c, option_d, correct_answer, difficulty) VALUES
(3, 'SQL là viết tắt của?', 'Structured Query Language', 'Simple Query Language', 'Standard Query Language', 'Server Query Language', 'A', 'EASY'),
(3, 'Lệnh nào dùng để tạo bảng?', 'MAKE TABLE', 'CREATE TABLE', 'NEW TABLE', 'ADD TABLE', 'B', 'EASY'),
(3, 'Khóa chính (Primary Key) có đặc điểm gì?', 'Có thể NULL', 'Không duy nhất', 'Duy nhất và NOT NULL', 'Có thể trùng lặp', 'C', 'MEDIUM'),
(3, 'JOIN nào trả về tất cả các hàng từ cả hai bảng?', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL OUTER JOIN', 'D', 'HARD'),
(3, 'Chuẩn hóa 3NF yêu cầu?', 'Không phụ thuộc bắc cầu', 'Không phụ thuộc hàm', 'Chỉ có 1 khóa chính', 'Không có khóa ngoại', 'A', 'HARD');
