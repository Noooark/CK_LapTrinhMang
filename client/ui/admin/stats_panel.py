import threading
from typing import Dict, Any
import customtkinter as ctk

from client.network import ServerConnection
from client.ui.utils import PRIMARY_COLOR, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR, show_error


class StatsCard(ctk.CTkFrame):
    """Stat indicator card with icon, count, and title."""

    def __init__(self, master, title: str, value: str, icon: str, color: str, **kwargs):
        super().__init__(master, corner_radius=12, fg_color=("gray85", "#242830"), **kwargs)
        self.grid_columnconfigure(0, weight=1)

        self.icon_label = ctk.CTkLabel(self, text=icon, font=("Segoe UI Emoji", 28))
        self.icon_label.grid(row=0, column=0, pady=(15, 5))

        self.val_label = ctk.CTkLabel(
            self,
            text=str(value),
            font=("Helvetica", 24, "bold"),
            text_color=color
        )
        self.val_label.grid(row=1, column=0, pady=(0, 2))

        self.title_label = ctk.CTkLabel(
            self,
            text=title,
            font=("Helvetica", 12),
            text_color=("gray40", "gray70")
        )
        self.title_label.grid(row=2, column=0, pady=(0, 15))

    def update_value(self, val: Any):
        self.val_label.configure(text=str(val))


class SystemStatsPanel(ctk.CTkFrame):
    """
    Overview statistics panel for system administrators.
    """

    def __init__(self, master, connection: ServerConnection, token: str, **kwargs):
        super().__init__(master, **kwargs)
        self.connection = connection
        self.token = token

        self._build_ui()
        self.refresh_stats()

    def _build_ui(self):
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="📊 Thống kê Toàn hệ thống",
            font=("Helvetica", 20, "bold")
        ).grid(row=0, column=0, sticky="w")

        self.refresh_btn = ctk.CTkButton(
            header,
            text="🔄 Làm mới",
            width=90,
            height=34,
            fg_color="gray40",
            hover_color="gray30",
            command=self.refresh_stats
        )
        self.refresh_btn.grid(row=0, column=1, sticky="e")

        # Grid of Cards
        cards_container = ctk.CTkFrame(self, fg_color="transparent")
        cards_container.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        cards_container.grid_columnconfigure((0, 1, 2), weight=1)

        self.card_users = StatsCard(cards_container, "Tổng tài khoản", "0", "👥", PRIMARY_COLOR)
        self.card_users.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.card_teachers = StatsCard(cards_container, "Giáo viên", "0", "👨‍🏫", SUCCESS_COLOR)
        self.card_teachers.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.card_students = StatsCard(cards_container, "Học sinh / Sinh viên", "0", "🎓", WARNING_COLOR)
        self.card_students.grid(row=0, column=2, padx=10, pady=10, sticky="ew")

        self.card_subjects = StatsCard(cards_container, "Môn học", "0", "📚", "#17a2b8")
        self.card_subjects.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        self.card_questions = StatsCard(cards_container, "Ngân hàng câu hỏi", "0", "❓", "#6f42c1")
        self.card_questions.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        self.card_exams = StatsCard(cards_container, "Đề thi đã tạo", "0", "📝", "#e83e8c")
        self.card_exams.grid(row=1, column=2, padx=10, pady=10, sticky="ew")

        # Summary box
        summary_frame = ctk.CTkFrame(self, corner_radius=10, fg_color=("gray90", "#242830"))
        summary_frame.grid(row=2, column=0, padx=30, pady=(15, 20), sticky="nsew")
        summary_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            summary_frame,
            text="📌 Thông tin hệ thống",
            font=("Helvetica", 14, "bold")
        ).grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        info_text = (
            "• Hệ thống quản lý thi trắc nghiệm trực tuyến qua mạng máy tính TCP Socket.\n"
            "• Giao thức mã hóa JSON có độ dài cố định 4 bytes độ dài.\n"
            "• Quyền Admin cho phép quản trị người dùng, phân quyền giảng dạy và cấu hình môn học.\n"
            "• Mọi thay đổi dữ liệu được lưu tức thời và đồng bộ với cơ sở dữ liệu."
        )
        ctk.CTkLabel(
            summary_frame,
            text=info_text,
            font=("Helvetica", 12),
            text_color=("gray30", "gray75"),
            justify="left",
            wraplength=600
        ).grid(row=1, column=0, padx=20, pady=(0, 15), sticky="w")

    def refresh_stats(self):
        def worker():
            try:
                resp = self.connection.send_request("GET_STATS", token=self.token)
                self.after(0, lambda: self._on_stats_loaded(resp))
            except Exception as e:
                self.after(0, lambda: show_error("Lỗi", str(e), parent=self))

        threading.Thread(target=worker, daemon=True).start()

    def _on_stats_loaded(self, resp):
        if resp and resp.get("status") == "SUCCESS":
            data = resp.get("data") or {}
            self.card_users.update_value(data.get("total_users", 0))
            self.card_teachers.update_value(data.get("total_teachers", 0))
            self.card_students.update_value(data.get("total_students", 0))
            self.card_subjects.update_value(data.get("total_subjects", 0))
            self.card_questions.update_value(data.get("total_questions", 0))
            self.card_exams.update_value(data.get("total_exams", 0))
