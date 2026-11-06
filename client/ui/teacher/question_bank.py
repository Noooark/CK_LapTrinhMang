import threading
import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional, List
import customtkinter as ctk

from client.network import ServerConnection
from client.ui.utils import (
    PRIMARY_COLOR, PRIMARY_HOVER, DANGER_COLOR, SUCCESS_COLOR,
    style_treeview, show_error, show_info, show_warning, ask_yes_no
)
from client.ui.teacher.question_importer import ImportQuestionsDialog


class QuestionDialog(ctk.CTkToplevel):
    """Dialog for creating or editing a quiz question."""

    def __init__(
        self,
        parent,
        connection: ServerConnection,
        token: str,
        subjects: List[Dict[str, Any]],
        question_data: Optional[Dict[str, Any]] = None,
        on_save_success=None
    ):
        super().__init__(parent)
        self.connection = connection
        self.token = token
        self.subjects = subjects
        self.question_data = question_data
        self.on_save_success = on_save_success
        self.is_edit = question_data is not None

        self.title("Chỉnh sửa câu hỏi" if self.is_edit else "Thêm câu hỏi mới")
        self.geometry("620x650")
        self.minsize(500, 480)
        self.resizable(True, True)
        self.transient(parent)
        self.lift()
        self.focus_force()
        self.after(100, self._safe_grab)

        self._build_ui()
        self._populate_fields()

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
        title_text = "Chỉnh sửa câu hỏi trắc nghiệm" if self.is_edit else "Thêm câu hỏi trắc nghiệm mới"
        header = ctk.CTkLabel(self, text=title_text, font=("Helvetica", 18, "bold"))
        header.grid(row=0, column=0, padx=25, pady=(15, 10), sticky="w")

        # Scrollable / Form container
        form = ctk.CTkScrollableFrame(self, fg_color="transparent")
        form.grid(row=1, column=0, padx=25, pady=0, sticky="nsew")
        form.grid_columnconfigure(0, weight=1)

        # Row 0: Subject & Difficulty in one row
        top_meta = ctk.CTkFrame(form, fg_color="transparent")
        top_meta.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        top_meta.grid_columnconfigure((0, 1), weight=1)

        # Subject dropdown
        ctk.CTkLabel(top_meta, text="Môn học:", font=("Helvetica", 12, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.subject_map = {}
        subj_names = []
        for s in self.subjects:
            name = s.get("name", f"Subject #{s.get('id')}")
            subj_names.append(name)
            self.subject_map[name] = s.get("id")

        if not subj_names:
            subj_names = ["-- Chưa có môn học --"]

        self.subj_var = ctk.StringVar(value=subj_names[0])
        self.subj_menu = ctk.CTkOptionMenu(top_meta, values=subj_names, variable=self.subj_var, height=36)
        self.subj_menu.grid(row=1, column=0, sticky="ew", padx=(0, 10))

        # Difficulty dropdown
        ctk.CTkLabel(top_meta, text="Độ khó:", font=("Helvetica", 12, "bold")).grid(row=0, column=1, sticky="w", pady=(0, 2))
        self.diff_var = ctk.StringVar(value="MEDIUM")
        self.diff_menu = ctk.CTkOptionMenu(
            top_meta,
            values=["EASY", "MEDIUM", "HARD"],
            variable=self.diff_var,
            height=36
        )
        self.diff_menu.grid(row=1, column=1, sticky="ew")

        # Content Textarea
        ctk.CTkLabel(form, text="Nội dung câu hỏi:", font=("Helvetica", 12, "bold")).grid(row=1, column=0, sticky="w", pady=(5, 2))
        self.content_text = ctk.CTkTextbox(form, height=100, font=("Helvetica", 12))
        self.content_text.grid(row=2, column=0, sticky="ew", pady=(0, 12))

        # Options A, B, C, D
        ctk.CTkLabel(form, text="Phương án lựa chọn:", font=("Helvetica", 12, "bold")).grid(row=3, column=0, sticky="w", pady=(5, 4))

        self.opt_a_entry = ctk.CTkEntry(form, placeholder_text="Đáp án A", height=36)
        self.opt_a_entry.grid(row=4, column=0, sticky="ew", pady=3)

        self.opt_b_entry = ctk.CTkEntry(form, placeholder_text="Đáp án B", height=36)
        self.opt_b_entry.grid(row=5, column=0, sticky="ew", pady=3)

        self.opt_c_entry = ctk.CTkEntry(form, placeholder_text="Đáp án C", height=36)
        self.opt_c_entry.grid(row=6, column=0, sticky="ew", pady=3)

        self.opt_d_entry = ctk.CTkEntry(form, placeholder_text="Đáp án D", height=36)
        self.opt_d_entry.grid(row=7, column=0, sticky="ew", pady=3)

        # Correct Answer Selection
        ctk.CTkLabel(form, text="Đáp án chính xác:", font=("Helvetica", 12, "bold")).grid(row=8, column=0, sticky="w", pady=(10, 4))
        self.correct_var = ctk.StringVar(value="A")
        self.correct_segment = ctk.CTkSegmentedButton(
            form,
            values=["A", "B", "C", "D"],
            variable=self.correct_var,
            selected_color=SUCCESS_COLOR,
            selected_hover_color="#218838",
            height=36
        )
        self.correct_segment.grid(row=9, column=0, sticky="ew", pady=(0, 10))

        # Action Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=2, column=0, padx=25, pady=(10, 15), sticky="ew")
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            btn_frame,
            text="Hủy",
            fg_color="gray50",
            hover_color="gray40",
            command=self.destroy,
            height=38
        ).grid(row=0, column=0, padx=(0, 10), sticky="ew")

        self.save_btn = ctk.CTkButton(
            btn_frame,
            text="Lưu câu hỏi",
            fg_color=PRIMARY_COLOR,
            hover_color=PRIMARY_HOVER,
            command=self._save_question,
            height=38
        )
        self.save_btn.grid(row=0, column=1, padx=(10, 0), sticky="ew")

    def _populate_fields(self):
        if self.is_edit and self.question_data:
            self.content_text.insert("1.0", self.question_data.get("content", ""))
            self.opt_a_entry.insert(0, self.question_data.get("option_a", ""))
            self.opt_b_entry.insert(0, self.question_data.get("option_b", ""))
            self.opt_c_entry.insert(0, self.question_data.get("option_c", ""))
            self.opt_d_entry.insert(0, self.question_data.get("option_d", ""))
            self.correct_var.set(self.question_data.get("correct_answer", "A"))
            self.diff_var.set(self.question_data.get("difficulty", "MEDIUM"))

            subj_id = self.question_data.get("subject_id")
            for name, sid in self.subject_map.items():
                if sid == subj_id:
                    self.subj_var.set(name)
                    break

    def _save_question(self):
        content = self.content_text.get("1.0", "end-1c").strip()
        opt_a = self.opt_a_entry.get().strip()
        opt_b = self.opt_b_entry.get().strip()
        opt_c = self.opt_c_entry.get().strip()
        opt_d = self.opt_d_entry.get().strip()
        correct_ans = self.correct_var.get()
        difficulty = self.diff_var.get()
        subject_id = self.subject_map.get(self.subj_var.get())

        if not subject_id:
            show_error("Lỗi", "Vui lòng chọn môn học hợp lệ!", parent=self)
            return

        if not content:
            show_error("Thiếu thông tin", "Vui lòng nhập nội dung câu hỏi!", parent=self)
            return

        if not all([opt_a, opt_b, opt_c, opt_d]):
            show_error("Thiếu thông tin", "Vui lòng nhập đủ 4 lựa chọn A, B, C, D!", parent=self)
            return

        self.save_btn.configure(state="disabled", text="Đang lưu...")

        def worker():
            try:
                payload = {
                    "subject_id": subject_id,
                    "content": content,
                    "option_a": opt_a,
                    "option_b": opt_b,
                    "option_c": opt_c,
                    "option_d": opt_d,
                    "correct_answer": correct_ans,
                    "difficulty": difficulty
                }

                if self.is_edit:
                    payload["question_id"] = self.question_data["id"]
                    resp = self.connection.send_request("UPDATE_QUESTION", data=payload, token=self.token)
                else:
                    resp = self.connection.send_request("CREATE_QUESTION", data=payload, token=self.token)

                self.after(0, lambda: self._handle_result(resp))
            except Exception as e:
                self.after(0, lambda: self._handle_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_result(self, resp):
        self.save_btn.configure(state="normal", text="Lưu câu hỏi")
        if resp and resp.get("status") == "SUCCESS":
            show_info("Thành công", resp.get("message", "Đã lưu câu hỏi thành công!"), parent=self)
            if self.on_save_success:
                self.on_save_success()
            self.destroy()
        else:
            show_error("Thất bại", resp.get("message", "Không thể lưu câu hỏi!"), parent=self)

    def _handle_error(self, err):
        self.save_btn.configure(state="normal", text="Lưu câu hỏi")
        show_error("Lỗi kết nối", err, parent=self)


class QuestionBankPanel(ctk.CTkFrame):
    """
    Teacher panel for managing quiz questions: filter by subject & difficulty, CRUD questions.
    """

    def __init__(self, master, connection: ServerConnection, token: str, **kwargs):
        super().__init__(master, **kwargs)
        self.connection = connection
        self.token = token
        self.questions_cache: List[Dict[str, Any]] = []
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
            text="📝 Ngân hàng Câu hỏi",
            font=("Helvetica", 20, "bold")
        ).grid(row=0, column=0, sticky="w")

        # 2. Filter & Action Toolbar
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        toolbar.grid_columnconfigure(0, weight=1)

        # Left filter section
        filter_box = ctk.CTkFrame(toolbar, fg_color="transparent")
        filter_box.grid(row=0, column=0, sticky="w")

        # Search field
        self.search_entry = ctk.CTkEntry(
            filter_box,
            placeholder_text="🔍 Tìm nội dung câu hỏi...",
            width=220,
            height=34
        )
        self.search_entry.grid(row=0, column=0, padx=(0, 8))
        self.search_entry.bind("<KeyRelease>", lambda e: self._apply_filter())

        # Subject filter
        self.subj_filter_var = ctk.StringVar(value="Tất cả môn")
        self.subj_filter_menu = ctk.CTkOptionMenu(
            filter_box,
            values=["Tất cả môn"],
            variable=self.subj_filter_var,
            command=lambda v: self._apply_filter(),
            width=150,
            height=34
        )
        self.subj_filter_menu.grid(row=0, column=1, padx=(0, 8))

        # Difficulty filter
        self.diff_filter_var = ctk.StringVar(value="Tất cả độ khó")
        self.diff_filter_menu = ctk.CTkOptionMenu(
            filter_box,
            values=["Tất cả độ khó", "EASY", "MEDIUM", "HARD"],
            variable=self.diff_filter_var,
            command=lambda v: self._apply_filter(),
            width=130,
            height=34
        )
        self.diff_filter_menu.grid(row=0, column=2, padx=(0, 8))

        # Refresh button
        self.refresh_btn = ctk.CTkButton(
            filter_box,
            text="🔄",
            width=40,
            height=34,
            fg_color="gray40",
            hover_color="gray30",
            command=self.refresh_data
        )
        self.refresh_btn.grid(row=0, column=3)

        # Right Action Buttons
        btn_box = ctk.CTkFrame(toolbar, fg_color="transparent")
        btn_box.grid(row=0, column=1, sticky="e")

        self.import_btn = ctk.CTkButton(
            btn_box,
            text="📥 Import file (.docx/.txt)",
            width=150,
            height=34,
            fg_color="#17a2b8",
            hover_color="#138496",
            command=self._open_import_dialog
        )
        self.import_btn.grid(row=0, column=0, padx=(0, 6))

        self.add_btn = ctk.CTkButton(
            btn_box,
            text="➕ Thêm thủ công",
            width=115,
            height=34,
            fg_color=SUCCESS_COLOR,
            hover_color="#218838",
            command=self._open_add_dialog
        )
        self.add_btn.grid(row=0, column=1, padx=(0, 6))

        self.edit_btn = ctk.CTkButton(
            btn_box,
            text="✏️ Sửa",
            width=65,
            height=34,
            fg_color=PRIMARY_COLOR,
            hover_color=PRIMARY_HOVER,
            command=self._open_edit_dialog
        )
        self.edit_btn.grid(row=0, column=2, padx=(0, 6))

        self.delete_btn = ctk.CTkButton(
            btn_box,
            text="🗑️ Xóa",
            width=65,
            height=34,
            fg_color=DANGER_COLOR,
            hover_color="#bd2130",
            command=self._delete_selected_question
        )
        self.delete_btn.grid(row=0, column=3)

        # 3. Treeview Table
        table_frame = ctk.CTkFrame(self, corner_radius=8)
        table_frame.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="nsew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        columns = ("id", "subject", "content", "diff", "correct")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )
        style = ttk.Style()
        style_treeview(style)

        self.tree.heading("id", text="ID")
        self.tree.heading("subject", text="Môn học")
        self.tree.heading("content", text="Nội dung câu hỏi")
        self.tree.heading("diff", text="Độ khó")
        self.tree.heading("correct", text="Đáp án")

        self.tree.column("id", width=50, anchor="center")
        self.tree.column("subject", width=160, anchor="w")
        self.tree.column("content", width=550, anchor="w")
        self.tree.column("diff", width=100, anchor="center")
        self.tree.column("correct", width=80, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.tree.bind("<Double-1>", lambda event: self._open_edit_dialog())

        # 4. Status Bar
        self.status_label = ctk.CTkLabel(
            self,
            text="Đang tải ngân hàng câu hỏi...",
            font=("Helvetica", 11),
            text_color="gray60"
        )
        self.status_label.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="w")

    def refresh_data(self):
        self.status_label.configure(text="Đang làm mới câu hỏi...")

        def worker():
            try:
                q_resp = self.connection.send_request("GET_QUESTIONS", token=self.token)
                s_resp = self.connection.send_request("GET_SUBJECTS", token=self.token)
                self.after(0, lambda: self._on_data_loaded(q_resp, s_resp))
            except Exception as e:
                self.after(0, lambda: self._on_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_data_loaded(self, q_resp, s_resp):
        if q_resp and q_resp.get("status") == "SUCCESS":
            self.questions_cache = q_resp.get("data") or []
        else:
            self.questions_cache = []

        if s_resp and s_resp.get("status") == "SUCCESS":
            self.subjects_cache = s_resp.get("data") or []
            # Update subject dropdown in filter
            names = ["Tất cả môn"] + [s.get("name") for s in self.subjects_cache if s.get("name")]
            self.subj_filter_menu.configure(values=names)

        self._apply_filter()

    def _on_error(self, err):
        self.status_label.configure(text=f"Lỗi: {err}")
        show_error("Lỗi kết nối", err, parent=self)

    def _apply_filter(self):
        query = self.search_entry.get().strip().lower()
        sel_subj = self.subj_filter_var.get()
        sel_diff = self.diff_filter_var.get()

        for item in self.tree.get_children():
            self.tree.delete(item)

        subj_lookup = {s.get("id"): s.get("name") for s in self.subjects_cache}

        count = 0
        for q in self.questions_cache:
            content = str(q.get("content", "")).lower()
            diff = str(q.get("difficulty", "MEDIUM"))
            subj_name = q.get("subject_name") or subj_lookup.get(q.get("subject_id"), "-")

            if query and query not in content:
                continue
            if sel_subj != "Tất cả môn" and subj_name != sel_subj:
                continue
            if sel_diff != "Tất cả độ khó" and diff != sel_diff:
                continue

            # Preview first 80 characters of content
            preview = q.get("content", "").replace("\n", " ")
            if len(preview) > 80:
                preview = preview[:77] + "..."

            self.tree.insert(
                "",
                "end",
                iid=str(q.get("id")),
                values=(
                    q.get("id"),
                    subj_name,
                    preview,
                    diff,
                    q.get("correct_answer", "A")
                )
            )
            count += 1

        self.status_label.configure(text=f"Hiển thị {count}/{len(self.questions_cache)} câu hỏi")

    def _get_selected_question(self) -> Optional[Dict[str, Any]]:
        selected = self.tree.selection()
        if not selected:
            return None
        qid = int(selected[0])
        for q in self.questions_cache:
            if q.get("id") == qid:
                return q
        return None

    def _open_import_dialog(self):
        selected_subj = self.subj_filter_var.get()
        init_id = None
        for s in self.subjects_cache:
            if s.get("name") == selected_subj:
                init_id = s.get("id")
                break

        ImportQuestionsDialog(
            self,
            self.connection,
            self.token,
            subjects=self.subjects_cache,
            initial_subject_id=init_id,
            on_import_success=self.refresh_data
        )

    def _open_add_dialog(self):
        QuestionDialog(
            self,
            self.connection,
            self.token,
            subjects=self.subjects_cache,
            question_data=None,
            on_save_success=self.refresh_data
        )

    def _open_edit_dialog(self):
        question = self._get_selected_question()
        if not question:
            show_warning("Chưa chọn", "Vui lòng chọn câu hỏi cần sửa!", parent=self)
            return
        QuestionDialog(
            self,
            self.connection,
            self.token,
            subjects=self.subjects_cache,
            question_data=question,
            on_save_success=self.refresh_data
        )

    def _delete_selected_question(self):
        question = self._get_selected_question()
        if not question:
            show_warning("Chưa chọn", "Vui lòng chọn câu hỏi cần xóa!", parent=self)
            return

        confirm = ask_yes_no(
            "Xác nhận xóa câu hỏi",
            f"Bạn có chắc muốn xóa câu hỏi #{question.get('id')}?",
            parent=self
        )
        if not confirm:
            return

        def worker():
            try:
                resp = self.connection.send_request("DELETE_QUESTION", data={"question_id": question["id"]}, token=self.token)
                self.after(0, lambda: self._on_delete_result(resp))
            except Exception as e:
                self.after(0, lambda: show_error("Lỗi", str(e), parent=self))

        threading.Thread(target=worker, daemon=True).start()

    def _on_delete_result(self, resp):
        if resp and resp.get("status") == "SUCCESS":
            show_info("Thành công", resp.get("message", "Đã xóa câu hỏi thành công!"), parent=self)
            self.refresh_data()
        else:
            show_error("Thất bại", resp.get("message", "Không thể xóa câu hỏi!"), parent=self)
