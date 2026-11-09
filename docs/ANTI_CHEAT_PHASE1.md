# Giám sát kỳ thi Giai đoạn 1

## Luồng làm bài

Sinh viên xác nhận thông báo giám sát trước khi vào bài. Server kiểm tra đề đã mở và tài khoản chưa nộp bài, rồi trả về mã lượt thi, câu hỏi và thời gian còn lại. Lượt thi được xác định theo cặp đề thi và sinh viên. Gửi lại yêu cầu mở lượt thi giữ nguyên thời điểm bắt đầu và hạn nộp.

Client ẩn menu sinh viên, phóng to cửa sổ trong vùng làm việc của hệ điều hành để giữ thanh tiêu đề, nút X và Taskbar trên Windows và dùng đồng hồ monotonic để đếm ngược. Khi ứng dụng mất focus ít nhất 2,5 giây, Client xếp một sự kiện cho đợt rời cửa sổ đó, kể cả khi sinh viên vẫn đang ở ứng dụng khác. Thời lượng được ghi là số giây đã quan sát lúc vượt ngưỡng. Khi quay lại, sinh viên thấy cảnh báo ngay trên màn hình làm bài. Focus giữa widget, cửa sổ con và hộp thoại nội bộ được bỏ qua.

Heartbeat gửi mỗi 10 giây. Server quét mỗi 2 giây và đánh dấu mất liên lạc từ 30 giây kể từ heartbeat cuối. Khi nhận heartbeat hợp lệ trở lại, Server cập nhật trạng thái và giữ lịch sử của đợt mất kết nối. Mỗi lượt thi dùng một worker tuần tự cho heartbeat, hàng đợi cảnh báo và nộp bài. UUID giữ nguyên khi thử lại. Đọc socket hết thời gian chờ sẽ đóng socket để lần gửi sau mở kết nối mới. Tk nhận kết quả qua hàng đợi bằng `after()`.

## Thời hạn và bảo toàn đáp án

- Hạn làm bài tính từ lúc Server tạo lượt thi cộng thời lượng của đề. Nếu giáo viên kết thúc đề sớm, Server dùng thời điểm kết thúc đó làm hạn mới và báo thời gian còn lại trong heartbeat.
- Client khóa chỉnh sửa khi hết giờ và tự gửi đáp án. Server chấp nhận bài trong 120 giây sau hạn để xử lý gián đoạn mạng hoặc phản hồi chậm. Khoảng gia hạn được kiểm tra bằng đồng hồ cơ sở dữ liệu. Việc gửi lại sau khi bài đã lưu trả về kết quả trước đó, kể cả khi đã hết gia hạn.
- Kết quả, các đáp án và trạng thái đã nộp được lưu trong cùng giao dịch. Cách tính điểm vẫn là tỷ lệ số câu đúng trên tổng số câu nhân 10. Ràng buộc trên kết quả và khóa lượt thi bảo vệ khi hai kết nối nộp đồng thời.
- Bấm đóng cửa sổ khi đang thi sẽ hỏi xác nhận. Nếu đồng ý, Client gửi sự kiện yêu cầu thoát, nộp các đáp án đã chọn rồi đóng sau khi nhận xác nhận. Nếu gặp lỗi, đáp án vẫn nằm trong cửa sổ hiện tại. Sinh viên có thể thử lại hoặc dùng nút đóng để lưu bản sao JSON rồi thoát. Tệp JSON chỉ là bản sao để đối chiếu và cần chuyển qua quy trình hỗ trợ của đơn vị tổ chức thi.
- Khi Client vẫn mở, kết nối TCP có thể khôi phục bằng token và lượt thi hiện tại. Nếu tiến trình bị dừng đột ngột, các đáp án chưa nộp và cảnh báo chưa gửi trong RAM có thể mất. Khởi động lại Server làm mất token phiên đang lưu trong bộ nhớ. Cần đăng nhập lại sau khi Server khởi động lại.

## Migration và khởi động

Với database đang sử dụng, áp dụng riêng migration [add_proctoring.sql](../database/migrations/add_proctoring.sql). Chạy từ thư mục gốc dự án, thay máy chủ, cổng, tài khoản và tên database bằng thông tin tương ứng trong `config.ini`. Tùy chọn `-p` yêu cầu nhập mật khẩu tương tác.

```powershell
mysql --host=localhost --port=3306 --user=your_user -p --database=quiz_app --execute="SOURCE database/migrations/add_proctoring.sql"
```

Với database mới, nạp `database/schema.sql` trước rồi chạy migration trên. Có thể chạy lại migration. Nó tạo hai bảng InnoDB và các khóa ngoại, chỉ mục, ràng buộc duy nhất. Dữ liệu trong `exam_results` và `exam_answers` giữ nguyên. Các bài đã nộp trước migration vẫn được nhận diện qua kết quả cũ.

Cài thư viện và chạy Server. Trên hệ điều hành khác, thay `py` bằng lệnh Python của môi trường.

```powershell
py -m pip install -r requirements.txt
py -m server.main
```

Mở hai terminal Client. Nếu chạy trên máy khác, trỏ `[client] server_host` và `server_port` tới Server.

```powershell
py -m client.main
```

## Demo hai Client

1. Đăng nhập giáo viên, mở một đề có câu hỏi trong **Quản lý đề thi**, rồi chọn đề ở **Giám sát kỳ thi**.
2. Đăng nhập sinh viên trên Client thứ hai. Chọn đề và đồng ý thông báo giám sát. Kiểm tra cửa sổ được phóng to và vẫn có nút X cùng Taskbar và nhãn **Đang được giám sát**.
3. Chọn một đáp án rồi chuyển sang ứng dụng khác hơn 2,5 giây. Trong tab giám sát, kiểm tra lịch sử **Rời cửa sổ** và đếm cảnh báo. Bảng thăm dò khoảng mỗi 2 giây khi kết nối tốt.
4. Quay lại ứng dụng sinh viên và kiểm tra thông báo cùng đáp án đã chọn. Ở Client giáo viên, chọn dòng cảnh báo và bấm **Đánh dấu đã xem**. Có thể dùng **Cảnh báo cũ hơn** để phân trang.
5. Nộp bài. Kiểm tra điểm trong lịch sử sinh viên, trạng thái **Đã nộp** bên giáo viên và việc cửa sổ trở về kích thước ban đầu.
6. Để thử heartbeat, dùng một lượt thi khác, tạm ngắt kết nối Client sinh viên hơn 30 giây rồi kết nối lại khi còn giờ. Kiểm tra **Mất kết nối** chỉ xuất hiện một lần cho đợt đó và trạng thái chuyển về **Đang kết nối**.

## TCP

Tất cả lệnh giữ JSON và header độ dài 4 byte big-endian hiện có. Client gửi token trong từng request. Mã sinh viên lấy từ phiên đăng nhập.

| Command | Vai trò | Dữ liệu chính |
| --- | --- | --- |
| `START_EXAM_ATTEMPT` | STUDENT | `exam_id` |
| `REPORT_EXAM_EVENT` | STUDENT | `attempt_id`, UUID `event_id`, `event_type`, `duration_seconds` cho `FOCUS_LOST` |
| `EXAM_HEARTBEAT` | STUDENT | `attempt_id` |
| `GET_MONITORING_STATUS` | TEACHER, ADMIN | `exam_id` |
| `GET_EXAM_EVENTS` | TEACHER, ADMIN | `exam_id`, `before_id` tùy chọn |
| `ACKNOWLEDGE_EXAM_EVENT` | TEACHER, ADMIN | `exam_id`, `id` của bản ghi |
| `SUBMIT_EXAM` hiện có | STUDENT | `exam_id`, `attempt_id`, `answers` |

Giáo viên chỉ truy cập các đề do mình quản lý. Admin có quyền qua TCP. Tab desktop nằm ở dashboard giáo viên. Cập nhật cả Server và Client sinh viên cùng lúc vì lệnh nộp bài yêu cầu `attempt_id`.

## Các tệp

- Thêm `database/migrations/add_proctoring.sql`, `server/dao/proctoring_dao.py` và `server/service/proctoring_service.py`.
- Thêm `client/request_worker.py`, `client/anti_cheat/focus_monitor.py` và `client/ui/teacher/monitoring_panel.py`.
- Thêm `tests/test_proctoring_client.py`, `tests/test_proctoring_tcp.py` và tài liệu này.
- Sửa `common/protocol.py`, `server/main.py`, `server/client_handler.py`, `server/database.py`, `server/dao/exam_dao.py`, `server/dao/result_dao.py`, `server/service/exam_service.py`.
- Sửa `client/main.py`, `client/network.py`, `client/ui/student/exam_list.py`, `client/ui/student/student_dashboard.py`, `client/ui/student/exam_taking.py`, `client/ui/teacher/teacher_dashboard.py`.

## Kiểm thử và giới hạn

```powershell
py -m unittest discover -s tests -v
$env:QUIZ_TEST_DESKTOP = '1'
$env:QUIZ_TEST_DATABASE = '1'
py -m unittest discover -s tests -v
```

Chế độ desktop cần phiên Tk tương tác. Bài kiểm thử hai giao diện và chuyển sang tiến trình khác dùng Windows. Chế độ database cần quyền tạo schema trên máy chủ cấu hình sẵn. Nó tạo schema riêng có tiền tố `quiz_phase1_test_` và giữ schema để kiểm tra. Bài kiểm thử heartbeat đẩy thời gian heartbeat cuối về quá khứ rồi chờ bộ quét chạy.

Phóng to cửa sổ và focus phụ thuộc Tk, trình quản lý cửa sổ và hệ điều hành. Cảnh báo phản ánh các chuyển đổi Client hoặc Server quan sát được. Giáo viên xem lại các cảnh báo trước khi đánh giá sự việc. Giai đoạn này giám sát trạng thái cửa sổ và kết nối trong lượt thi. Khi tiến trình biến mất, Server ghi nhận qua timeout heartbeat. Sau hạn nộp, heartbeat có thể tiếp tục trong thời gian chờ xác nhận nộp bài. Kết quả chấm điểm độc lập với lịch sử cảnh báo.
