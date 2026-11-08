import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
import os

OUT_PATH = "/home/khoile/Documents/QuizApp/chuong2_phantich_thietke.docx"
FIG_DIR = "/home/khoile/Documents/QuizApp/figures"

doc = docx.Document()

# Setup standard A4 margins (top: 2cm, bottom: 2cm, left: 3cm, right: 2cm)
for section in doc.sections:
    section.top_margin = Inches(0.79)     # 2 cm
    section.bottom_margin = Inches(0.79)  # 2 cm
    section.left_margin = Inches(1.18)    # 3 cm
    section.right_margin = Inches(0.79)   # 2 cm

# Configure Default Normal Style
normal_style = doc.styles['Normal']
normal_style.font.name = 'Times New Roman'
normal_style.font.size = Pt(13)
normal_style.font.color.rgb = RGBColor(0, 0, 0)
normal_style.paragraph_format.line_spacing = 1.3
normal_style.paragraph_format.space_after = Pt(6)

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def add_h1(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.keep_with_next = True
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.font.name = 'Times New Roman'
    run.font.size = Pt(16)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0, 51, 102)
    return p

def add_h2(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.font.name = 'Times New Roman'
    run.font.size = Pt(14)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0, 51, 102)
    return p

def add_h3(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.font.name = 'Times New Roman'
    run.font.size = Pt(13)
    run.font.bold = True
    run.font.color.rgb = RGBColor(30, 30, 30)
    return p

def add_p(text, bold_prefix="", indent=0.3):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if indent > 0:
        p.paragraph_format.first_line_indent = Inches(indent)
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.font.name = 'Times New Roman'
        r_pre.font.size = Pt(13)
        r_pre.font.bold = True
    run = p.add_run(text)
    run.font.name = 'Times New Roman'
    run.font.size = Pt(13)
    return p

def add_bullet(text, bold_prefix=""):
    p = doc.add_paragraph(style='List Bullet')
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(3)
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.font.name = 'Times New Roman'
        r_pre.font.size = Pt(13)
        r_pre.font.bold = True
    run = p.add_run(text)
    run.font.name = 'Times New Roman'
    run.font.size = Pt(13)
    return p

def add_image_figure(img_rel_path, caption, width_inch=5.5):
    img_full_path = os.path.join(FIG_DIR, img_rel_path)
    if os.path.exists(img_full_path):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(6)
        p_img.paragraph_format.space_after = Pt(2)
        run = p_img.add_run()
        run.add_picture(img_full_path, width=Inches(width_inch))

        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap.paragraph_format.space_before = Pt(2)
        p_cap.paragraph_format.space_after = Pt(8)
        run_cap = p_cap.add_run(caption)
        run_cap.font.name = 'Times New Roman'
        run_cap.font.size = Pt(11)
        run_cap.font.italic = True
        run_cap.font.bold = True

def add_code_block(code_text, caption=""):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    set_cell_background(cell, "F4F6F9")
    set_cell_margins(cell, top=140, bottom=140, left=200, right=200)

    p = cell.paragraphs[0]
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(0)
    run = p.add_run(code_text)
    run.font.name = 'Courier New'
    run.font.size = Pt(9.5)
    run.font.color.rgb = RGBColor(33, 37, 41)

    if caption:
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap.paragraph_format.space_before = Pt(3)
        p_cap.paragraph_format.space_after = Pt(8)
        run_cap = p_cap.add_run(caption)
        run_cap.font.name = 'Times New Roman'
        run_cap.font.size = Pt(11)
        run_cap.font.italic = True
        run_cap.font.bold = True

print("Building Chapter 2 with new section 2.1...")

# CHAPTER TITLE
add_h1("CHƯƠNG 2: PHÂN TÍCH VÀ THIẾT KẾ HỆ THỐNG")

# 2.1 NEW SECTION REQUESTED BY USER
add_h2("2.1. Tổng quan kiến trúc mạng, giao thức, topology và các chức năng trọng tâm của dự án")
add_p("Trước khi đi sâu vào phân tích chi tiết cơ chế socket và các thuật toán triển khai, mục này trình bày tổng quan mang tính định hướng về kiến trúc mô hình, danh mục giao thức, cấu trúc liên kết mạng (topology) và các tính năng nghiệp vụ đặc biệt quan trọng được hiện thực hóa trong hệ thống thi trắc nghiệm trực tuyến QuizApp.")

add_h3("2.1.1. Mô hình kiến trúc ứng dụng mạng")
add_p("Dự án QuizApp lựa chọn mô hình Client–Server tập trung (Centralized Client-Server Model) kết hợp kiến trúc phân tầng 3 lớp (3-Tier Architecture):")
add_bullet("Ứng dụng đồ họa máy trạm (Desktop Client) được xây dựng bằng Python và CustomTkinter, phụ trách giao tiếp với người dùng và gửi nhận yêu cầu qua mạng.", "• Tầng 1 - Trình diễn (Presentation Tier / Client): ")
add_bullet("Máy chủ mạng TCP Socket đa luồng (QuizServer) viết bằng Python thuần, chạy thường trực tại cổng 9999 để phân giải gói tin, kiểm tra tính hợp lệ của Token phiên, phân quyền người dùng và thực thi các logic nghiệp vụ khảo thí.", "• Tầng 2 - Xử lý nghiệp vụ (Application / Server Tier): ")
add_bullet("Cơ sở dữ liệu quan hệ MySQL Server 8.0 đóng gói trong Docker Container tại cổng 3306, lưu trữ bền vững thông tin tài khoản, ngân hàng câu hỏi, đề thi và lịch sử kết quả thi.", "• Tầng 3 - Dữ liệu bền vững (Data Storage Tier): ")
add_p("Lý do lựa chọn mô hình Client–Server tập trung thay vì mô hình ngang hàng (P2P): Trong bài toán khảo thí trực tuyến, tính toàn vẹn dữ liệu, chống gian lận và kiểm soát điểm số đòi hỏi một máy chủ có thẩm quyền tối cao (Authoritative Server). Máy chủ là nơi duy nhất lưu giữ đáp án chuẩn, có quyền khởi động hoặc kết thúc ca thi, tự động tính điểm độc lập và lưu trữ kết quả an toàn. Mô hình P2P hoàn toàn không phù hợp cho thi cử vì thiếu cơ chế kiểm soát gian lận tập trung.")

add_h3("2.1.2. Danh mục các giao thức mạng được áp dụng")
add_p("Hệ thống QuizApp kết hợp hài hòa các giao thức mạng chuẩn quốc tế và giao thức tầng ứng dụng tự định nghĩa:")
add_bullet("Hoạt động tại cổng TCP 9999, cung cấp kênh truyền hai chiều tin cậy (Full-Duplex Stream), đảm bảo các gói tin đề thi và bài nộp đến đích chính xác 100%, không bị mất mát hay đảo lộn thứ tự.", "• Giao thức TCP Socket (Tầng Transport): ")
add_bullet("Đóng gói dữ liệu dạng JSON kết hợp tiêu đề 4 byte Big-Endian biểu thị độ dài (Length-Prefix Framing). Cơ chế này giải quyết triệt để vấn đề phân mảnh gói tin và dính gói (Sticky Packets) vốn là đặc thù phức tạp của luồng byte TCP.", "• Giao thức tầng ứng dụng tùy biến (Custom Application Protocol): ")
add_bullet("Băm mật khẩu người dùng bằng thuật toán Bcrypt một chiều kèm muối ngẫu nhiên (Salt), kết hợp cấp phát thẻ phiên ngẫu nhiên UUIDv4 Token lưu trên bộ nhớ RAM máy chủ để kiểm soát quyền hạn (RBAC) trên từng yêu cầu.", "• Giao thức bảo mật xác thực và quản lý phiên: ")
add_bullet("Giao thức kết nối CSDL chuẩn cổng 3306 với cơ chế Prepared Statements, bảo vệ an toàn hệ thống trước các nguy cơ tấn công SQL Injection.", "• Giao thức PyMySQL kết nối CSDL: ")

add_h3("2.1.3. Cấu trúc liên kết mạng (Network Topology)")
add_p("Hệ thống QuizApp được thiết kế để vận hành tối ưu trên cấu trúc liên kết mạng Topology hình sao (Star Topology):")
add_bullet("Máy chủ QuizServer đóng vai trò là nút trung tâm (Central Hub Node), kiểm soát toàn bộ lưu lượng vào/ra và điều phối hoạt động của hệ thống.", "• Nút trung tâm (Hub Node): ")
add_bullet("Các máy trạm Client đại diện cho các vai trò khác nhau trong hệ thống (Máy Admin, Máy Giảng viên, Máy Sinh viên 1, Sinh viên 2, ..., Sinh viên N) kết nối trực tiếp về máy chủ trung tâm qua giao thức TCP.", "• Các nút nhánh (Leaf Nodes): ")
add_bullet("Mọi luồng dữ liệu chỉ truyền giữa Client và Server; hoàn toàn không có bất kỳ kênh kết nối trực tiếp nào giữa các máy sinh viên với nhau. Điều này ngăn chặn triệt để hành vi sinh viên can thiệp, gửi bài giải hoặc làm nghẽn kết nối của thí sinh khác trong phòng thi.", "• Đặc trưng an ninh mạng quan trọng: ")

add_image_figure("fig_2_0_star_topology.png", "Hình 2.1: Sơ đồ cấu trúc liên kết mạng Topology hình sao (Star Topology) trong hệ thống QuizApp", width_inch=5.5)

add_h3("2.1.4. Một vài chức năng đặc biệt quan trọng của hệ thống")
add_p("Hệ thống QuizApp được thiết kế với nhiều tính năng kỹ thuật và nghiệp vụ chuyên sâu, nổi bật gồm:")
add_bullet("Khi sinh viên yêu cầu nạp đề thi (lệnh GET_EXAM_QUESTIONS), máy chủ chủ động bóc tách và loại bỏ trường đáp án đúng (correct_answer) trước khi đóng gói gửi qua mạng. Ngay cả khi sinh viên dùng phần mềm bắt gói tin (Packet Sniffer / Wireshark) cũng hoàn toàn không thể tìm thấy đáp án trước khi nộp bài.", "1. Cơ chế phòng thi an toàn và chống gian lận mạng: ")
add_bullet("Giao diện phòng thi tích hợp đồng hồ đếm ngược đồng bộ từng giây. Khi thời gian thi kết thúc (00:00), hệ thống tự động khóa toàn bộ thao tác của thí sinh và phát lệnh nộp bài cưỡng chế (Auto-Submit) về Server.", "2. Đồng hồ đếm ngược thời gian thực và Tự động thu bài: ")
add_bullet("Toàn bộ quy trình so khớp câu trả lời và tính điểm được thực hiện tự động tại máy chủ theo thang điểm 10, ghi nhận tức thời vào cơ sở dữ liệu và phản hồi kết quả cho thí sinh trong tích tắc (< 100ms).", "3. Chấm điểm tự động tức thì trên máy chủ: ")
add_bullet("Bộ phân tích cú pháp thông minh (Regex Parser) tự động nhận diện định dạng đề thi tiếng Việt, phân tách câu hỏi, các lựa chọn A, B, C, D, đáp án đúng (ký hiệu * hoặc [A]) và mức độ khó (DỄ, TRUNG BÌNH, KHÓ). Giảng viên có thể nạp hàng trăm câu hỏi chỉ bằng một cú nhấp chuột.", "4. Nạp câu hỏi và đề thi hàng loạt từ tệp Word (.docx) và Text (.txt): ")
add_bullet("Tái cấu trúc ngân hàng câu hỏi phân lập độc lập theo từng môn học; tích hợp cửa sổ xem đề thi trực quan với đáp án đúng được làm nổi bật màu xanh lá và hỗ trợ xuất đề thi ra file Microsoft Word (.docx) phục vụ lưu trữ học vụ.", "5. Quản lý Ngân hàng câu hỏi phân lập theo môn & Xuất Word: ")

# 2.2
add_h2("2.2. Mô hình Client–Server và giao thức TCP")
add_p("Mô hình Client–Server là kiến trúc phân tán kinh điển và phổ biến bậc nhất trong các hệ thống mạng máy tính hiện nay. Trong mô hình này, hệ thống được phân định rõ ràng thành hai vai trò độc lập: phía khách (Client) là thực thể chủ động gửi các yêu cầu dịch vụ (Service Requests), và máy chủ (Server) là thực thể thụ động lắng nghe, tiếp nhận, thực thi các thuật toán nghiệp vụ và phản hồi kết quả về cho các Client. Máy chủ đóng vai trò hạt nhân trung tâm, chịu trách nhiệm quản lý kết nối đồng thời từ nhiều người dùng, kiểm soát an toàn dữ liệu và điều phối các phiên làm việc.")

add_p("Hoạt động trao đổi dữ liệu trong mô hình Client–Server được xây dựng trên nền tảng bộ giao thức TCP/IP chuẩn quốc tế. Tại tầng giao vận (Transport Layer), giao thức TCP (Transmission Control Protocol) là sự lựa chọn cốt lõi và tối ưu nhất đối với các ứng dụng đòi hỏi tính toàn vẹn và độ tin cậy tuyệt đối, trong đó có hệ thống thi trắc nghiệm trực tuyến QuizApp.")

add_p("Giao thức TCP sở hữu những đặc tính kỹ thuật cơ bản và mang tính quyết định sau:")

add_bullet(" Trước khi bất kỳ byte dữ liệu nào được truyền tải, hai bên Client và Server bắt buộc phải thiết lập một kênh truyền thông logic thông qua quá trình bắt tay 3 bước (Three-way Handshake). Quá trình này đảm bảo cả hai thiết bị đều sẵn sàng gửi nhận và đã đồng bộ hóa số thứ tự gói tin (Sequence Number).", "• Hướng kết nối (Connection-oriented):")

add_image_figure("fig_2_1_handshake.png", "Hình 2.2: Quá trình bắt tay 3 bước trong giao thức TCP", width_inch=4.8)

add_bullet(" TCP sử dụng cơ chế số thứ tự (Sequence Numbers), gói tin xác nhận nhận đủ (Acknowledgment - ACK) và cơ chế phát hiện lỗi thông qua Checksum. Khi một bên gửi gói tin, bên nhận phải gửi trả ACK tương ứng. Nếu quá một khoảng thời gian chờ (Timeout) mà bên gửi chưa nhận được ACK, gói tin sẽ được tự động truyền lại (Retransmission). Cơ chế này đảm bảo dữ liệu không bao giờ bị mất mát, không bị nhân đôi và đến đích theo đúng thứ tự ban đầu.", "• Đảm bảo độ tin cậy tuyệt đối (Reliability):")

add_bullet(" Khác với giao thức UDP truyền theo từng gói tin độc lập (Datagram), TCP coi dữ liệu truyền tải là một dòng các byte liên tục không phân ranh giới tự nhiên. Dữ liệu từ ứng dụng được ghi vào bộ đệm của socket và được chia thành các phân đoạn (Segments) phù hợp với kích thước gói tối đa (MSS - Maximum Segment Size) để truyền qua mạng.", "• Truyền dữ liệu dạng luồng byte (Byte-stream):")

add_image_figure("fig_2_2_byte_stream.png", "Hình 2.3: Minh họa việc truyền dữ liệu dạng luồng bởi giao thức TCP", width_inch=5.2)

add_bullet(" TCP tích hợp các thuật toán điều khiển luồng (Flow Control) thông qua cơ chế cửa sổ trượt (Sliding Window) để ngăn máy gửi làm tràn bộ đệm máy nhận, đồng thời áp dụng các thuật toán điều khiển tắc nghẽn (Congestion Control như Slow Start, Congestion Avoidance, Fast Retransmit) giúp mạng hoạt động ổn định trên nhiều hạ tầng kết nối khác nhau.", "• Kiểm soát tắc nghẽn và lưu lượng mạng:")

# 2.3
add_h2("2.3. Socket và cơ chế giao tiếp trong TCP/IP")
add_p("Socket là khái niệm trung tâm trong lập trình mạng, đóng vai trò là điểm cuối giao tiếp (Communication Endpoint) giữa chương trình ứng dụng và ngăn xếp giao thức mạng của hệ điều hành. Khi một ứng dụng muốn truyền tải hoặc nhận dữ liệu qua mạng Internet, Socket hoạt động như một cánh cửa kết nối trung gian: ứng dụng chỉ cần thực hiện các thao tác đọc/ghi dữ liệu lên Socket mà không cần quan tâm đến chi tiết phức tạp của tầng dưới như phân đoạn gói tin, đánh số thứ tự, định tuyến IP hay tính toán checksum.")

add_image_figure("fig_2_3_socket_layer.png", "Hình 2.4: Mô tả Socket trong mô hình phân tầng TCP/IP", width_inch=4.8)

add_p("Một Socket TCP trong mạng được định danh duy nhất bởi bộ ba thành phần cơ bản:")
add_bullet("Xác định máy tính hoặc giao diện mạng trên hệ thống Internet.", "1. Địa chỉ IP (IP Address): ")
add_bullet("Xác định tiến trình ứng dụng cụ thể đang chạy trên máy tính đó (Ví dụ: Cổng 9999 dành cho QuizServer).", "2. Số hiệu cổng (Port Number): ")
add_bullet("Chỉ định phương thức giao vận ở tầng Transport (giao thức TCP trong dự án).", "3. Giao thức vận chuyển (Protocol): ")

add_p("Khi một Socket tại Client kết nối thành công với Socket tại Server, một kênh kết nối ảo hai chiều (Full-Duplex Virtual Circuit) được hình thành. Kênh này cho phép cả hai bên có thể gửi và nhận dữ liệu độc lập, song song và liên tục như thao tác với các luồng vào/ra (I/O Streams) cục bộ trên máy tính.")

add_image_figure("fig_2_4_socket_channel.png", "Hình 2.5: Socket trong mô hình ứng dụng Client-Server", width_inch=5.5)

add_p("Trong lập trình mạng TCP/IP, có hai loại Socket chính:")
add_bullet("Hoạt động trên giao thức TCP, yêu cầu thiết lập kết nối trước khi truyền, đảm bảo độ tin cậy tuyệt đối, thứ tự gói tin và không mất dữ liệu. Đây là loại Socket bắt buộc được ứng dụng trong đề tài QuizApp nhằm đảm bảo tính chính xác của đề thi và bài làm.", "• Stream Socket (SOCK_STREAM): ")
add_bullet("Hoạt động trên giao thức UDP, truyền dữ liệu không hướng kết nối, tốc độ nhanh nhưng không cam kết độ tin cậy. Thường chỉ ứng dụng trong các dịch vụ truyền trực tiếp video/audio hoặc trò chơi trực tuyến thời gian thực.", "• Datagram Socket (SOCK_DGRAM): ")

# 2.4
add_h2("2.4. Quy trình xây dựng ứng dụng Client–Server TCP")
add_p("Quy trình xây dựng một hệ thống mạng Client–Server dựa trên giao thức TCP tuân theo mô hình chuẩn của Socket API, bao gồm một chuỗi các bước tuần tự được thực hiện chặt chẽ tại cả hai phía máy chủ và máy khách.")

add_h3("a) Quy trình phía Server")
add_p("Máy chủ là thực thể thụ động, phải được khởi chạy trước và duy trì trạng thái lắng nghe thường trực để đón nhận các yêu cầu kết nối từ các Client:")
add_bullet("Khởi tạo điểm cuối giao tiếp hỗ trợ họ địa chỉ IPv4 (AF_INET) và kiểu Stream Socket (SOCK_STREAM).", "• Bước 1 - Tạo Socket TCP: ")
add_bullet("Liên kết Socket máy chủ với một địa chỉ IP (như 0.0.0.0 để lắng nghe trên tất cả card mạng) và số hiệu cổng xác định (Port 9999).", "• Bước 2 - Gán cổng (bind): ")
add_bullet("Chuyển Socket sang trạng thái thụ động chờ kết nối, thiết lập hàng đợi kết nối (Backlog queue, ví dụ tối đa 50 kết nối đồng thời).", "• Bước 3 - Lắng nghe (listen): ")
add_bullet("Khi có yêu cầu từ Client trong hàng đợi, hệ thống chấp nhận kết nối và tự động cấp phát một Socket mới (Client Socket) chuyên trách phục vụ riêng cho Client đó, giải phóng Socket chính để tiếp tục lắng nghe.", "• Bước 4 - Chấp nhận kết nối (accept): ")
add_bullet("Thực hiện truyền và nhận các gói tin nghiệp vụ qua luồng kết nối TCP đã được thiết lập an toàn.", "• Bước 5 - Trao đổi dữ liệu: ")
add_bullet("Giải phóng Socket con khi phiên làm việc của Client hoàn tất.", "• Bước 6 - Đóng kết nối (close): ")

add_image_figure("fig_2_5_server_algo.png", "Hình 2.6: Thuật toán xây dựng chương trình Server TCP", width_inch=3.8)

add_h3("b) Quy trình phía Client")
add_p("Máy khách là thực thể chủ động kết nối khi có nhu cầu sử dụng dịch vụ:")
add_bullet("Khởi tạo Socket TCP tương ứng phía Client.", "• Bước 1 - Tạo Socket TCP: ")
add_bullet("Chủ động phát lệnh kết nối tới máy chủ thông qua cặp thông số địa chỉ IP và số hiệu cổng đã biết của Server.", "• Bước 2 - Yêu cầu kết nối (connect): ")
add_bullet("Sau khi bắt tay 3 bước thành công, Client gửi yêu cầu (Request) và nhận phản hồi (Response) từ máy chủ.", "• Bước 3 - Trao đổi dữ liệu: ")
add_bullet("Gửi thông báo kết thúc phiên làm việc và đóng Socket để giải phóng tài nguyên hệ điều hành.", "• Bước 4 - Đóng kết nối (close): ")

add_image_figure("fig_2_6_client_algo.png", "Hình 2.7: Thuật toán xây dựng chương trình Client TCP", width_inch=3.8)

add_h3("c) Mô hình tương tác tổng quát Client–Server")
add_p("Sơ đồ dưới đây minh họa toàn bộ quá trình phối hợp nhịp nhàng giữa Client và Server: Server khởi động và chờ tại accept(); Client khởi động và phát lệnh connect(); kênh truyền ảo TCP được hình thành; hai bên liên tục trao đổi các thông điệp nghiệp vụ; cuối cùng phiên làm việc được đóng lại một cách an toàn.")

add_image_figure("fig_2_7_general_algo.png", "Hình 2.8: Thuật toán xây dựng ứng dụng Client-Server tổng quát", width_inch=5.2)

# 2.5
add_h2("2.5. Triển khai xây dựng chương trình Client–Server")
add_p("Trong quá trình hiện thực hóa ứng dụng mạng, việc truyền và nhận thông tin qua Socket được quản lý thông qua hai luồng dữ liệu độc lập: Luồng nhập (InputStream) để đọc dữ liệu và Luồng xuất (OutputStream) để ghi dữ liệu. Cả hai luồng này đều được gắn chặt với Socket đã kết nối.")

add_h3("2.5.1. Quy trình triển khai phía Server")
add_p("Phía Server quản lý kênh giao tiếp với từng Client thông qua Socket con do hàm accept() trả về. Dữ liệu từ phía mạng chuyển vào bộ đệm của Socket sẽ được Server đọc ra thông qua InputStream, trong khi dữ liệu phản hồi được Server ghi vào OutputStream để tầng TCP chuyển qua mạng đến máy khách.")

add_image_figure("fig_2_8_server_streams.png", "Hình 2.9: Chương trình Server gửi nhận dữ liệu nhờ vào các luồng dữ liệu", width_inch=5.5)

add_h3("2.5.2. Quy trình triển khai phía Client")
add_p("Tương tự phía Server, Client thực hiện đóng gói yêu cầu thành chuỗi byte và đẩy vào OutputStream. Dữ liệu phản hồi từ máy chủ sẽ được đón nhận qua InputStream. Nhờ tính chất truyền theo luồng liên tục (Stream) của TCP, Client có thể trao đổi nhiều câu hỏi, đề thi và bài nộp với cấu trúc dữ liệu phong phú.")

add_image_figure("fig_2_9_client_streams.png", "Hình 2.10: Chương trình Client gửi nhận dữ liệu với chương trình Server", width_inch=5.5)

add_h3("2.5.3. Kiến trúc Server đa tuyến (Multi-threaded Server)")
add_p("Trong mô hình Server đơn tuyến (Single-threaded), chương trình Server chỉ sở hữu duy nhất một luồng thực thi và chỉ có khả năng phục vụ một Client tại một thời điểm. Khi một Client kết nối và trao đổi dữ liệu (ví dụ sinh viên đang làm bài thi kéo dài 45 phút), luồng chính của Server hoàn toàn bị chiếm dụng (blocking). Mọi Client khác muốn đăng nhập hoặc nộp bài đều phải chờ đợi trong vô vọng. Hạn chế nghiêm trọng này làm cho mô hình đơn tuyến không thể ứng dụng trong các môi trường khảo thí thực tế.")

add_p("Để giải quyết triệt để vấn đề này, QuizServer bắt buộc phải được thiết kế và triển khai theo kiến trúc đa tuyến (Multi-threaded Server Architecture). Khi có một Client gửi yêu cầu kết nối đến, vòng lặp chính của Server lập tức khởi tạo một tiểu trình riêng (Worker Thread - ClientHandler) dành riêng cho Client đó. Mỗi Thread sẽ quản lý một Socket độc lập với luồng InputStream và OutputStream riêng biệt.")

add_image_figure("fig_2_10_multithread_overview.png", "Hình 2.11: Minh họa Server đa tuyến phục vụ đồng thời nhiều Client", width_inch=5.5)

add_image_figure("fig_2_11_multithread_detail.png", "Hình 2.12: Mô hình chi tiết Server đa tuyến với socket và luồng riêng biệt", width_inch=5.8)

add_p("Ưu điểm nổi bật của kiến trúc Server đa tuyến:")
add_bullet("Hàng chục, hàng trăm sinh viên và giảng viên có thể tương tác đồng thời mà không bị nghẽn mạng.", "• Khả năng phục vụ đồng thời (High Concurrency): ")
add_bullet("Sự cố phát sinh trên một Client (mất mạng đột ngột, đóng ứng dụng bất thường) chỉ ảnh hưởng đến Thread đó và được dọn dẹp sạch sẽ, hoàn toàn không làm gián đoạn máy chủ hay các thí sinh khác.", "• Cô lập lỗi và an toàn hệ thống (Fault Isolation): ")
add_bullet("Tận dụng triệt để năng lực tính toán của các bộ vi xử lý đa nhân hiện đại (Multi-core CPUs) để xử lý song song các tác vụ mã hóa, kiểm tra đáp án và ghi nhận kết quả thi.", "• Tối ưu hiệu năng phần cứng: ")

# 2.6
add_h2("2.6. Ứng dụng mô hình mạng và giao thức vào dự án QuizApp")

add_h3("2.6.1. Mô hình mạng tổng thể của hệ thống")
add_p("Hệ thống QuizApp được thiết kế theo kiến trúc 3 tầng (3-Tier Architecture) hoàn chỉnh, phân định rõ ràng ranh giới giữa tầng hiển thị, tầng điều phối xử lý mạng và tầng lưu trữ dữ liệu bền vững:")

add_bullet("Ứng dụng đồ họa máy trạm phát triển trên nền tảng Python CustomTkinter hiện đại. Client chịu trách nhiệm quản lý giao diện người dùng, đồng hồ đếm ngược thời gian thực, bảng điều hướng câu hỏi và duy trì kết nối mạng thông qua lớp ServerConnection chuyên biệt.", "1. Tầng máy khách (Client Presentation Tier): ")

add_bullet("Máy chủ mạng TCP Socket đa luồng (QuizServer) lắng nghe tại cổng TCP 9999. Tầng này điều phối các tiến trình ClientHandler, kiểm tra tính hợp lệ của Token phiên, phân quyền bảo mật theo vai trò (RBAC), tiếp nhận và thực thi 28 mã lệnh nghiệp vụ (Command Routing) và kiểm soát logic thi trắc nghiệm.", "2. Tầng máy chủ nghiệp vụ (Server Logic Tier): ")

add_bullet("Hệ quản trị cơ sở dữ liệu quan hệ MySQL Server 8.0 được đóng gói triển khai trong Docker Container tại cổng 3306. Cơ sở dữ liệu lưu trữ 7 bảng dữ liệu quan hệ với bộ mã chuẩn utf8mb4, bảo đảm tính toàn vẹn và giao dịch ACID cho các thao tác nạp đề và ghi nhận bài nộp.", "3. Tầng cơ sở dữ liệu (Database Tier): ")

add_image_figure("fig_2_12_quizapp_architecture.png", "Hình 2.13: Mô hình kiến trúc mạng tổng thể 3 tầng của hệ thống QuizApp", width_inch=5.8)

add_h3("2.6.2. Các giao thức mạng và cơ chế được áp dụng")
add_p("Bảng tổng hợp dưới đây trình bày toàn bộ các giao thức mạng và giải pháp kỹ thuật cốt lõi được áp dụng trong quá trình xây dựng hệ thống QuizApp:")

# Table of protocols
table = doc.add_table(rows=6, cols=3)
table.alignment = WD_TABLE_ALIGNMENT.CENTER
headers = ["Tên giao thức / Cơ chế", "Tầng áp dụng", "Chức năng chính trong QuizApp"]
row_hdr = table.rows[0]
for idx, text in enumerate(headers):
    cell = row_hdr.cells[idx]
    set_cell_background(cell, "003366")
    set_cell_margins(cell, 120, 120, 150, 150)
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.font.name = 'Times New Roman'
    run.font.size = Pt(11)
    run.font.bold = True
    run.font.color.rgb = RGBColor(255, 255, 255)

data = [
    ("TCP Socket (Stream)", "Transport Layer (Cổng 9999)", "Thiết lập kênh truyền thông 2 chiều tin cậy 100%, chống mất gói tin, đảm bảo an toàn tuyệt đối cho đề thi và bài thi nộp."),
    ("Framing Protocol (JSON + 4-byte Prefix)", "Application Layer (Tùy biến)", "Đóng gói thông điệp với tiêu đề 4 byte Big-Endian biểu thị độ dài; giải quyết triệt để lỗi dính gói (Sticky Packets) và phân mảnh luồng TCP."),
    ("Bcrypt Hashing Algorithm", "Security / Application Layer", "Mã hóa băm mật khẩu một chiều kết hợp muối ngẫu nhiên (Salt); ngăn chặn tấn công từ điển và bảo vệ dữ liệu người dùng trong CSDL."),
    ("Session Token (UUIDv4)", "Session / Security Management", "Cấp phát thẻ phiên định danh duy nhất ngẫu nhiên lưu tạm trên RAM máy chủ để xác thực quyền hạn (Admin, Teacher, Student) trên từng gói tin."),
    ("PyMySQL Protocol", "Database Transport (Cổng 3306)", "Kết nối Socket TCP an toàn giữa QuizServer và cơ sở dữ liệu MySQL Container bằng cơ chế Prepared Statements chống tấn công SQL Injection.")
]

for row_idx, (col0, col1, col2) in enumerate(data, 1):
    row = table.rows[row_idx]
    bg = "F9FAFC" if row_idx % 2 == 1 else "FFFFFF"
    for col_i, text in enumerate([col0, col1, col2]):
        cell = row.cells[col_i]
        set_cell_background(cell, bg)
        set_cell_margins(cell, 100, 100, 140, 140)
        p = cell.paragraphs[0]
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(10.5)

add_p("", indent=0)

# 2.6.2.1
add_h3("2.6.2.1. Cơ chế đóng gói và giải khung phân mảnh dữ liệu (Framing Protocol)")
add_p("Trong môi trường mạng TCP, dữ liệu được truyền tải dưới dạng luồng byte liên tục (Stream-oriented). Do cơ chế tối ưu hóa của thuật toán Nagle và các tầng đệm mạng, hiện tượng dính gói (Sticky Packets - nhiều thông điệp gộp thành một gói nhận) hoặc phân mảnh gói (Packet Fragmentation - một thông điệp bị xé nhỏ thành nhiều phần) thường xuyên xảy ra. Nếu chỉ sử dụng hàm recv(1024) đơn giản, hệ thống chắc chắn sẽ bị sập hoặc giải mã JSON thất bại khi gửi đề thi lớn chứa nhiều câu hỏi.")

add_p("Để giải quyết triệt để vấn đề này, nhóm đã thiết kế giao thức đóng gói tùy biến sử dụng cơ chế Tiêu đề độ dài cố định 4 byte (4-Byte Big-Endian Length-Prefix Framing) trong module common/protocol.py:")
add_bullet("Trước khi gửi, chuỗi JSON được mã hóa sang mảng byte UTF-8. Nhóm sử dụng hàm struct.pack('>I', len(raw_data)) để tạo ra đúng 4 byte tiêu đề biểu diễn độ dài chính xác của gói tin theo chuẩn mạng Big-Endian, sau đó gửi đồng thời tiêu đề và nội dung qua hàm sendall().", "• Đóng gói khi gửi (send_message): ")
add_bullet("Bên nhận trước tiên đọc chính xác 4 byte tiêu đề thông qua hàm hỗ trợ _recvall(sock, 4). Sau đó giải mã ra độ dài N bằng struct.unpack('>I', header)[0]. Tiếp tục gọi _recvall(sock, N) để đọc đủ N byte của phần thân (Payload) và tiến hành nạp cấu trúc JSON. Nếu mạng bị phân mảnh, vòng lặp _recvall sẽ tiếp tục nhận từng đoạn byte cho đến khi đủ chiều dài N.", "• Tiếp nhận và ráp khung (receive_message & _recvall): ")

code_protocol = """# common/protocol.py
import json, struct, socket

def _recvall(sock: socket.socket, n: int) -> bytes | None:
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return bytes(data)

def send_message(sock: socket.socket, obj: any) -> bool:
    payload_dict = obj.to_dict() if hasattr(obj, "to_dict") else obj
    raw_data = json.dumps(payload_dict, ensure_ascii=False).encode("utf-8")
    header = struct.pack(">I", len(raw_data))  # 4 byte big-endian
    sock.sendall(header + raw_data)
    return True

def receive_message(sock: socket.socket) -> dict | None:
    header = _recvall(sock, 4)
    if not header or len(header) < 4:
        return None
    length = struct.unpack(">I", header)[0]
    payload = _recvall(sock, length)
    return json.loads(payload.decode("utf-8")) if payload else None"""
add_code_block(code_protocol, "Hình 2.14: Mã nguồn cơ chế đóng gói và giải khung phân mảnh (common/protocol.py)")

# 2.6.2.2
add_h3("2.6.2.2. Khởi tạo và vận hành Server TCP đa luồng")
add_p("Module server/main.py hiện thực hóa lớp QuizServer quản lý toàn bộ vòng đời của máy chủ. Server thiết lập tùy chọn SO_REUSEADDR để giải phóng cổng ngay khi khởi động lại, lắng nghe trên cổng 9999 và sử dụng cơ chế Non-blocking Timeout kết hợp vòng lặp accept() để tiếp nhận các kết nối Client:")

code_server = """# server/main.py
class QuizServer:
    def __init__(self, host='0.0.0.0', port=9999, max_connections=50):
        self.host = host
        self.port = port
        self.max_connections = max_connections
        self.auth_service = AuthService()
        self.clients = []
        self.lock = threading.Lock()

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(self.max_connections)
        self.running = True

        while self.running:
            client_socket, address = self.server_socket.accept()
            # Cấp phát một tiểu trình ClientHandler riêng biệt cho mỗi Client
            handler = ClientHandler(client_socket, address, self.auth_service)
            with self.lock:
                self.clients.append(handler)
            handler.start()
            logger.info(f"Phục vụ client {address} trên thread riêng")"""
add_code_block(code_server, "Hình 2.15: Mã nguồn khởi tạo Socket Server đa luồng (server/main.py)")

# 2.6.2.3
add_h3("2.6.2.3. Module giao tiếp mạng an toàn phía Client (Thread-Safe)")
add_p("Phía Client, giao diện CustomTkinter hoạt động trên một luồng chính (Main GUI Thread). Nếu các lệnh gửi nhận mạng chạy trực tiếp trên luồng này, giao diện sẽ bị đơ (Not Responding) mỗi khi mạng chậm. Do đó, lớp ServerConnection trong client/network.py được thiết kế dạng Thread-safe bằng cách sử dụng threading.Lock() nhằm đồng bộ hóa việc truy cập Socket từ các luồng nền:")

code_client_net = """# client/network.py
class ServerConnection:
    def __init__(self, host=None, port=None):
        self.host = host or "127.0.0.1"
        self.port = port or 9999
        self.sock = None
        self._lock = threading.Lock()
        self._is_connected = False

    def send_request(self, command: str, data=None, token=None) -> dict:
        with self._lock:  # Bảo đảm an toàn luồng (Thread-safe)
            if not self.is_connected:
                self.connect()
            req = Request(command=command, token=token, data=data or {})
            if not send_message(self.sock, req):
                return {"status": "ERROR", "message": "Lỗi gửi dữ liệu"}
            
            resp = receive_message(self.sock)
            return resp or {"status": "ERROR", "message": "Mất kết nối máy chủ"}"""
add_code_block(code_client_net, "Hình 2.16: Mã nguồn giao tiếp mạng Client an toàn đa luồng (client/network.py)")

# 2.6.2.4
add_h3("2.6.2.4. Bộ điều phối và định tuyến 28 mã lệnh nghiệp vụ")
add_p("Tiểu trình ClientHandler tiếp nhận thông điệp từ Socket con, trích xuất mã lệnh (command), token xác thực và tham số dữ liệu. Hệ thống sử dụng bảng ánh xạ hàm (Handler Map) để điều phối đến đúng dịch vụ nghiệp vụ tương ứng, đồng thời thực thi kiểm tra quyền hạn (Role-based Access Control - RBAC) nghiêm ngặt trước khi cho phép thao tác:")

code_handler = """# server/client_handler.py
class ClientHandler(threading.Thread):
    def run(self):
        while self.running:
            request = receive_message(self.client_socket)
            if not request: break
            response = self._handle_request(request)
            send_message(self.client_socket, response)

    def _handle_request(self, request: dict) -> dict:
        command = request.get('command')
        token = request.get('token')
        data = request.get('data', {})

        if command == CommandType.LOGIN:
            return self._handle_login(data)

        # Kiểm tra tính hợp lệ của Token phiên
        user = self.auth_service.validate_token(token)
        if not user:
            return {"status": "ERROR", "message": "Phiên làm việc hết hạn"}

        # Định tuyến mã lệnh theo quyền hạn
        handler_map = {
            CommandType.GET_USERS: lambda: self._require_role(user, ['ADMIN'], ...),
            CommandType.GET_QUESTIONS: lambda: self._require_role(user, ['ADMIN', 'TEACHER'], ...),
            CommandType.CREATE_EXAM: lambda: self._require_role(user, ['TEACHER'], ...),
            CommandType.SUBMIT_EXAM: lambda: ExamService.submit_exam(data, user),
            # ... Tổng cộng 28 mã lệnh nghiệp vụ
        }
        return handler_map.get(command, lambda: self._error("Lệnh không tồn tại"))()"""
add_code_block(code_handler, "Hình 2.17: Mã nguồn định tuyến lệnh và kiểm tra quyền hạn (server/client_handler.py)")

# 2.6.2.5
add_h3("2.6.2.5. Cơ chế bảo mật xác thực Bcrypt và quản lý phiên Token")
add_p("Hệ thống áp dụng thuật toán Bcrypt (chuẩn Blowfish) để băm mật khẩu một chiều với muối ngẫu nhiên trước khi lưu vào CSDL MySQL. Khi người dùng đăng nhập thành công, máy chủ sinh một chuỗi ngẫu nhiên chuẩn UUID phiên bản 4 (Token) và lưu trữ trên bộ nhớ RAM của AuthService:")

code_auth = """# server/service/auth_service.py
class AuthService:
    def __init__(self):
        self._sessions = {}  # Lưu trữ RAM: {token: user_info}

    def login(self, username: str, password: str):
        user = UserDAO.find_by_username(username)
        if not user or not user.get('is_active'):
            return False, "Tài khoản không hợp lệ", None

        # So khớp mật khẩu bằng hàm băm an toàn Bcrypt
        if not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            return False, "Mật khẩu không chính xác", None

        token = str(uuid.uuid4())  # Sinh mã Token ngẫu nhiên
        self._sessions[token] = {
            'id': user['id'], 'username': user['username'],
            'full_name': user['full_name'], 'role': user['role']
        }
        return True, "Đăng nhập thành công", {'token': token, 'user': self._sessions[token]}"""
add_code_block(code_auth, "Hình 2.18: Mã nguồn xác thực Bcrypt và sinh Token phiên (server/service/auth_service.py)")

# 2.6.2.6
add_h3("2.6.2.6. Phân tích các luồng tương tác mạng cốt lõi giữa hai máy Client – Server")
add_p("Hệ thống QuizApp hỗ trợ triển khai thực tế trên hai máy tính độc lập kết nối qua mạng LAN (hoặc máy ảo/máy vật lý). Dưới đây là phân tích chi tiết luồng trao đổi gói tin TCP giữa hai máy tính trong ba tình huống nghiệp vụ quan trọng nhất:")

add_p("1. Luồng nghiệp vụ Đăng nhập hệ thống (Lệnh LOGIN):", bold_prefix="• ")
add_bullet("Client khởi tạo kết nối TCP tới IP máy chủ tại Port 9999. Khi bắt tay 3 bước hoàn tất, Client gửi gói tin Request chứa {'command': 'LOGIN', 'data': {'username': '...', 'password': '...'}} có kèm 4 byte độ dài.")
add_bullet("Server giải mã JSON, kiểm tra mật khẩu bằng Bcrypt. Nếu hợp lệ, Server sinh UUID Token, lưu vào bộ nhớ RAM và phản hồi gói tin Response status: 'SUCCESS' kèm Token.")
add_bullet("Client lưu Token vào biến cục bộ để tự động gắn vào tiêu đề của mọi yêu cầu tiếp theo.")

add_p("2. Luồng nghiệp vụ Tải đề thi trực tuyến (Lệnh GET_EXAM_QUESTIONS):", bold_prefix="• ")
add_bullet("Sinh viên chọn đề thi và nhấn 'Vào thi'. Client gửi lệnh GET_EXAM_QUESTIONS kèm token và exam_id.")
add_bullet("Server kiểm tra xem đề thi có đang ở trạng thái ACTIVE hay không. Sau đó, Server truy vấn CSDL để lấy danh sách câu hỏi nhưng chủ động loại bỏ trường đáp án đúng (correct_answer) nhằm chống gian lận dữ liệu khi truyền qua mạng.")
add_bullet("Client nhận danh sách câu hỏi, khởi động đồng hồ đếm ngược nội bộ (Countdown Timer) và kết xuất giao diện phòng thi.")

add_p("3. Luồng nghiệp vụ Nộp bài thi và Chấm điểm tự động (Lệnh SUBMIT_EXAM):", bold_prefix="• ")
add_bullet("Khi sinh viên nhấn 'Nộp bài' (hoặc đồng hồ về 00:00), Client gom toàn bộ câu trả lời dạng {'question_id': ans} gửi lên Server.")
add_bullet("Server thực hiện đối chiếu song song với đáp án gốc trong CSDL MySQL, tính điểm theo thang 10, lưu vào bảng exam_results và exam_answers trong một giao dịch cơ sở dữ liệu an toàn.")
add_bullet("Server gửi phản hồi kết quả tức thì (Điểm số, số câu đúng / tổng số câu). Client hiển thị thông báo chúc mừng và cập nhật bảng lịch sử thi.")

# 2.7
add_h2("2.7. Kết chương 2")
add_p("Chương 2 đã trình bày một cách có hệ thống, toàn diện và sâu sắc quá trình phân tích và thiết kế hệ thống ứng dụng thi trắc nghiệm trực tuyến QuizApp dựa trên nền tảng lập trình mạng máy tính. Chương đã làm rõ kiến trúc phân tầng 3-tier, các giao thức mạng chủ đạo, topology hình sao và các tính năng chống gian lận đặc thù; đồng thời phân tích sâu sắc cơ chế hoạt động của giao thức TCP, Socket API, cùng quy trình chuẩn để xây dựng và triển khai một hệ thống giao tiếp mạng hai chiều.")

add_p("Đặc biệt, chương đã làm sáng tỏ giải pháp Server đa tuyến (Multi-threaded Concurrency) giúp hệ thống đáp ứng khối lượng lớn thí sinh dự thi cùng lúc; phân tích cơ chế đóng gói phân mảnh 4-byte Length-Prefix, bộ điều phối 28 mã lệnh nghiệp vụ, cùng các cơ chế bảo mật xác thực bằng thuật toán Bcrypt và Session Token UUID. Tất cả các nội dung đều được minh chứng trực tiếp bằng các đoạn mã nguồn và sơ đồ kỹ thuật trích xuất từ dự án thực tế.")

add_p("Những kết quả phân tích và thiết kế khoa học trong chương này chính là kim chỉ nam vững chắc để tiến hành cài đặt, triển khai và kiểm thử hệ thống trên môi trường thực nghiệm trong Chương 3 tiếp theo.")

doc.save(OUT_PATH)
print("Saved chuong2_phantich_thietke.docx successfully to:", OUT_PATH)
