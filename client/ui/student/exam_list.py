import threading
import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional, List, Callable
import customtkinter as ctk

from client.network import ServerConnection
from client.ui.student.exam_notice import exam_notice
from client.ui.utils import (
    PRIMARY_COLOR, PRIMARY_HOVER, SUCCESS_COLOR, WARNING_COLOR,
    style_treeview, show_error, show_info, show_warning
)


class ExamListPanel(ctk.CTkFrame):
    """
    Panel listing all available and active exams that students can take.
    """

    def __init__(
        self,
        master,
        connection: ServerConnection,
        token: str,
        on_start_exam: Callable[[Dict[str, Any]], None],
        **kwargs
    ):
        super().__init__(master, **kwargs)
        self.connection = connection
        self.token = token
        self.on_start_exam = on_start_exam

        self.exams_cache: List[Dict[str, Any]] = []
        self.taken_exam_ids = set()
        self.start_notice = None

        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # 1. Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="📝 Danh Sách Bài Thi Có Sẵn",
            font=("Helvetica", 20, "bold")
        ).grid(row=0, column=0, sticky="w")

        # 2. Toolbar
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        toolbar.grid_columnconfigure(0, weight=1)

        # Search field
        left_box = ctk.CTkFrame(toolbar, fg_color="transparent")
        left_box.grid(row=0, column=0, sticky="w")

        self.search_entry = ctk.CTkEntry(
            left_box,
            placeholder_text="🔍 Tìm bài thi theo tên hoặc môn...",
            width=300,
            height=34
        )
        self.search_entry.grid(row=0, column=0, padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda e: self._apply_filter())

        self.refresh_btn = ctk.CTkButton(
            left_box,
            text="🔄 Làm mới",
            width=90,
            height=34,
            fg_color="gray40",
            hover_color="gray30",
            command=self.refresh_data
        )
        self.refresh_btn.grid(row=0, column=1)

        # Start exam button
        right_box = ctk.CTkFrame(toolbar, fg_color="transparent")
        right_box.grid(row=0, column=1, sticky="e")

        self.take_exam_btn = ctk.CTkButton(
            right_box,
            text="✏️ Vào thi ngay",
            width=130,
            height=34,
            fg_color=SUCCESS_COLOR,
            hover_color="#218838",
            font=("Helvetica", 13, "bold"),
            command=self._start_exam_action
        )
        self.take_exam_btn.grid(row=0, column=0)

        # 3. Treeview Table
        table_frame = ctk.CTkFrame(self, corner_radius=8)
        table_frame.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="nsew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        cols = ("id", "title", "subject", "duration", "questions", "status", "user_status")
        self.tree = ttk.Treeview(
            table_frame,
            columns=cols,
            show="headings",
            selectmode="browse"
        )
        style = ttk.Style()
        style_treeview(style)

        self.tree.heading("id", text="ID")
        self.tree.heading("title", text="Tên đề thi")
        self.tree.heading("subject", text="Môn học")
        self.tree.heading("duration", text="Thời lượng")
        self.tree.heading("questions", text="Số câu hỏi")
        self.tree.heading("status", text="Trạng thái đề")
        self.tree.heading("user_status", text="Tình trạng của bạn")

        self.tree.column("id", width=50, anchor="center")
        self.tree.column("title", width=280, anchor="w")
        self.tree.column("subject", width=180, anchor="w")
        self.tree.column("duration", width=100, anchor="center")
        self.tree.column("questions", width=90, anchor="center")
        self.tree.column("status", width=110, anchor="center")
        self.tree.column("user_status", width=140, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.tree.bind("<Double-1>", lambda e: self._start_exam_action())

        # 4. Status Bar
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=("Helvetica", 11),
            text_color="gray60"
        )
        self.status_label.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="w")

    def refresh_data(self):
        self.status_label.configure(text="Đang tải danh sách bài thi...")

        def worker():
            try:
                # Fetch available exams and student's submitted results
                avail_resp = self.connection.send_request("GET_AVAILABLE_EXAMS", token=self.token)
                res_resp = self.connection.send_request("GET_MY_RESULTS", token=self.token)
                self.after(0, lambda: self._on_data_loaded(avail_resp, res_resp))
            except Exception as e:
                self.after(0, lambda: self._on_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_data_loaded(self, avail_resp, res_resp):
        if avail_resp and avail_resp.get("status") == "SUCCESS":
            self.exams_cache = avail_resp.get("data") or []
        else:
            self.exams_cache = []

        self.taken_exam_ids.clear()
        if res_resp and res_resp.get("status") == "SUCCESS":
            results = res_resp.get("data") or []
            for r in results:
                self.taken_exam_ids.add(r.get("exam_id"))

        self._apply_filter()

    def _apply_filter(self):
        query = self.search_entry.get().strip().lower()

        for item in self.tree.get_children():
            self.tree.delete(item)

        count = 0
        for exam in self.exams_cache:
            title = str(exam.get("title", "")).lower()
            subj = str(exam.get("subject_name", "")).lower()

            if query and (query not in title and query not in subj):
                continue

            eid = exam.get("id")
            is_taken = eid in self.taken_exam_ids
            user_status_str = "Đã hoàn thành ✓" if is_taken else "Chưa làm"

            self.tree.insert(
                "",
                "end",
                iid=str(eid),
                values=(
                    eid,
                    exam.get("title"),
                    exam.get("subject_name") or "-",
                    f"{exam.get('duration_minutes', 30)} phút",
                    exam.get("total_questions", 0),
                    exam.get("status", "ACTIVE"),
                    user_status_str
                )
            )
            count += 1

        self.status_label.configure(text=f"Có {count} bài thi hiển thị")

    def _get_selected_exam(self) -> Optional[Dict[str, Any]]:
        selected = self.tree.selection()
        if not selected:
            return None
        eid = int(selected[0])
        for e in self.exams_cache:
            if e.get("id") == eid:
                return e
        return None

    def _start_exam_action(self):
        if self.start_notice is not None:
            return
        exam = self._get_selected_exam()
        if not exam:
            show_warning("Chưa chọn bài thi", "Vui lòng chọn bài thi bạn muốn tham gia!", parent=self)
            return

        eid = exam.get("id")
        if eid in self.taken_exam_ids:
            show_warning(
                "Đã thi",
                "Bạn đã làm và nộp bài thi này rồi!\nVui lòng vào mục 'Lịch sử bài thi' để xem kết quả chi tiết.",
                parent=self
            )
            return

        status = exam.get("status", "ACTIVE")
        if status != "ACTIVE":
            show_warning("Chưa mở", f"Bài thi này hiện đang ở trạng thái {status}, chưa thể vào thi!", parent=self)
            return

        dur = exam.get("duration_minutes", 30)
        camera = "\nĐề thi này yêu cầu kiểm tra camera trước khi bắt đầu." if exam.get("camera_required") else ""
        self.start_notice, card = exam_notice(
            self, "Xác nhận vào thi",
            f"{exam.get('title')}\nThời gian làm bài: {dur} phút.{camera}\n\n"
            "Hệ thống ghi nhận việc rời cửa sổ, yêu cầu đóng cửa sổ và mất kết nối trong lúc thi. "
            "Giáo viên phụ trách có thể xem các cảnh báo.",
            PRIMARY_COLOR,
        )
        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(pady=(4, 20))
        ctk.CTkButton(actions, text="Quay lại", fg_color="gray40",
                      command=self._dismiss_start_notice).pack(side="left", padx=6)
        ctk.CTkButton(actions, text="Đồng ý vào thi",
                      command=lambda: self._confirm_start(exam)).pack(side="left", padx=6)

    def _dismiss_start_notice(self):
        self.start_notice.destroy()
        self.start_notice = None

    def _confirm_start(self, exam):
        self._dismiss_start_notice()
        self.on_start_exam(exam)

    def _on_error(self, err):
        self.status_label.configure(text=f"Lỗi: {err}")
        show_error("Lỗi kết nối", err, parent=self)
