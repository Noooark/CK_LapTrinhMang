# Ảnh bằng chứng camera

## Bật tính năng

Cập nhật Server và hai Client cùng đợt. Dừng Server rồi áp dụng [add_camera_evidence.sql](../database/migrations/add_camera_evidence.sql) **một lần**, sau hai migration giám sát trước đó. Dùng thông tin máy chủ, tài khoản và schema trong cấu hình triển khai.

```powershell
mysql --host=localhost --port=3306 --user=your_user -p --database=quiz_app --execute="SOURCE database/migrations/add_camera_evidence.sql"
```

Migration thêm chính sách theo đề, sự đồng ý theo lượt thi và bảng `proctoring_snapshots`. Bảng chứa khóa tham chiếu tới sự kiện, mã lưu trữ, kích thước và các mốc thời gian. File luôn là JPEG. Các sự kiện cũ không có ảnh. Điểm và đáp án giữ nguyên.

### Server

Dùng chứng chỉ PEM có Subject Alternative Name khớp địa chỉ hoặc tên DNS mà Client dùng. Khóa riêng và thư mục ảnh cần nằm ngoài repository. Trên Windows, cấp quyền đọc khóa và đọc/ghi thư mục ảnh cho tài khoản chạy Server, cùng quyền quản trị theo chính sách của đơn vị. Gỡ các quyền kế thừa dành cho người dùng không có thẩm quyền. Trên Linux/macOS, thư mục ảnh phải có quyền `0700` và do tài khoản Server quản lý.

```powershell
$env:QUIZ_TLS_CERT = 'C:\quiz-private\server-chain.pem'
$env:QUIZ_TLS_KEY = 'C:\quiz-private\server.key'
$env:QUIZ_SNAPSHOT_DIR = 'C:\quiz-private\proctoring_snapshots'
$env:QUIZ_SNAPSHOT_DAYS = '7'
py -m server.main
```

Nếu cấu hình TLS, cổng Server đó chỉ nhận TLS 1.2 trở lên. Thiếu cặp chứng chỉ và khóa làm Server từ chối khởi động. Nếu chạy cấu hình TCP cũ, gửi và lấy ảnh đều bị từ chối. Cấu hình thư mục ảnh là tùy chọn bật tính năng toàn Server. Thời hạn mặc định là 7 ngày, hỗ trợ 1–365 ngày.

### Client giáo viên và học viên

Cấp chứng chỉ CA tin cậy cho từng Client. Chỉ chuyển CA hoặc chuỗi tin cậy, giữ khóa riêng ở Server. Đặt `server_host` trong `config.ini` trùng tên hoặc IP trong SAN của chứng chỉ. Với môi trường thử nghiệm, có thể dùng chứng chỉ riêng cho máy thử và tin cậy chứng chỉ đó một cách rõ ràng. Client kiểm tra chuỗi tin cậy và tên máy, đồng thời dừng kết nối nếu kiểm tra thất bại. [Python SSL](https://docs.python.org/3/library/ssl.html#client-side-operation)

```powershell
$env:QUIZ_TLS_CA = 'C:\quiz-client\trusted-ca.pem'
py -m client.main
```

## Demo hai Client

Trên Windows, nếu cả hai Client và Server chạy cùng máy, có thể dùng script tạo chứng chỉ riêng cho localhost. Chạy MySQL và dừng Server cũ đang dùng cùng cổng trước khi mở Server TLS. Giữ `server_host = 127.0.0.1` và đặt cổng Client trùng cổng Server trong `config.ini`.

```powershell
# Terminal Server. Đổi đường dẫn nếu OpenSSL nằm ở chỗ khác.
.\scripts\start-local-evidence.ps1 -Mode Server -OpenSsl D:\xampp\apache\bin\openssl.exe

# Chạy ở hai terminal Client riêng.
.\scripts\start-local-evidence.ps1 -Mode Client
```

Script dành cho demo cùng máy, lưu chứng chỉ và ảnh dưới `%LOCALAPPDATA%\CK_LapTrinhMang\EvidenceDemo`. Nếu lệnh `py` không khả dụng, truyền thêm `-Python` với đường dẫn đến `python.exe`.

1. Giáo viên tạo đề, bật **Yêu cầu camera khi thi** và **Bắt buộc lưu ảnh bằng chứng**, rồi mở đề.
2. Học viên vào kiểm tra camera. Hộp thoại ghi rõ yêu cầu lưu ảnh, mục đích, thời hạn và quyền xem. Học viên chọn **Đồng ý và bật camera** để chấp nhận điều kiện, điều chỉnh preview rồi bắt đầu thi. Nếu không chấp nhận, chọn **Quay lại** và liên hệ giáo viên. Đề bật yêu cầu lưu ảnh chỉ mở lượt thi khi TLS và thư mục lưu ảnh đã được cấu hình.
3. Tạo cảnh báo **nhiều khuôn mặt**, **không thấy khuôn mặt** hoặc **hình ảnh khó quan sát** đủ ngưỡng của đề. Dòng cảnh báo xuất hiện trước. Biểu tượng 👁 xuất hiện sau khi ảnh đã lưu và Dashboard cập nhật.
4. Giáo viên bấm 👁 để xem JPEG theo đúng tỷ lệ, cùng tên đề, tên học viên, thời gian và loại cảnh báo. Đóng cửa sổ xem ảnh để giải phóng ảnh trên Client.
5. Nộp bài và kiểm tra kết quả. Cảnh báo cũ, mất tín hiệu, phục hồi và các sự kiện thiếu ảnh sẽ không có 👁.

## Luồng ảnh và quyền truy cập

### Cảnh báo điện thoại

Áp dụng `database/migrations/add_camera_phone_detection.sql` sau migration ảnh, rồi khởi động lại Server và Client. Trên mỗi máy học viên, đặt mô hình YOLOX-S ONNX của OpenCV Zoo trong `models/object_detection_yolox_2022nov.onnx` ở thư mục gốc dự án. Hộp kiểm tra camera hiển thị mô hình đã sẵn sàng hay chưa. Các kiểm tra khuôn mặt và ảnh vẫn chạy nếu thiếu mô hình. [OpenCV Zoo YOLOX](https://github.com/opencv/opencv_zoo/tree/main/models/object_detection_yolox)

```powershell
New-Item -ItemType Directory -Force models | Out-Null
$model = 'models/object_detection_yolox_2022nov.onnx'
Invoke-WebRequest 'https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/object_detection_yolox/object_detection_yolox_2022nov.onnx' -OutFile "$model.download"
if ((Get-FileHash "$model.download" -Algorithm SHA256).Hash -ne 'C5C2D13E59AE883E6AF3B45DAEA64AF4833A4951C92D116EC270D9DDBE998063') {
    throw 'Mã kiểm tra SHA-256 của mô hình không khớp.'
}
Move-Item "$model.download" $model -Force
```

Ở màn hình xem trước, đưa điện thoại vào vùng nhìn của camera để kiểm tra dòng **Đã thấy điện thoại trong khung hình xem trước**. Client chỉ tạo cảnh báo và gửi ảnh khi đã vào lượt thi.

Nếu lượt phân tích đầu chưa thấy điện thoại, Client thử cân góc theo các cạnh nổi bật rồi kiểm tra bốn hướng xoay và ảnh phản chiếu. Ảnh bằng chứng vẫn lấy từ khung hình webcam gốc của cảnh báo. Điện thoại chỉ lộ cạnh mỏng hoặc bị che nhiều vẫn có thể bị bỏ sót.

Khi mô hình phát hiện điện thoại qua nhiều khung hình trong ít nhất 2 giây, Client ghi một sự kiện `CAMERA_PHONE_DETECTED` và cảnh báo học viên. Mô hình chấp nhận khoảng bỏ sót ngắn giữa hai lần phát hiện, tối đa 1,5 giây. Với đề yêu cầu lưu ảnh, Client gửi một ảnh của khung hình phát hiện qua luồng ảnh bên dưới. Giữ điện thoại trong khung hình chỉ tạo một cảnh báo cho mỗi đợt. Sau khi không thấy điện thoại ổn định trong ít nhất 1 giây, đợt tiếp theo có thể tạo cảnh báo mới. Giáo viên có thể bấm 👁 để xem ảnh đã lưu.

Mô hình phát hiện điện thoại nhìn thấy trong vùng camera. Khả năng xác nhận hành vi bấm chụp, hướng điện thoại hoặc thiết bị ngoài góc quay nằm ngoài phạm vi của cảnh báo này.

Camera worker chỉ giữ mẫu mới nhất của điều kiện quan sát. Khi cảnh báo vượt ngưỡng, Client lấy tối đa một mẫu mới trong vòng 2 giây. Worker mạng nén JPEG ở chất lượng 75 rồi giảm xuống 55 hoặc 35 nếu cần. Kích thước tối đa là 640 × 480 và 200 KiB sau nén. Client lưu sự kiện bằng `REPORT_EXAM_EVENT` trước, rồi mới gửi ảnh. Mỗi lượt giữ tối đa bốn ảnh đang chờ hoặc đang gửi. Ảnh chờ quá 30 giây sẽ được bỏ qua. Nếu mất mạng, không có frame hoặc ảnh không đạt giới hạn, lịch sử sự kiện vẫn giữ lại. Upload thử lại tối đa một lần với UUID cũ.

- `UPLOAD_EXAM_SNAPSHOT` dành cho STUDENT sở hữu lượt thi, có đồng ý và sự kiện camera phù hợp. Server kiểm tra Base64, định dạng và kích thước JPEG, sau đó chuẩn hóa ảnh để bỏ metadata gắn trong file. Server giới hạn một ảnh cho mỗi sự kiện.
- `GET_EXAM_SNAPSHOT` chỉ dành cho giáo viên phụ trách đề hoặc ADMIN. Server tra quyền qua sự kiện và lượt thi. Dashboard chỉ lấy JPEG khi bấm 👁. Lịch sử chỉ trả `has_snapshot` và metadata.
- Ảnh lưu trong `QUIZ_SNAPSHOT_DIR` với tên UUID do Server sinh. Server ghi file tạm và đổi tên nguyên tử trước khi ghi metadata. Mốc ảnh hiển thị là thời điểm nhận cảnh báo theo cơ sở dữ liệu, còn hạn lưu tính từ lúc Server lưu ảnh.
- Cơ chế dọn ảnh chạy khi mở Server và mỗi 5 phút. Hết hạn là ảnh bị chặn truy cập ngay, sau đó file và metadata được dọn. Lịch sử cảnh báo vẫn tồn tại. File mồ côi từ thao tác gián đoạn hoặc xóa đề được dọn sau ít nhất một giờ.

Chạy dọn thủ công với cùng `QUIZ_SNAPSHOT_DIR` và cấu hình database của Server.

```powershell
py -m server.service.snapshot_service
```

## Kiểm thử và giới hạn

```powershell
py -m unittest discover -s tests -v
$env:QUIZ_TEST_DESKTOP = '1'
$env:QUIZ_TEST_DATABASE = '1'
py -m unittest discover -s tests -v
```

Bài test TLS tích hợp yêu cầu `QUIZ_TLS_CERT`, `QUIZ_TLS_KEY` và `QUIZ_TLS_CA` cho chứng chỉ kiểm thử có SAN `127.0.0.1` và không có `localhost`. Bộ test database tạo schema riêng. Chỉ chạy cấu hình này trên máy kiểm thử với quyền phù hợp. Webcam thật cần kiểm thử riêng với người đồng ý tham gia. Camera có thể đếm sai trong ánh sáng yếu hoặc góc mặt khó quan sát. Ảnh chỉ cung cấp ngữ cảnh cho giáo viên xem xét.

## Tệp

- Thêm `common/snapshots.py`, `client/anti_cheat/camera_snapshot.py`, `server/service/snapshot_service.py`, migration ảnh và tài liệu này.
- Sửa luồng mạng và hàng đợi Client, CameraMonitor, hộp kiểm tra camera, màn hình thi, màn hình tạo đề và Dashboard giám sát. Sửa định tuyến TCP, vòng đời Server, lưu cấu hình đề, lưu sự đồng ý và truy vấn lịch sử.
- Cập nhật kiểm thử CameraMonitor/Tk và TCP, cùng `.gitignore` cho thư mục ảnh cục bộ và khóa TLS.
