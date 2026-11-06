import threading
import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional, List
import customtkinter as ctk

from client.network import ServerConnection
from client.ui.utils import (
    PRIMARY_COLOR, PRIMARY_HOVER, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR,
    style_treeview, show_error, show_info
)


class StatBadge(ctk.CTkFrame):
    """Small metric display card."""

    def __init__(self, master, label: str, value: str, color: str, **kwargs):
        super().__init__(master, corner_radius=10, fg_color=("gray85", "#242830"), **kwargs)
        self.grid_columnconfigure(0, weight=1)

        self.val_label = ctk.CTkLabel(
            self,
            text=value,
            font=("Helvetica", 20, "bold"),
            text_color=color
        )
        self.val_label.pack(pady=(12, 2))

        self.lbl_label = ctk.CTkLabel(
            self,
            text=label,
            font=("Helvetica", 11),
            text_color=("gray40", "gray70")
        )
        self.lbl_label.pack(pady=(0, 12))

    def set_value(self, val: str):
        self.val_label.configure(text=val)


class ResultViewerPanel(ctk.CTkFrame):
    """
    Teacher panel for inspecting exam results and performance metrics of students.
    """

    def __init__(self, master, connection: ServerConnection, token: str, **kwargs):
        super().__init__(master, **kwargs)
        self.connection = connection
        self.token = token

        self.exams_cache: List[Dict[str, Any]] = []
        self.results_cache: List[Dict[str, Any]] = []

        self._build_ui()
        self.load_exams()

    def _build_ui(self):
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # 1. Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="📊 Kết Quả Thi & Thống Kê",
            font=("Helvetica", 20, "bold")
        ).grid(row=0, column=0, sticky="w")

        # 2. Exam Selector toolbar
        selector_frame = ctk.CTkFrame(self, fg_color="transparent")
        selector_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        selector_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(selector_frame, text="Chọn đề thi:", font=("Helvetica", 13, "bold")).grid(row=0, column=0, padx=(0, 10), sticky="w")

        self.exam_map = {}
        self.exam_select_var = ctk.StringVar(value="-- Đang tải danh sách đề thi --")
        self.exam_menu = ctk.CTkOptionMenu(
            selector_frame,
            values=["-- Đang tải danh sách đề thi --"],
            variable=self.exam_select_var,
            command=self._on_exam_selected,
            width=350,
            height=36
        )
        self.exam_menu.grid(row=0, column=1, sticky="w")

        self.refresh_btn = ctk.CTkButton(
            selector_frame,
            text="🔄 Làm mới",
            width=90,
            height=36,
            fg_color="gray40",
            hover_color="gray30",
            command=self._reload_current_exam
        )
        self.refresh_btn.grid(row=0, column=2, padx=(10, 0), sticky="e")

        # 3. Stats row
        stats_row = ctk.CTkFrame(self, fg_color="transparent")
        stats_row.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="ew")
        stats_row.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        self.stat_count = StatBadge(stats_row, "Số bài thi nộp", "0", PRIMARY_COLOR)
        self.stat_count.grid(row=0, column=0, padx=5, sticky="ew")

        self.stat_avg = StatBadge(stats_row, "Điểm trung bình", "0.0", "#17a2b8")
        self.stat_avg.grid(row=0, column=1, padx=5, sticky="ew")

        self.stat_max = StatBadge(stats_row, "Điểm cao nhất", "0.0", SUCCESS_COLOR)
        self.stat_max.grid(row=0, column=2, padx=5, sticky="ew")

        self.stat_min = StatBadge(stats_row, "Điểm thấp nhất", "0.0", DANGER_COLOR)
        self.stat_min.grid(row=0, column=3, padx=5, sticky="ew")

        self.stat_pass = StatBadge(stats_row, "Tỉ lệ đạt (≥ 5.0)", "0%", WARNING_COLOR)
        self.stat_pass.grid(row=0, column=4, padx=5, sticky="ew")

        # 4. Results Treeview
        table_frame = ctk.CTkFrame(self, corner_radius=8)
        table_frame.grid(row=3, column=0, padx=20, pady=(0, 15), sticky="nsew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        cols = ("id", "student_name", "score", "correct", "total", "submitted_at")
        self.tree = ttk.Treeview(
            table_frame,
            columns=cols,
            show="headings",
            selectmode="browse"
        )
        style = ttk.Style()
        style_treeview(style)

        self.tree.heading("id", text="Mã KQ")
        self.tree.heading("student_name", text="Thí sinh (Học sinh/Sinh viên)")
        self.tree.heading("score", text="Điểm số (Thang 10)")
        self.tree.heading("correct", text="Số câu đúng")
        self.tree.heading("total", text="Tổng số câu")
        self.tree.heading("submitted_at", text="Thời gian nộp bài")

        self.tree.column("id", width=60, anchor="center")
        self.tree.column("student_name", width=260, anchor="w")
        self.tree.column("score", width=140, anchor="center")
        self.tree.column("correct", width=120, anchor="center")
        self.tree.column("total", width=120, anchor="center")
        self.tree.column("submitted_at", width=180, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # 5. Status footer
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=("Helvetica", 11),
            text_color="gray60"
        )
        self.status_label.grid(row=4, column=0, padx=20, pady=(0, 10), sticky="w")

    def load_exams(self):
        def worker():
            try:
                resp = self.connection.send_request("GET_EXAMS", token=self.token)
                self.after(0, lambda: self._on_exams_loaded(resp))
            except Exception as e:
                self.after(0, lambda: show_error("Lỗi", str(e), parent=self))

        threading.Thread(target=worker, daemon=True).start()

    def _on_exams_loaded(self, resp):
        if resp and resp.get("status") == "SUCCESS":
            self.exams_cache = resp.get("data") or []
        else:
            self.exams_cache = []

        self.exam_map.clear()
        options = []
        for e in self.exams_cache:
            label = f"[{e.get('id')}] {e.get('title')} ({e.get('status')})"
            self.exam_map[label] = e.get("id")
            options.append(label)

        if options:
            self.exam_menu.configure(values=options)
            self.exam_select_var.set(options[0])
            self._load_exam_results(self.exam_map[options[0]])
        else:
            self.exam_menu.configure(values=["-- Chưa có đề thi nào --"])
            self.exam_select_var.set("-- Chưa có đề thi nào --")
            self._clear_results()

    def _on_exam_selected(self, label: str):
        eid = self.exam_map.get(label)
        if eid:
            self._load_exam_results(eid)

    def _reload_current_exam(self):
        eid = self.exam_map.get(self.exam_select_var.get())
        if eid:
            self._load_exam_results(eid)
        else:
            self.load_exams()

    def _load_exam_results(self, exam_id: int):
        self.status_label.configure(text="Đang tải kết quả thi...")

        def worker():
            try:
                # Try GET_EXAM_RESULTS first, fallback to GET_RESULTS
                resp = self.connection.send_request("GET_EXAM_RESULTS", data={"exam_id": exam_id}, token=self.token)
                if not resp or resp.get("status") != "SUCCESS":
                    resp = self.connection.send_request("GET_RESULTS", data={"exam_id": exam_id}, token=self.token)

                self.after(0, lambda: self._on_results_loaded(resp))
            except Exception as e:
                self.after(0, lambda: self._on_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_results_loaded(self, resp):
        for item in self.tree.get_children():
            self.tree.delete(item)

        data = resp.get("data") if (resp and resp.get("status") == "SUCCESS") else None
        server_stats = {}
        if isinstance(data, dict):
            self.results_cache = data.get("results") or []
            server_stats = data.get("stats") or {}
        elif isinstance(data, list):
            self.results_cache = data
        else:
            self.results_cache = []

        scores = []
        pass_count = 0

        for r in self.results_cache:
            score = float(r.get("score", 0.0))
            scores.append(score)
            if score >= 5.0:
                pass_count += 1

            student_name = r.get("student_name") or f"Sinh viên #{r.get('student_id')}"
            submitted_at = str(r.get("submitted_at", "") or "")[:19]

            self.tree.insert(
                "",
                "end",
                iid=str(r.get("id")),
                values=(
                    r.get("id"),
                    student_name,
                    f"{score:.1f}",
                    r.get("correct_count", 0),
                    r.get("total_questions", 0),
                    submitted_at or "-"
                )
            )

        # Update metrics
        total = len(scores)
        self.stat_count.set_value(str(total))

        if total > 0:
            avg_score = sum(scores) / total
            max_score = max(scores)
            min_score = min(scores)
            pass_rate = (pass_count / total) * 100

            self.stat_avg.set_value(f"{avg_score:.1f}")
            self.stat_max.set_value(f"{max_score:.1f}")
            self.stat_min.set_value(f"{min_score:.1f}")
            self.stat_pass.set_value(f"{pass_rate:.0f}%")
        else:
            self.stat_avg.set_value("0.0")
            self.stat_max.set_value("0.0")
            self.stat_min.set_value("0.0")
            self.stat_pass.set_value("0%")

        self.status_label.configure(text=f"Hiển thị {total} kết quả bài nộp")

    def _clear_results(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.stat_count.set_value("0")
        self.stat_avg.set_value("0.0")
        self.stat_max.set_value("0.0")
        self.stat_min.set_value("0.0")
        self.stat_pass.set_value("0%")
        self.status_label.configure(text="")

    def _on_error(self, err):
        self.status_label.configure(text=f"Lỗi: {err}")
        show_error("Lỗi kết nối", err, parent=self)
