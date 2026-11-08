"""Explicit camera consent and local preview before opening an attempt."""
import customtkinter as ctk
from PIL import Image

from client.anti_cheat.camera_monitor import CameraMonitor, DISCONNECTED


class CameraCheckDialog(ctk.CTkToplevel):
    def __init__(self, master, on_ready, retention_days=None):
        super().__init__(master)
        self.title("Kiểm tra camera trước khi thi")
        self.transient(master.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.on_ready = on_ready
        self.camera = None
        self.job = None
        self.last_preview = None
        self.evidence_required = bool(retention_days)

        ctk.CTkLabel(self, text="Kiểm tra camera trước khi thi",
                     font=("Helvetica", 22, "bold")).pack(padx=20, pady=(16, 0))
        ctk.CTkLabel(
            self, text="Đề thi yêu cầu camera để kiểm tra sự hiện diện, số người và điện thoại trong khung hình. "
                       "Video được phân tích trên máy. "
                       "Nếu không đồng ý hoặc không có camera, hãy liên hệ giáo viên.",
            font=("Helvetica", 15), wraplength=460, justify="left",
        ).pack(padx=20, pady=12)
        if self.evidence_required:
            ctk.CTkLabel(
                self, text=f"Lưu ảnh bằng chứng là điều kiện của đề thi. Khi có cảnh báo vắng mặt, nhiều người, "
                           f"điện thoại hoặc ảnh khó quan sát, hệ thống lưu một ảnh webcam nếu có khung hình hợp lệ. "
                           f"Giáo viên phụ trách có thể xem ảnh trong {retention_days} ngày. "
                           "Nếu không chấp nhận điều kiện này, hãy chọn Quay lại và liên hệ giáo viên.",
                font=("Helvetica", 15), wraplength=460, justify="left",
            ).pack(padx=20, pady=(0, 8))
        else:
            ctk.CTkLabel(self, text="Lượt thi này không lưu ảnh webcam.").pack(padx=20)
        device = ctk.CTkFrame(self, fg_color="transparent")
        device.pack(padx=20)
        ctk.CTkLabel(device, text="Thiết bị camera (0 là mặc định)").pack(side="left")
        self.index = ctk.CTkEntry(device, width=48)
        self.index.insert(0, "0")
        self.index.pack(side="left", padx=8)
        self.preview = ctk.CTkLabel(self, width=300, height=180, text="Camera chưa bật")
        self.preview.pack(padx=20, pady=8)
        self.status = ctk.CTkLabel(self, text="Chờ bạn đồng ý", font=("Helvetica", 15, "bold"), wraplength=460)
        self.status.pack(padx=20)
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(padx=12, pady=14)
        self.enable = ctk.CTkButton(actions, text="Đồng ý và bật camera", command=self._enable)
        self.enable.pack(side="left", padx=4)
        self.start = ctk.CTkButton(actions, text="Bắt đầu thi", state="disabled", command=self._start)
        self.start.pack(side="left", padx=4)
        ctk.CTkButton(actions, text="Quay lại", command=self.destroy).pack(side="left", padx=4)
        self.grab_set()

    def _enable(self):
        try:
            index = int(self.index.get())
            if not 0 <= index <= 15:
                raise ValueError
        except ValueError:
            self.status.configure(text="Nhập mã camera từ 0 đến 15.")
            return
        if self.camera is None or self.camera.finished.is_set():
            self.camera = CameraMonitor(index)
        else:
            self.camera.retry(index)
        self.enable.configure(text="Thử lại / đổi thiết bị")
        if self.job is None:
            self._poll()

    def _poll(self):
        sample = self.camera.snapshot()
        ready = sample.condition is None
        self.start.configure(state="normal" if ready else "disabled")
        if sample.preview is not None and sample.timestamp != self.last_preview:
            image = Image.fromarray(sample.preview)
            height = round(300 * image.height / image.width)
            self.preview.configure(image=ctk.CTkImage(image, size=(300, height)), text="")
            self.last_preview = sample.timestamp
        if sample.condition == DISCONNECTED:
            self.preview.configure(image=None, text="Chưa có hình ảnh")
            message = sample.error or "Đang kết nối camera…"
        elif sample.condition == "CAMERA_OBSTRUCTED":
            message = "Hình ảnh khó quan sát. Hãy kiểm tra ánh sáng và camera."
        else:
            message = f"Camera đã kết nối · Số khuôn mặt: {sample.faces}. Cần đúng một khuôn mặt."
        if sample.condition != DISCONNECTED:
            if self.camera.phone_available is not True:
                phone = "Nhận diện điện thoại chưa sẵn sàng."
            elif sample.phone_detected is True:
                phone = "Đã thấy điện thoại trong khung hình xem trước."
            else:
                phone = "Nhận diện điện thoại đang bật · Chưa thấy điện thoại."
            message += f"\n{phone}"
        self.status.configure(text=message)
        self.job = self.after(100, self._poll)

    def _start(self):
        if self.camera is not None and self.camera.snapshot().condition is None:
            camera, self.camera = self.camera, None
            camera.begin_exam()
            camera.snapshot_consent = self.evidence_required
            self.destroy()
            try:
                self.on_ready(camera)
            except Exception:
                camera.stop()
                raise

    def destroy(self):
        if self.job is not None:
            self.after_cancel(self.job)
            self.job = None
        if self.camera is not None:
            self.camera.stop()
            self.camera = None
        super().destroy()
