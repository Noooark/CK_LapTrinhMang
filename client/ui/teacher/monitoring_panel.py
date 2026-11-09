"""Teacher workspace for live attempts and reviewing alerts."""
import base64
from io import BytesIO
from time import monotonic
from tkinter import ttk

import customtkinter as ctk
from PIL import Image

from common.camera import CAMERA_EVENTS
from common.snapshots import MAX_BASE64_CHARS, MAX_HEIGHT, MAX_WIDTH
from client.request_worker import RequestWorker
from client.ui.utils import PRIMARY_COLOR, WARNING_COLOR


EVENT_LABELS = {
    "FOCUS_LOST": "Rời cửa sổ",
    "FULLSCREEN_EXIT": "Thoát toàn màn hình",
    "EXAM_EXIT_REQUESTED": "Yêu cầu đóng cửa sổ",
    "HEARTBEAT_TIMEOUT": "Mất kết nối",
    "CAMERA_NO_FACE": "Không thấy khuôn mặt",
    "CAMERA_MULTIPLE_FACES": "Nhiều khuôn mặt",
    "CAMERA_PHONE_DETECTED": "Phát hiện điện thoại",
    "CAMERA_DISCONNECTED": "Camera mất tín hiệu / đã tắt",
    "CAMERA_OBSTRUCTED": "Hình ảnh khó quan sát",
    "CAMERA_RECOVERED": "Camera hoạt động",
}


class MonitoringPanel(ctk.CTkFrame):
    POLL_SECONDS = 2

    def __init__(self, master, connection, token):
        super().__init__(master)
        self.worker = RequestWorker(connection, token)
        self.exams = {}
        self.exam_id = None
        self.before_id = None
        self.next_before_id = None
        self.latest_seen = {}
        self.pending = False
        self.generation = 0
        self.next_poll = 0
        self.snapshot_rows = set()
        self.snapshot_pending = False
        self.snapshot_window = None

        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=14, pady=12)
        self.exam_menu = ctk.CTkComboBox(toolbar, width=370, values=["Đang tải đề thi…"],
                                        state="readonly", command=self._select_exam)
        self.exam_menu.set("Đang tải đề thi…")
        self.exam_menu.pack(side="left")
        ctk.CTkButton(toolbar, text="Tải lại đề thi", command=self._load_exams).pack(side="left", padx=10)
        self.notice = ctk.CTkLabel(self, text="", text_color=WARNING_COLOR,
                                   font=("Helvetica", 15, "bold"), anchor="w")
        self.notice.pack(fill="x", padx=14)
        self.status = self._tree(("Sinh viên", "Bắt đầu", "Trạng thái", "Camera", "Heartbeat cuối",
                                  "Số cảnh báo", "Cảnh báo gần nhất", "Thời điểm"))
        self.history = self._tree(("Thời gian", "Sinh viên", "Sự kiện", "Thời lượng", "Trạng thái"))
        self.history.bind("<ButtonRelease-1>", self._open_history_status, add="+")
        self.snapshot_hint = ctk.CTkLabel(self, text="", anchor="w", font=("Helvetica", 12))
        self.snapshot_hint.pack(fill="x", padx=14)

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=14, pady=(4, 12))
        self.review = ctk.CTkButton(actions, text="Đánh dấu đã xem", command=self._acknowledge)
        self.review.pack(side="left")
        ctk.CTkButton(actions, text="Mới nhất", command=lambda: self._show_page(None)).pack(side="right")
        self.older = ctk.CTkButton(actions, text="Cảnh báo cũ hơn", command=self._older_page, state="disabled")
        self.older.pack(side="right", padx=10)

        self.loading_exams = False
        self.reviewing = False
        self._load_exams()
        self.poll_job = self.after(100, self._poll)

    def _tree(self, headings):
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=14, pady=5)
        style = ttk.Style(self)
        style.configure("Monitoring.Treeview", font=("Segoe UI", 11),
                        rowheight=round(self._apply_widget_scaling(27)))
        style.configure("Monitoring.Treeview.Heading", font=("Segoe UI", 11, "bold"))
        tree = ttk.Treeview(frame, columns=headings, show="headings", selectmode="browse", height=7,
                            style="Monitoring.Treeview")
        for heading in headings:
            tree.heading(heading, text=heading)
            tree.column(heading, width=115, minwidth=70, anchor="center")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        vertical = ttk.Scrollbar(frame, command=tree.yview)
        horizontal = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        tree.tag_configure("unreviewed", background="#fff0cd", foreground="#573900")
        return tree

    def _load_exams(self):
        if not self.loading_exams:
            self.loading_exams = True
            self.worker.request("GET_EXAMS", {}, self._on_exams)

    def _on_exams(self, response):
        self.loading_exams = False
        if response["status"] != "SUCCESS":
            self.notice.configure(text=response["message"])
            return
        self.exams = {f"{row['id']} · {row['title']}": row["id"] for row in response["data"]}
        self.exam_menu.configure(values=list(self.exams))
        label = next((key for key, value in self.exams.items() if value == self.exam_id),
                     next(iter(self.exams), "Chưa có đề thi"))
        self.exam_menu.set(label)
        self._select_exam(label)

    def _select_exam(self, label):
        self.exam_id = self.exams.get(label)
        self.notice.configure(text="")
        self._replace(self.status, [])
        self._show_page(None)

    def _show_page(self, before_id):
        self.generation += 1
        self.before_id = before_id
        self.snapshot_rows.clear()
        self.snapshot_hint.configure(text="")
        self.next_before_id = None
        self.older.configure(state="disabled")
        self._replace(self.history, [])
        self.next_poll = 0

    def _older_page(self):
        if self.next_before_id is not None:
            self._show_page(self.next_before_id)

    def _poll(self):
        self.worker.dispatch()
        if self.exam_id is not None and not self.pending and monotonic() >= self.next_poll:
            self.pending = True
            generation = self.generation
            query = {"exam_id": self.exam_id}
            self.worker.request("GET_MONITORING_STATUS", query, lambda r: self._on_status(generation, r))
            self.worker.request("GET_EXAM_EVENTS", {**query, "before_id": self.before_id},
                                lambda r: self._on_history(generation, r))
        self.poll_job = self.after(100, self._poll)

    def _on_status(self, generation, response):
        if generation != self.generation:
            return
        if response["status"] != "SUCCESS":
            self.notice.configure(text=response["message"])
            return
        rows = []
        for row in response["data"]:
            if row["status"] == "SUBMITTED":
                status = "Đã nộp"
            elif row["expired"]:
                status = "Hết hạn"
            else:
                status = "Mất liên lạc" if row["status"] == "INTERRUPTED" else "Đang kết nối"
            camera = EVENT_LABELS.get(row.get("camera_status"), "Không yêu cầu camera")
            if row.get("camera_status") and (row["status"] == "SUBMITTED" or row["expired"]):
                camera = "Đã dừng"
            elif row.get("camera_status") and row["status"] == "INTERRUPTED":
                camera = "Chưa xác nhận · mất TCP"
            rows.append((row["id"], (row["username"], self._time(row["started_at"]), status, camera,
                                     self._time(row["last_heartbeat"]), row["event_count"],
                                     EVENT_LABELS.get(row["latest_event"], "—"), self._time(row["latest_at"])), ""))
        self._replace(self.status, rows)

    def _on_history(self, generation, response):
        self.pending = False
        self.next_poll = monotonic() + self.POLL_SECONDS
        if generation != self.generation:
            self.next_poll = 0
            return
        if response["status"] != "SUCCESS":
            self.notice.configure(text=response["message"])
            return
        data = response["data"]
        rows = data["events"]
        self.snapshot_rows = {str(row["id"]) for row in rows if row.get("has_snapshot")}
        if data.get("snapshot_access") is False:
            hint = "Xem ảnh bằng chứng cần kết nối TLS và thư mục lưu ảnh được cấu hình trên Server."
        else:
            hint = "Bấm 👁 trên dòng cảnh báo camera để xem ảnh của sự kiện đó."
        self.snapshot_hint.configure(text=hint)
        self.next_before_id = data["next_before_id"]
        self.older.configure(state="normal" if self.next_before_id is not None else "disabled")
        if self.before_id is None:
            latest = next((row["id"] for row in rows if row.get("severity") != "INFO"),
                          self.latest_seen.get(self.exam_id, 0))
            previous = self.latest_seen.get(self.exam_id, latest)
            if latest > previous:
                self.notice.configure(text="Có cảnh báo mới trong lịch sử giám sát.")
            self.latest_seen[self.exam_id] = latest
        self._replace(self.history, [
            (row["id"], (self._time(row["created_at"]), row["username"], self._event_label(row),
                         "—" if row["duration_seconds"] is None else f"{row['duration_seconds']:.1f} s",
                         self._status_label(row)),
             "" if row["reviewed"] or row.get("severity") == "INFO" else "unreviewed") for row in rows
        ])

    @staticmethod
    def _status_label(row):
        if row.get("severity") == "INFO":
            return "Thông tin"
        if row["event_type"] in CAMERA_EVENTS:
            return "👁" if row.get("has_snapshot") else "Không có ảnh"
        return "Đã xem" if row["reviewed"] else "Chưa xem"

    def _open_history_status(self, event):
        if self.snapshot_pending or self.history.identify_region(event.x, event.y) != "cell":
            return
        column = self.history.identify_column(event.x)
        row = self.history.identify_row(event.y)
        if row in self.snapshot_rows and column and self.history.column(column, "id") == "Trạng thái":
            self.snapshot_pending = True
            generation = self.generation
            self.worker.request("GET_EXAM_SNAPSHOT", {"event_id": int(row)},
                                lambda result: self._show_snapshot(generation, result))

    def _show_snapshot(self, generation, response):
        self.snapshot_pending = False
        if generation != self.generation:
            return
        data = response.get("data") or {}
        encoded = data.get("image_base64", "")
        try:
            if (response["status"] != "SUCCESS" or not isinstance(encoded, str)
                    or not 0 < len(encoded) <= MAX_BASE64_CHARS):
                raise ValueError
            with Image.open(BytesIO(base64.b64decode(encoded, validate=True)), formats=["JPEG"]) as jpeg:
                if not 0 < jpeg.width <= MAX_WIDTH or not 0 < jpeg.height <= MAX_HEIGHT:
                    raise ValueError
                jpeg.thumbnail((580, 370))
                image = jpeg.copy()
        except (OSError, ValueError, Image.DecompressionBombError):
            dialog = self._snapshot_dialog()
            ctk.CTkLabel(dialog, text="Ảnh bằng chứng không còn khả dụng",
                         font=("Helvetica", 18, "bold"), text_color=WARNING_COLOR).pack(padx=24, pady=20)
            ctk.CTkButton(dialog, text="Đóng", command=self._close_snapshot).pack(pady=(0, 16))
            return

        dialog = self._snapshot_dialog()
        ctk.CTkLabel(dialog, text="Ảnh bằng chứng camera", text_color=PRIMARY_COLOR,
                     font=("Helvetica", 22, "bold")).pack(padx=24, pady=(18, 6))
        ctk.CTkLabel(dialog, text=self._event_label(data), font=("Helvetica", 17, "bold"),
                     wraplength=580).pack(padx=24)
        text = (f"Sinh viên: {data['username']} · Đề thi: {data['title']}\n"
                f"Thời điểm: {self._time(data['captured_at'])}")
        ctk.CTkLabel(dialog, text=text, font=("Helvetica", 14), wraplength=580).pack(padx=24, pady=8)
        ctk.CTkLabel(dialog, text="", image=ctk.CTkImage(image, size=image.size)).pack(padx=24, pady=6)
        ctk.CTkButton(dialog, text="Đóng", command=self._close_snapshot).pack(pady=(8, 18))

    def _snapshot_dialog(self):
        self._close_snapshot()
        dialog = ctk.CTkToplevel(self)
        self.snapshot_window = dialog
        dialog.title("Ảnh bằng chứng camera")
        dialog.transient(self.winfo_toplevel())
        dialog.protocol("WM_DELETE_WINDOW", self._close_snapshot)
        return dialog

    def _close_snapshot(self):
        if self.snapshot_window is not None:
            self.snapshot_window.destroy()
            self.snapshot_window = None

    @staticmethod
    def _event_label(row):
        if row.get("face_count"):
            return f"Camera: Phát hiện {row['face_count']} khuôn mặt"
        if row["event_type"] == "CAMERA_DISCONNECTED" and row["duration_seconds"] == 0:
            return "Camera: Đã rút quyền"
        return EVENT_LABELS.get(row["event_type"], row["event_type"])

    @staticmethod
    def _time(value):
        return str(value).split(".")[0] if value else "—"

    @staticmethod
    def _replace(tree, rows):
        # Update in place so polling doesn't reset selection or scroll position.
        stale = set(tree.get_children())
        for index, (key, values, tag) in enumerate(rows):
            key = str(key)
            tags = (tag,) if tag else ()
            if key in stale:
                tree.item(key, values=values, tags=tags)
                tree.move(key, "", index)
                stale.remove(key)
            else:
                tree.insert("", index, iid=key, values=values, tags=tags)
        if stale:
            tree.delete(*stale)

    def _acknowledge(self):
        selected = self.history.selection()
        if selected and not self.reviewing:
            self.reviewing = True
            self.worker.request("ACKNOWLEDGE_EXAM_EVENT",
                                {"exam_id": self.exam_id, "id": int(selected[0])}, self._on_acknowledged)

    def _on_acknowledged(self, response):
        self.reviewing = False
        self.notice.configure(text=response["message"])
        self.next_poll = 0

    def destroy(self):
        self._close_snapshot()
        self.after_cancel(self.poll_job)
        self.worker.stop()
        super().destroy()
