# Giai đoạn 2 · Giám sát camera

## Cài đặt và migration

Giai đoạn 2 giữ giao diện thi dạng cửa sổ phóng to với nút X và Taskbar. Đề cũ mặc định không yêu cầu camera. Server và Client cập nhật cùng đợt.

Dừng Server và áp dụng [add_camera_proctoring.sql](../database/migrations/add_camera_proctoring.sql) **một lần** vào database đã có migration Giai đoạn 1. Với database mới, chạy `schema.sql`, `add_proctoring.sql`, rồi migration này theo thứ tự. Thay thông tin máy chủ, tài khoản và tên database theo `config.ini`.

```powershell
mysql --host=localhost --port=3306 --user=your_user -p --database=quiz_app --execute="SOURCE database/migrations/add_camera_proctoring.sql"
py -m pip install -r requirements.txt
py -m pip install --only-binary=:all: -r requirements-camera.txt
py -m server.main
```

Dòng cài OpenCV chỉ cần ở Client sinh viên làm đề yêu cầu webcam. Server, giáo viên và sinh viên làm đề thường chạy với bộ thư viện cơ bản. OpenCV Headless 4.13.0.92 cung cấp wheel Windows x64 `cp37-abi3`. Đã kiểm tra import và nạp cascade trên Windows với CPython 3.14.2. Bản Headless dùng Tk để hiển thị preview. Cascade Haar đi cùng OpenCV giúp tránh thêm runtime MediaPipe hoặc tệp mô hình tải riêng. [OpenCV trên PyPI](https://pypi.org/project/opencv-python-headless/4.13.0.92/)

Migration thêm cờ và bốn ngưỡng trên `exams`, trạng thái camera trên `exam_attempts` và loại sự kiện, số khuôn mặt, chỉ mục tần suất trên `proctoring_events`. Lịch sử, câu trả lời và điểm đã lưu được giữ lại. Với MySQL, các lệnh DDL áp dụng theo từng câu. Nếu một câu lỗi, kiểm tra bảng và tiếp tục từ câu chưa áp dụng.

## Chạy hai Client

Camera có thể nhận diện thêm điện thoại khi máy học viên đã cài mô hình YOLOX. Xem [cách tải mô hình, migration và cấu hình TLS](CAMERA_EVIDENCE.md#cảnh-báo-điện-thoại).

```powershell
py -m client.main
```

1. Giáo viên tạo đề trong **Quản lý đề thi**, chọn **Yêu cầu camera khi thi**, giữ hoặc đổi các ngưỡng rồi mở đề. Chọn đề đó ở **Giám sát kỳ thi**.
2. Học viên chọn đề, xác nhận giám sát rồi bấm **Đồng ý bật camera** trong hộp kiểm tra. Camera mặc định có chỉ số 0. Có thể nhập chỉ số khác và chọn **Thử lại / đổi thiết bị**. Khi preview đủ sáng và có đúng một khuôn mặt, nút **Bắt đầu thi** được bật.
3. Trong lượt thi, thử rời khung hình, đưa thêm người vào khung, giảm ánh sáng hoặc ngắt webcam theo các ngưỡng bên dưới. Kiểm tra chỉ báo bên học viên, cột **Camera** và lịch sử bên giáo viên. Khi đã khôi phục thiết bị, Client tự thử kết nối lại hoặc học viên có thể bấm **Kết nối lại**.
4. Học viên nộp bài. Đối chiếu điểm, đáp án và trạng thái camera **Đã dừng** trên Dashboard.

Trên Windows, vào **Settings → Privacy & security → Camera**. Bật **Camera access** và **Let desktop apps access your camera**. Đóng ứng dụng khác đang giữ webcam nếu cần. Nếu không đồng ý hoặc không có thiết bị, quay lại danh sách đề và liên hệ giáo viên để được hướng dẫn. [Microsoft Support](https://support.microsoft.com/en-us/windows/privacy/windows-camera-microphone-and-privacy)

Trên Ubuntu/Linux, chạy bằng `python3` trong môi trường có Tk và wheel OpenCV tương thích. Kiểm tra quyền truy cập thiết bị camera, ví dụ `/dev/video0`. Quy trình desktop Linux chưa được xác minh trong đợt này.

## Kiến trúc và sự kiện

Camera chạy bằng một worker, phân tích tối đa khoảng 3 khung/giây và chỉ giữ mẫu mới nhất. Preview xử lý tại chỗ trong thời gian kiểm tra trước thi. Sau khi vào thi, worker chỉ chuyển kết quả phân tích về Tk. Luồng Tk cập nhật trạng thái và đo các đợt bất thường bằng monotonic. Đồng hồ và worker TCP hoạt động riêng. Các sự kiện dùng UUID và được gửi lại bằng UUID cũ khi TCP hồi phục.

| Sự kiện | Điều kiện mặc định |
| --- | --- |
| `CAMERA_NO_FACE` | Không thấy khuôn mặt trong 10 giây liên tục |
| `CAMERA_MULTIPLE_FACES` | Từ hai khuôn mặt trong 3 giây liên tục, kèm số khuôn mặt |
| `CAMERA_DISCONNECTED` | Mất tín hiệu 5 giây liên tục. Bản ghi cũ có thời lượng 0 biểu thị học viên đã rút quyền từ Client cũ |
| `CAMERA_OBSTRUCTED` | Ảnh quá tối hoặc ít tương phản trong 10 giây liên tục |
| `CAMERA_RECOVERED` | Sau một cảnh báo, ảnh đủ điều kiện và có một khuôn mặt ổn định trong ít nhất 1 giây. Sự kiện thông tin này không làm tăng số cảnh báo |

Giáo viên cấu hình bốn ngưỡng thời gian khi tạo đề, từ 1 đến 300 giây. Có thể hiệu chỉnh chất lượng ảnh trên Client bằng biến môi trường `QUIZ_CAMERA_MIN_BRIGHTNESS` và `QUIZ_CAMERA_MIN_CONTRAST`. Giá trị mặc định lần lượt là 35 và 9, trên thang pixel 0–255.

Không có command TCP mới. `START_EXAM_ATTEMPT` nhận thêm cờ `camera_ready` và trả ngưỡng. `REPORT_EXAM_EVENT` nhận các loại trên, chỉ chấp nhận metadata cho sự kiện camera và giới hạn 10 sự kiện camera trong 10 giây mỗi lượt. UUID trùng được xác nhận mà không ghi lại. Header TCP 4 byte được giữ nguyên. Server từ chối request lớn hơn 32 MiB.

## Quyền riêng tư và giới hạn

Camera bật sau khi học viên đồng ý. Client dừng camera khi hủy bước kiểm tra, mở lượt thi thất bại, hết giờ, nộp thành công, hoặc đóng ứng dụng. Nếu quyền camera bị thu hồi ở cấp hệ điều hành, Client xử lý như mất tín hiệu. Worker gọi release khi thao tác đọc native trả về. Nếu driver bị treo, giao diện vẫn chạy và ghi nhận mất tín hiệu, còn việc giải phóng thiết bị có thể chậm đến khi driver trả về hoặc tiến trình kết thúc.

Chế độ giám sát mặc định chỉ đếm khuôn mặt và gửi metadata. Các đề có chính sách lưu ảnh riêng dùng quy trình đồng ý trong [Ảnh bằng chứng camera](CAMERA_EVIDENCE.md). Ánh sáng, góc mặt, kính và chuyển động có thể ảnh hưởng kết quả. `camera_ready` là xác nhận từ Client, không phải chứng thực phần cứng. Giáo viên xem xét ngữ cảnh trước khi đánh giá các cảnh báo.

## Kiểm thử

```powershell
py -m unittest discover -s tests -p test_camera_monitor.py -v
$env:QUIZ_TEST_DESKTOP = '1'
$env:QUIZ_TEST_DATABASE = '1'
py -m unittest discover -s tests -v
```

Bộ test desktop dùng Tk và camera giả. Bộ test TCP dùng MariaDB hoặc MySQL cục bộ và tạo một schema kiểm thử riêng. Kiểm thử webcam thật gồm mở preview sau khi đồng ý, rút thiết bị trong lượt thi, kết nối lại và xác nhận đèn camera tắt sau khi nộp. Cần thực hiện các bước này trên máy có webcam và được phép truy cập.

## Tệp

- Mới: `common/camera.py`, `client/anti_cheat/camera_monitor.py`, `client/anti_cheat/face_detector.py`, `client/ui/student/camera_check_dialog.py`, `database/migrations/add_camera_proctoring.sql`, `requirements-camera.txt`, `tests/test_camera_monitor.py` và tài liệu này.
- Sửa: `client/ui/student/student_dashboard.py`, `client/ui/student/exam_taking.py`, `client/ui/teacher/exam_creator.py`, `client/ui/teacher/monitoring_panel.py`, `common/protocol.py`, `server/client_handler.py`, `server/dao/exam_dao.py`, `server/dao/proctoring_dao.py`, `server/service/exam_service.py`, `server/service/proctoring_service.py`, `tests/test_proctoring_tcp.py`.
