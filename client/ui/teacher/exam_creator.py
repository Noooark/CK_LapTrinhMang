import os
import shutil
import threading
import tkinter as tk
from tkinter import ttk, filedialog
from typing import Dict, Any, Optional, List
import customtkinter as ctk

from client.network import ServerConnection
from client.ui.utils import (
    PRIMARY_COLOR, PRIMARY_HOVER, DANGER_COLOR, SUCCESS_COLOR, WARNING_COLOR,
    style_treeview, show_error, show_info, show_warning, ask_yes_no
)
from common.parser import QuestionParser


class CreateExamDialog(ctk.CTkToplevel):
    """
    Dialog for creating a new exam, supporting both random question generation
    and manual selection from question bank.
    """

    def __init__(
        self,
        parent,
        connection: ServerConnection,
        token: str,
        subjects: List[Dict[str, Any]],
        on_save_success=None
    ):
        super().__init__(parent)
        self.connection = connection
        self.token = token
        self.subjects = subjects
        self.on_save_success = on_save_success

        self.subject_questions: List[Dict[str, Any]] = []
        self.selected_question_ids = set()
        self.file_imported_questions: List[Dict[str, Any]] = []

        self.title("Tạo Đề Thi Mới")
        self.geometry("700x680")
        self.minsize(580, 500)
        self.resizable(True, True)
        self.transient(parent)
        self.lift()
        self.focus_force()
        self.after(100, self._safe_grab)

        self._build_ui()

    def _safe_grab(self):
        try:
            if self.winfo_exists():
                self.grab_set()
        except Exception:
            pass

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        ctk.CTkLabel(
            self,
            text="Tạo Đề Thi Mới",
            font=("Helvetica", 18, "bold")
        ).grid(row=0, column=0, padx=25, pady=(15, 10), sticky="w")

        # Container
        container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        container.grid(row=1, column=0, padx=25, pady=0, sticky="nsew")
        container.grid_columnconfigure(0, weight=1)

        # Exam Title
        ctk.CTkLabel(container, text="Tên đề thi:", font=("Helvetica", 12, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.title_entry = ctk.CTkEntry(container, height=36, placeholder_text="Ví dụ: Kiểm tra giữa kỳ Mạng máy tính")
        self.title_entry.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        # Row 2: Subject & Duration
        row2 = ctk.CTkFrame(container, fg_color="transparent")
        row2.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        row2.grid_columnconfigure((0, 1), weight=1)

        # Subject
        ctk.CTkLabel(row2, text="Môn học:", font=("Helvetica", 12, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.subject_map = {}
        subj_names = []
        for s in self.subjects:
            name = s.get("name", f"Subject #{s.get('id')}")
            subj_names.append(name)
            self.subject_map[name] = s.get("id")

        if not subj_names:
            subj_names = ["-- Chưa có môn học --"]

        self.subj_var = ctk.StringVar(value=subj_names[0])
        self.subj_menu = ctk.CTkOptionMenu(
            row2,
            values=subj_names,
            variable=self.subj_var,
            command=self._on_subject_changed,
            height=36
        )
        self.subj_menu.grid(row=1, column=0, sticky="ew", padx=(0, 10))

        # Duration (minutes)
        ctk.CTkLabel(row2, text="Thời gian làm bài (phút):", font=("Helvetica", 12, "bold")).grid(row=0, column=1, sticky="w", pady=(0, 2))
        self.duration_entry = ctk.CTkEntry(row2, height=36, placeholder_text="Ví dụ: 30")
        self.duration_entry.grid(row=1, column=1, sticky="ew")
        self.duration_entry.insert(0, "30")

        # Mode Selection Tab
        ctk.CTkLabel(container, text="Phương thức chọn câu hỏi:", font=("Helvetica", 12, "bold")).grid(row=3, column=0, sticky="w", pady=(5, 4))
        self.mode_var = ctk.StringVar(value="RANDOM")
        self.mode_segmented = ctk.CTkSegmentedButton(
            container,
            values=["Ngẫu nhiên", "Chọn thủ công", "📁 Nhập từ file"],
            command=self._on_mode_changed,
            height=34
        )
        self.mode_segmented.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        self.mode_segmented.set("Ngẫu nhiên")

        # Frame for RANDOM mode
        self.random_frame = ctk.CTkFrame(container, fg_color="transparent")
        self.random_frame.grid(row=5, column=0, sticky="ew", pady=(5, 10))
        self.random_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.random_frame, text="Số lượng câu hỏi ngẫu nhiên:", font=("Helvetica", 12)).grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.num_questions_entry = ctk.CTkEntry(self.random_frame, height=36, placeholder_text="Ví dụ: 10")
        self.num_questions_entry.grid(row=1, column=0, sticky="ew")
        self.num_questions_entry.insert(0, "10")

        # Frame for MANUAL mode
        self.manual_frame = ctk.CTkFrame(container, fg_color="transparent")
        # Hidden by default

        ctk.CTkLabel(
            self.manual_frame,
            text="Chọn các câu hỏi từ ngân hàng (click để chọn/bỏ chọn):",
            font=("Helvetica", 12)
        ).pack(anchor="w", pady=(0, 4))

        # Treeview for selecting questions
        tbl_container = ctk.CTkFrame(self.manual_frame, height=220)
        tbl_container.pack(fill="both", expand=True)

        cols = ("sel", "id", "content", "diff")
        self.q_tree = ttk.Treeview(tbl_container, columns=cols, show="headings", height=8, selectmode="browse")
        style = ttk.Style()
        style_treeview(style)

        self.q_tree.heading("sel", text="✓")
        self.q_tree.heading("id", text="ID")
        self.q_tree.heading("content", text="Nội dung câu hỏi")
        self.q_tree.heading("diff", text="Độ khó")

        self.q_tree.column("sel", width=35, anchor="center")
        self.q_tree.column("id", width=45, anchor="center")
        self.q_tree.column("content", width=420, anchor="w")
        self.q_tree.column("diff", width=70, anchor="center")

        q_scroll = ttk.Scrollbar(tbl_container, orient="vertical", command=self.q_tree.yview)
        self.q_tree.configure(yscrollcommand=q_scroll.set)

        self.q_tree.pack(side="left", fill="both", expand=True)
        q_scroll.pack(side="right", fill="y")

        self.q_tree.bind("<ButtonRelease-1>", self._toggle_question_selection)

        self.manual_count_label = ctk.CTkLabel(self.manual_frame, text="Đã chọn: 0 câu", font=("Helvetica", 11, "bold"))
        self.manual_count_label.pack(anchor="e", pady=(4, 0))

        # Frame for FILE IMPORT mode
        self.file_frame = ctk.CTkFrame(container, fg_color="transparent")
        # Hidden by default

        file_picker_row = ctk.CTkFrame(self.file_frame, fg_color="transparent")
        file_picker_row.pack(fill="x", pady=(0, 6))

        self.file_path_entry = ctk.CTkEntry(
            file_picker_row,
            placeholder_text="Chọn tệp Word (.docx) hoặc Text (.txt)...",
            height=34
        )
        self.file_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(
            file_picker_row,
            text="📂 Chọn file...",
            width=105,
            height=34,
            command=self._browse_exam_file
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            file_picker_row,
            text="📄 Tải mẫu",
            width=85,
            height=34,
            fg_color="gray50",
            hover_color="gray40",
            command=self._save_sample_file
        ).pack(side="left")

        self.file_status_label = ctk.CTkLabel(
            self.file_frame,
            text="Chưa chọn tệp. Hãy chọn file .docx hoặc .txt để nạp toàn bộ câu hỏi vào đề thi.",
            font=("Helvetica", 11),
            text_color="gray60"
        )
        self.file_status_label.pack(anchor="w", pady=(0, 4))

        tbl_file_box = ctk.CTkFrame(self.file_frame, height=200)
        tbl_file_box.pack(fill="both", expand=True)

        file_cols = ("stt", "content", "diff", "correct")
        self.file_tree = ttk.Treeview(tbl_file_box, columns=file_cols, show="headings", height=7, selectmode="browse")
        self.file_tree.heading("stt", text="#")
        self.file_tree.heading("content", text="Nội dung câu hỏi")
        self.file_tree.heading("diff", text="Độ khó")
        self.file_tree.heading("correct", text="Đ/A")

        self.file_tree.column("stt", width=35, anchor="center")
        self.file_tree.column("content", width=420, anchor="w")
        self.file_tree.column("diff", width=70, anchor="center")
        self.file_tree.column("correct", width=50, anchor="center")

        f_scroll = ttk.Scrollbar(tbl_file_box, orient="vertical", command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=f_scroll.set)
        self.file_tree.pack(side="left", fill="both", expand=True)
        f_scroll.pack(side="right", fill="y")

        # Action Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=2, column=0, padx=25, pady=(15, 20), sticky="ew")
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            btn_frame,
            text="Hủy",
            fg_color="gray50",
            hover_color="gray40",
            command=self.destroy,
            height=38
        ).grid(row=0, column=0, padx=(0, 10), sticky="ew")

        self.create_btn = ctk.CTkButton(
            btn_frame,
            text="Tạo đề thi",
            fg_color=SUCCESS_COLOR,
            hover_color="#218838",
            command=self._create_exam,
            height=38
        )
        self.create_btn.grid(row=0, column=1, padx=(10, 0), sticky="ew")

        # Load questions for initial subject
        self._load_subject_questions()

    def _on_mode_changed(self, mode_str):
        self.random_frame.grid_forget()
        self.manual_frame.grid_forget()
        self.file_frame.grid_forget()

        if mode_str == "Ngẫu nhiên":
            self.random_frame.grid(row=5, column=0, sticky="ew", pady=(5, 10))
        elif mode_str == "Chọn thủ công":
            self.manual_frame.grid(row=5, column=0, sticky="nsew", pady=(5, 10))
            self._populate_manual_questions()
        elif mode_str == "📁 Nhập từ file":
            self.file_frame.grid(row=5, column=0, sticky="nsew", pady=(5, 10))

    def _browse_exam_file(self):
        filetypes = [
            ("Tệp trắc nghiệm (*.docx, *.txt)", "*.docx;*.txt"),
            ("Microsoft Word Document (*.docx)", "*.docx"),
            ("Văn bản thuần (*.txt)", "*.txt"),
            ("Tất cả tệp", "*.*")
        ]
        chosen = filedialog.askopenfilename(
            parent=self,
            title="Chọn file đề thi trắc nghiệm",
            filetypes=filetypes
        )
        if not chosen:
            return

        self.file_path_entry.delete(0, "end")
        self.file_path_entry.insert(0, chosen)

        for item in self.file_tree.get_children():
            self.file_tree.delete(item)

        questions, errors = QuestionParser.parse_file(chosen)
        self.file_imported_questions = questions

        for idx, q in enumerate(questions, 1):
            c_prev = q["content"].replace("\n", " ")[:60]
            self.file_tree.insert("", "end", values=(idx, c_prev, q["difficulty"], q["correct_answer"]))

        if questions:
            msg = f"✅ Nhận diện: {len(questions)} câu hỏi hợp lệ!"
            if errors:
                msg += f" (Bỏ qua {len(errors)} câu lỗi)"
            self.file_status_label.configure(text=msg, text_color=SUCCESS_COLOR)
        else:
            self.file_status_label.configure(text="❌ Không tìm thấy câu hỏi hợp lệ trong tệp!", text_color=DANGER_COLOR)

    def _save_sample_file(self):
        sample_docx = "/home/khoile/Documents/QuizApp/database/mau_cau_hoi.docx"
        dest_file = filedialog.asksaveasfilename(
            parent=self,
            title="Lưu file đề thi mẫu",
            defaultextension=".docx",
            filetypes=[("Microsoft Word (*.docx)", "*.docx"), ("Văn bản (*.txt)", "*.txt")],
            initialfile="mau_de_thi.docx"
        )
        if not dest_file:
            return

        try:
            if dest_file.endswith(".txt"):
                src_txt = "/home/khoile/Documents/QuizApp/database/mau_cau_hoi.txt"
                shutil.copyfile(src_txt, dest_file)
            else:
                shutil.copyfile(sample_docx, dest_file)
            show_info("Đã lưu mẫu", f"Đã lưu tệp mẫu thành công tại:\n{dest_file}", parent=self)
        except Exception as e:
            show_error("Lỗi sao chép", f"Không thể lưu file mẫu: {e}", parent=self)

    def _on_subject_changed(self, _):
        self._load_subject_questions()

    def _load_subject_questions(self):
        subj_id = self.subject_map.get(self.subj_var.get())
        if not subj_id:
            return

        def worker():
            try:
                resp = self.connection.send_request("GET_QUESTIONS", data={"subject_id": subj_id}, token=self.token)
                if resp and resp.get("status") == "SUCCESS":
                    self.subject_questions = resp.get("data") or []
                    # Filter questions belonging to this subject if server returns all
                    self.subject_questions = [q for q in self.subject_questions if q.get("subject_id") == subj_id or not q.get("subject_id")]
                else:
                    self.subject_questions = []

                self.selected_question_ids.clear()
                self.after(0, self._populate_manual_questions)
            except Exception as e:
                print(f"[ExamCreator] Error loading questions: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def _populate_manual_questions(self):
        for item in self.q_tree.get_children():
            self.q_tree.delete(item)

        for q in self.subject_questions:
            qid = q.get("id")
            is_sel = "✓" if qid in self.selected_question_ids else ""
            preview = str(q.get("content", "")).replace("\n", " ")[:60]
            self.q_tree.insert("", "end", iid=str(qid), values=(is_sel, qid, preview, q.get("difficulty", "MEDIUM")))

        self.manual_count_label.configure(text=f"Đã chọn: {len(self.selected_question_ids)} câu")

    def _toggle_question_selection(self, event):
        item = self.q_tree.identify_row(event.y)
        if not item:
            return
        qid = int(item)
        if qid in self.selected_question_ids:
            self.selected_question_ids.remove(qid)
            self.q_tree.set(item, "sel", "")
        else:
            self.selected_question_ids.add(qid)
            self.q_tree.set(item, "sel", "✓")
        self.manual_count_label.configure(text=f"Đã chọn: {len(self.selected_question_ids)} câu")

    def _create_exam(self):
        title = self.title_entry.get().strip()
        subj_id = self.subject_map.get(self.subj_var.get())
        dur_str = self.duration_entry.get().strip()

        if not title:
            show_error("Thiếu thông tin", "Vui lòng nhập tên đề thi!", parent=self)
            return

        if not subj_id:
            show_error("Lỗi", "Vui lòng chọn môn học hợp lệ!", parent=self)
            return

        try:
            duration = int(dur_str)
            if duration <= 0:
                raise ValueError()
        except ValueError:
            show_error("Sai dữ liệu", "Thời gian thi phải là số nguyên dương (phút)!", parent=self)
            return

        mode = self.mode_segmented.get()
        is_random = (mode == "Ngẫu nhiên")
        is_file = (mode == "📁 Nhập từ file")
        question_ids = []
        new_questions = []
        total_questions = 0

        if is_random:
            try:
                total_questions = int(self.num_questions_entry.get().strip())
                if total_questions <= 0:
                    raise ValueError()
            except ValueError:
                show_error("Sai dữ liệu", "Số lượng câu hỏi phải là số nguyên dương!", parent=self)
                return
        elif is_file:
            if not self.file_imported_questions:
                show_error("Thiếu câu hỏi", "Vui lòng chọn file (.docx / .txt) chứa ít nhất 1 câu hỏi hợp lệ!", parent=self)
                return
            new_questions = self.file_imported_questions
            total_questions = len(new_questions)
        else:
            if not self.selected_question_ids:
                show_error("Thiếu câu hỏi", "Vui lòng chọn ít nhất 1 câu hỏi cho đề thi!", parent=self)
                return
            question_ids = list(self.selected_question_ids)
            total_questions = len(question_ids)

        self.create_btn.configure(state="disabled", text="Đang tạo...")

        def worker():
            try:
                payload = {
                    "title": title,
                    "subject_id": subj_id,
                    "duration_minutes": duration,
                    "total_questions": total_questions,
                    "question_ids": question_ids,
                    "new_questions": new_questions,
                    "random": is_random
                }
                resp = self.connection.send_request("CREATE_EXAM", data=payload, token=self.token)
                self.after(0, lambda: self._handle_result(resp))
            except Exception as e:
                self.after(0, lambda: self._handle_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_result(self, resp):
        self.create_btn.configure(state="normal", text="Tạo đề thi")
        if resp and resp.get("status") == "SUCCESS":
            show_info("Thành công", resp.get("message", "Đã tạo đề thi thành công!"), parent=self)
            if self.on_save_success:
                self.on_save_success()
            self.destroy()
        else:
            show_error("Thất bại", resp.get("message", "Không thể tạo đề thi!"), parent=self)

    def _handle_error(self, err):
        self.create_btn.configure(state="normal", text="Tạo đề thi")
        show_error("Lỗi kết nối", err, parent=self)


class ExamCreatorPanel(ctk.CTkFrame):
    """
    Teacher panel for managing exams: Create exam, Start exam, End exam, Delete exam.
    """

    def __init__(self, master, connection: ServerConnection, token: str, **kwargs):
        super().__init__(master, **kwargs)
        self.connection = connection
        self.token = token
        self.exams_cache: List[Dict[str, Any]] = []
        self.subjects_cache: List[Dict[str, Any]] = []

        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # 1. Title bar
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="📋 Quản lý Đề thi",
            font=("Helvetica", 20, "bold")
        ).grid(row=0, column=0, sticky="w")

        # 2. Controls & Actions Toolbar
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        toolbar.grid_columnconfigure(0, weight=1)

        # Left filter
        left_box = ctk.CTkFrame(toolbar, fg_color="transparent")
        left_box.grid(row=0, column=0, sticky="w")

        self.search_entry = ctk.CTkEntry(
            left_box,
            placeholder_text="🔍 Tìm tên đề thi...",
            width=220,
            height=34
        )
        self.search_entry.grid(row=0, column=0, padx=(0, 8))
        self.search_entry.bind("<KeyRelease>", lambda e: self._apply_filter())

        self.status_filter_var = ctk.StringVar(value="Tất cả trạng thái")
        self.status_filter_menu = ctk.CTkOptionMenu(
            left_box,
            values=["Tất cả trạng thái", "DRAFT", "ACTIVE", "ENDED"],
            variable=self.status_filter_var,
            command=lambda v: self._apply_filter(),
            width=150,
            height=34
        )
        self.status_filter_menu.grid(row=0, column=1, padx=(0, 8))

        self.refresh_btn = ctk.CTkButton(
            left_box,
            text="🔄",
            width=40,
            height=34,
            fg_color="gray40",
            hover_color="gray30",
            command=self.refresh_data
        )
        self.refresh_btn.grid(row=0, column=2)

        # Right buttons: Tạo đề, Bắt đầu thi, Kết thúc thi, Xóa
        right_box = ctk.CTkFrame(toolbar, fg_color="transparent")
        right_box.grid(row=0, column=1, sticky="e")

        self.create_btn = ctk.CTkButton(
            right_box,
            text="➕ Tạo đề",
            width=90,
            height=34,
            fg_color=SUCCESS_COLOR,
            hover_color="#218838",
            command=self._open_create_dialog
        )
        self.create_btn.grid(row=0, column=0, padx=(0, 6))

        self.start_btn = ctk.CTkButton(
            right_box,
            text="▶️ Bắt đầu thi",
            width=110,
            height=34,
            fg_color=PRIMARY_COLOR,
            hover_color=PRIMARY_HOVER,
            command=self._start_selected_exam
        )
        self.start_btn.grid(row=0, column=1, padx=(0, 6))

        self.end_btn = ctk.CTkButton(
            right_box,
            text="⏹️ Kết thúc",
            width=95,
            height=34,
            fg_color=WARNING_COLOR,
            hover_color="#d3680e",
            command=self._end_selected_exam
        )
        self.end_btn.grid(row=0, column=2, padx=(0, 6))

        self.delete_btn = ctk.CTkButton(
            right_box,
            text="🗑️ Xóa",
            width=70,
            height=34,
            fg_color=DANGER_COLOR,
            hover_color="#bd2130",
            command=self._delete_selected_exam
        )
        self.delete_btn.grid(row=0, column=3)

        # 3. Treeview Table
        table_frame = ctk.CTkFrame(self, corner_radius=8)
        table_frame.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="nsew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        columns = ("id", "title", "subject", "duration", "questions", "status", "start_time", "end_time")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )
        style = ttk.Style()
        style_treeview(style)

        self.tree.heading("id", text="ID")
        self.tree.heading("title", text="Tên đề thi")
        self.tree.heading("subject", text="Môn học")
        self.tree.heading("duration", text="Thời gian")
        self.tree.heading("questions", text="Số câu")
        self.tree.heading("status", text="Trạng thái")
        self.tree.heading("start_time", text="Bắt đầu")
        self.tree.heading("end_time", text="Kết thúc")

        self.tree.column("id", width=45, anchor="center")
        self.tree.column("title", width=220, anchor="w")
        self.tree.column("subject", width=140, anchor="w")
        self.tree.column("duration", width=90, anchor="center")
        self.tree.column("questions", width=70, anchor="center")
        self.tree.column("status", width=95, anchor="center")
        self.tree.column("start_time", width=130, anchor="center")
        self.tree.column("end_time", width=130, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # 4. Status Bar
        self.status_label = ctk.CTkLabel(
            self,
            text="Đang tải danh sách đề thi...",
            font=("Helvetica", 11),
            text_color="gray60"
        )
        self.status_label.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="w")

    def refresh_data(self):
        self.status_label.configure(text="Đang làm mới đề thi...")

        def worker():
            try:
                e_resp = self.connection.send_request("GET_EXAMS", token=self.token)
                s_resp = self.connection.send_request("GET_SUBJECTS", token=self.token)
                self.after(0, lambda: self._on_data_loaded(e_resp, s_resp))
            except Exception as e:
                self.after(0, lambda: self._on_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_data_loaded(self, e_resp, s_resp):
        if e_resp and e_resp.get("status") == "SUCCESS":
            self.exams_cache = e_resp.get("data") or []
        else:
            self.exams_cache = []

        if s_resp and s_resp.get("status") == "SUCCESS":
            self.subjects_cache = s_resp.get("data") or []

        self._apply_filter()

    def _on_error(self, err):
        self.status_label.configure(text=f"Lỗi: {err}")
        show_error("Lỗi kết nối", err, parent=self)

    def _apply_filter(self):
        query = self.search_entry.get().strip().lower()
        sel_status = self.status_filter_var.get()

        for item in self.tree.get_children():
            self.tree.delete(item)

        subj_lookup = {s.get("id"): s.get("name") for s in self.subjects_cache}

        count = 0
        for exam in self.exams_cache:
            title = str(exam.get("title", "")).lower()
            status = str(exam.get("status", "DRAFT"))
            subj_name = exam.get("subject_name") or subj_lookup.get(exam.get("subject_id"), "-")

            if query and query not in title:
                continue
            if sel_status != "Tất cả trạng thái" and status != sel_status:
                continue

            start_t = str(exam.get("start_time", "") or "")[:16]
            end_t = str(exam.get("end_time", "") or "")[:16]

            self.tree.insert(
                "",
                "end",
                iid=str(exam.get("id")),
                values=(
                    exam.get("id"),
                    exam.get("title"),
                    subj_name,
                    f"{exam.get('duration_minutes', 30)} ph",
                    exam.get("total_questions", 0),
                    status,
                    start_t or "-",
                    end_t or "-"
                )
            )
            count += 1

        self.status_label.configure(text=f"Hiển thị {count}/{len(self.exams_cache)} đề thi")

    def _get_selected_exam(self) -> Optional[Dict[str, Any]]:
        selected = self.tree.selection()
        if not selected:
            return None
        eid = int(selected[0])
        for e in self.exams_cache:
            if e.get("id") == eid:
                return e
        return None

    def _open_create_dialog(self):
        CreateExamDialog(
            self,
            self.connection,
            self.token,
            subjects=self.subjects_cache,
            on_save_success=self.refresh_data
        )

    def _start_selected_exam(self):
        exam = self._get_selected_exam()
        if not exam:
            show_warning("Chưa chọn", "Vui lòng chọn đề thi cần bắt đầu!", parent=self)
            return

        if exam.get("status") == "ACTIVE":
            show_info("Thông báo", "Đề thi này đang trong trạng thái hoạt động (ACTIVE)!", parent=self)
            return

        confirm = ask_yes_no(
            "Bắt đầu bài thi",
            f"Bạn có chắc muốn BẮT ĐẦU kỳ thi '{exam.get('title')}'?\nSinh viên sẽ có thể nhìn thấy và tham gia thi.",
            parent=self
        )
        if not confirm:
            return

        def worker():
            try:
                resp = self.connection.send_request("START_EXAM", data={"exam_id": exam["id"]}, token=self.token)
                self.after(0, lambda: self._on_action_result(resp, "Đã bắt đầu kỳ thi thành công!"))
            except Exception as e:
                self.after(0, lambda: show_error("Lỗi", str(e), parent=self))

        threading.Thread(target=worker, daemon=True).start()

    def _end_selected_exam(self):
        exam = self._get_selected_exam()
        if not exam:
            show_warning("Chưa chọn", "Vui lòng chọn đề thi cần kết thúc!", parent=self)
            return

        if exam.get("status") == "ENDED":
            show_info("Thông báo", "Đề thi này đã kết thúc trước đó!", parent=self)
            return

        confirm = ask_yes_no(
            "Kết thúc bài thi",
            f"Bạn có chắc muốn KẾT THÚC kỳ thi '{exam.get('title')}'?\nSinh viên sẽ không thể vào làm bài nữa.",
            parent=self
        )
        if not confirm:
            return

        def worker():
            try:
                resp = self.connection.send_request("END_EXAM", data={"exam_id": exam["id"]}, token=self.token)
                self.after(0, lambda: self._on_action_result(resp, "Đã kết thúc kỳ thi!"))
            except Exception as e:
                self.after(0, lambda: show_error("Lỗi", str(e), parent=self))

        threading.Thread(target=worker, daemon=True).start()

    def _delete_selected_exam(self):
        exam = self._get_selected_exam()
        if not exam:
            show_warning("Chưa chọn", "Vui lòng chọn đề thi cần xóa!", parent=self)
            return

        confirm = ask_yes_no(
            "Xác nhận xóa đề thi",
            f"Bạn có chắc muốn xóa đề thi '{exam.get('title')}'?",
            parent=self
        )
        if not confirm:
            return

        def worker():
            try:
                resp = self.connection.send_request("DELETE_EXAM", data={"exam_id": exam["id"]}, token=self.token)
                self.after(0, lambda: self._on_action_result(resp, "Đã xóa đề thi thành công!"))
            except Exception as e:
                self.after(0, lambda: show_error("Lỗi", str(e), parent=self))

        threading.Thread(target=worker, daemon=True).start()

    def _on_action_result(self, resp, success_msg: str):
        if resp and resp.get("status") == "SUCCESS":
            show_info("Thành công", resp.get("message") or success_msg, parent=self)
            self.refresh_data()
        else:
            show_error("Thất bại", resp.get("message", "Thao tác không thành công!"), parent=self)
