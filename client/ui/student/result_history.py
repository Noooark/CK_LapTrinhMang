import threading
import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional, List
import customtkinter as ctk

from client.network import ServerConnection
from client.ui.utils import (
    PRIMARY_COLOR, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR,
    style_treeview, show_error, show_info
)


class ResultHistoryPanel(ctk.CTkFrame):
    """
    Student panel displaying historical exam results, scores, and completion timestamps.
    """

    def __init__(self, master, connection: ServerConnection, token: str, **kwargs):
        super().__init__(master, **kwargs)
        self.connection = connection
        self.token = token
        self.results_cache: List[Dict[str, Any]] = []

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
            text="📜 Lịch Sử Bài Thi",
            font=("Helvetica", 20, "bold")
        ).grid(row=0, column=0, sticky="w")

        self.refresh_btn = ctk.CTkButton(
            header,
            text="🔄 Làm mới",
            width=90,
            height=34,
            fg_color="gray40",
            hover_color="gray30",
            command=self.refresh_data
        )
        self.refresh_btn.grid(row=0, column=1, sticky="e")

        # 2. Summary stats strip
        stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        stats_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        stats_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.card_total = ctk.CTkFrame(stats_frame, corner_radius=8, fg_color=("gray85", "#242830"))
        self.card_total.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        self.lbl_total = ctk.CTkLabel(self.card_total, text="0 bài", font=("Helvetica", 18, "bold"), text_color=PRIMARY_COLOR)
        self.lbl_total.pack(pady=(10, 2))
        ctk.CTkLabel(self.card_total, text="Đã hoàn thành", font=("Helvetica", 11), text_color="gray60").pack(pady=(0, 10))

        self.card_avg = ctk.CTkFrame(stats_frame, corner_radius=8, fg_color=("gray85", "#242830"))
        self.card_avg.grid(row=0, column=1, padx=(0, 10), sticky="ew")
        self.lbl_avg = ctk.CTkLabel(self.card_avg, text="0.0", font=("Helvetica", 18, "bold"), text_color=SUCCESS_COLOR)
        self.lbl_avg.pack(pady=(10, 2))
        ctk.CTkLabel(self.card_avg, text="Điểm trung bình", font=("Helvetica", 11), text_color="gray60").pack(pady=(0, 10))

        self.card_pass = ctk.CTkFrame(stats_frame, corner_radius=8, fg_color=("gray85", "#242830"))
        self.card_pass.grid(row=0, column=2, sticky="ew")
        self.lbl_pass = ctk.CTkLabel(self.card_pass, text="0%", font=("Helvetica", 18, "bold"), text_color=WARNING_COLOR)
        self.lbl_pass.pack(pady=(10, 2))
        ctk.CTkLabel(self.card_pass, text="Tỉ lệ đạt (≥ 5.0)", font=("Helvetica", 11), text_color="gray60").pack(pady=(0, 10))

        # 3. Treeview Table
        table_frame = ctk.CTkFrame(self, corner_radius=8)
        table_frame.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="nsew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        cols = ("id", "title", "score", "correct", "total", "date", "status")
        self.tree = ttk.Treeview(
            table_frame,
            columns=cols,
            show="headings",
            selectmode="browse"
        )
        style = ttk.Style()
        style_treeview(style)

        self.tree.heading("id", text="Mã KQ")
        self.tree.heading("title", text="Tên bài thi")
        self.tree.heading("score", text="Điểm số")
        self.tree.heading("correct", text="Số câu đúng")
        self.tree.heading("total", text="Tổng câu hỏi")
        self.tree.heading("date", text="Ngày nộp bài")
        self.tree.heading("status", text="Đánh giá")

        self.tree.column("id", width=60, anchor="center")
        self.tree.column("title", width=340, anchor="w")
        self.tree.column("score", width=100, anchor="center")
        self.tree.column("correct", width=110, anchor="center")
        self.tree.column("total", width=110, anchor="center")
        self.tree.column("date", width=160, anchor="center")
        self.tree.column("status", width=110, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.tree.bind("<Double-1>", lambda e: self._view_details())

        # 4. Status Bar
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=("Helvetica", 11),
            text_color="gray60"
        )
        self.status_label.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="w")

    def refresh_data(self):
        self.status_label.configure(text="Đang tải lịch sử thi...")

        def worker():
            try:
                resp = self.connection.send_request("GET_MY_RESULTS", token=self.token)
                self.after(0, lambda: self._on_data_loaded(resp))
            except Exception as e:
                self.after(0, lambda: self._on_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_data_loaded(self, resp):
        for item in self.tree.get_children():
            self.tree.delete(item)

        if resp and resp.get("status") == "SUCCESS":
            self.results_cache = resp.get("data") or []
        else:
            self.results_cache = []

        scores = []
        pass_count = 0

        for r in self.results_cache:
            score = float(r.get("score", 0.0))
            scores.append(score)
            is_pass = (score >= 5.0)
            if is_pass:
                pass_count += 1

            status_str = "Đạt" if is_pass else "Chưa đạt"
            title = r.get("exam_title") or f"Bài thi #{r.get('exam_id')}"
            submitted_at = str(r.get("submitted_at", "") or "")[:19]

            self.tree.insert(
                "",
                "end",
                iid=str(r.get("id")),
                values=(
                    r.get("id"),
                    title,
                    f"{score:.1f}",
                    r.get("correct_count", 0),
                    r.get("total_questions", 0),
                    submitted_at or "-",
                    status_str
                )
            )

        total = len(scores)
        self.lbl_total.configure(text=f"{total} bài")

        if total > 0:
            avg_score = sum(scores) / total
            pass_rate = (pass_count / total) * 100
            self.lbl_avg.configure(text=f"{avg_score:.1f}")
            self.lbl_pass.configure(text=f"{pass_rate:.0f}%")
        else:
            self.lbl_avg.configure(text="0.0")
            self.lbl_pass.configure(text="0%")

        self.status_label.configure(text=f"Hiển thị {total} bài thi đã làm")

    def _view_details(self):
        selected = self.tree.selection()
        if not selected:
            return
        rid = int(selected[0])
        res = next((r for r in self.results_cache if r.get("id") == rid), None)
        if not res:
            return

        title = res.get("exam_title") or f"Bài thi #{res.get('exam_id')}"
        score = float(res.get("score", 0.0))
        correct = res.get("correct_count", 0)
        total = res.get("total_questions", 0)
        date = str(res.get("submitted_at", "") or "")[:19]

        msg = (
            f"Tên bài thi: {title}\n"
            f"Điểm số: {score:.1f} / 10\n"
            f"Số câu đúng: {correct} / {total}\n"
            f"Kết quả: {'ĐẠT ✅' if score >= 5.0 else 'CHƯA ĐẠT ❌'}\n"
            f"Thời gian nộp: {date}"
        )
        show_info("Chi tiết kết quả thi", msg, parent=self)

    def _on_error(self, err):
        self.status_label.configure(text=f"Lỗi: {err}")
        show_error("Lỗi kết nối", err, parent=self)
