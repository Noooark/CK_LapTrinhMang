import threading
import tkinter as tk
from tkinter import ttk, filedialog
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
        initial_subject_id: Optional[int] = None,
        on_save_success=None
    ):
        super().__init__(parent)
        self.connection = connection
        self.token = token
        self.subjects = subjects
        self.question_data = question_data
        self.initial_subject_id = initial_subject_id
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
        elif self.initial_subject_id:
            for name, sid in self.subject_map.items():
                if sid == self.initial_subject_id:
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


class SubjectBankDialog(ctk.CTkToplevel):
    """
    Dialog displaying the full Question Bank for a specific subject,
    styled similarly to ViewExamDialog in Exam Management.
    """

    def __init__(
        self,
        parent,
        connection: ServerConnection,
        token: str,
        subject_data: Dict[str, Any],
        subjects_list: List[Dict[str, Any]],
        on_data_changed=None
    ):
        super().__init__(parent)
        self.connection = connection
        self.token = token
        self.subject_data = subject_data
        self.subjects_list = subjects_list
        self.on_data_changed = on_data_changed
        self.questions: List[Dict[str, Any]] = []

        subj_name = subject_data.get("name", f"Môn #{subject_data.get('id')}")
        self.title(f"Ngân hàng Câu hỏi: {subj_name}")
        self.geometry("920x740")
        self.minsize(720, 520)
        self.resizable(True, True)
        self.transient(parent)
        self.lift()
        self.focus_force()
        self.after(100, self._safe_grab)

        self._build_ui()
        self._load_questions()

    def _safe_grab(self):
        try:
            if self.winfo_exists():
                self.grab_set()
        except Exception:
            pass

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        subj_name = self.subject_data.get("name", "")

        # 1. Top Header Banner
        header = ctk.CTkFrame(self, corner_radius=10)
        header.grid(row=0, column=0, padx=20, pady=(15, 8), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        top_row = ctk.CTkFrame(header, fg_color="transparent")
        top_row.grid(row=0, column=0, padx=15, pady=(12, 4), sticky="ew")
        top_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top_row,
            text=f"📂 Ngân hàng câu hỏi: {subj_name}",
            font=("Helvetica", 18, "bold")
        ).grid(row=0, column=0, sticky="w")

        btn_box = ctk.CTkFrame(top_row, fg_color="transparent")
        btn_box.grid(row=0, column=1, sticky="e")

        ctk.CTkButton(
            btn_box,
            text="📥 Import file (.docx/.txt)",
            width=145,
            height=32,
            fg_color="#17a2b8",
            hover_color="#138496",
            command=self._open_import
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_box,
            text="➕ Thêm câu hỏi",
            width=115,
            height=32,
            fg_color=SUCCESS_COLOR,
            hover_color="#218838",
            command=self._open_add
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_box,
            text="📄 Xuất Word",
            width=95,
            height=32,
            fg_color="gray50",
            hover_color="gray40",
            command=self._export_to_docx
        ).pack(side="left")

        # Stats banner
        self.stats_label = ctk.CTkLabel(
            header,
            text="⏳ Đang tải số lượng câu hỏi...",
            font=("Helvetica", 12),
            text_color="gray60"
        )
        self.stats_label.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="w")

        # 2. Filter Bar inside this Subject Bank
        filter_bar = ctk.CTkFrame(self, fg_color="transparent")
        filter_bar.grid(row=1, column=0, padx=20, pady=(0, 8), sticky="ew")
        filter_bar.grid_columnconfigure(0, weight=1)

        left_filter = ctk.CTkFrame(filter_bar, fg_color="transparent")
        left_filter.grid(row=0, column=0, sticky="w")

        self.search_entry = ctk.CTkEntry(
            left_filter,
            placeholder_text="🔍 Tìm nội dung câu hỏi trong môn này...",
            width=280,
            height=34
        )
        self.search_entry.grid(row=0, column=0, padx=(0, 8))
        self.search_entry.bind("<KeyRelease>", lambda e: self._render_questions())

        self.diff_var = ctk.StringVar(value="Tất cả độ khó")
        self.diff_menu = ctk.CTkOptionMenu(
            left_filter,
            values=["Tất cả độ khó", "EASY", "MEDIUM", "HARD"],
            variable=self.diff_var,
            command=lambda v: self._render_questions(),
            width=140,
            height=34
        )
        self.diff_menu.grid(row=0, column=1, padx=(0, 8))

        ctk.CTkButton(
            left_filter,
            text="🔄",
            width=36,
            height=34,
            fg_color="gray40",
            hover_color="gray30",
            command=self._load_questions
        ).grid(row=0, column=2)

        # 3. Scrollable list of Question Cards (Just like ViewExamDialog!)
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.grid(row=2, column=0, padx=20, pady=(0, 8), sticky="nsew")
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        self.loading_label = ctk.CTkLabel(
            self.scroll_frame,
            text="⏳ Đang nạp danh sách câu hỏi của ngân hàng...",
            font=("Helvetica", 13)
        )
        self.loading_label.pack(pady=40)

        # 4. Bottom bar
        bottom_bar = ctk.CTkFrame(self, fg_color="transparent")
        bottom_bar.grid(row=3, column=0, padx=20, pady=(5, 15), sticky="ew")
        bottom_bar.grid_columnconfigure(0, weight=1)

        self.count_label = ctk.CTkLabel(
            bottom_bar,
            text="",
            font=("Helvetica", 12, "bold"),
            text_color="gray60"
        )
        self.count_label.grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            bottom_bar,
            text="Đóng",
            width=100,
            height=36,
            fg_color="gray50",
            hover_color="gray40",
            command=self.destroy
        ).grid(row=0, column=1, sticky="e")

    def _load_questions(self):
        subj_id = self.subject_data.get("id")
        def worker():
            try:
                resp = self.connection.send_request("GET_QUESTIONS", data={"subject_id": subj_id}, token=self.token)
                self.after(0, lambda: self._on_questions_loaded(resp))
            except Exception as e:
                self.after(0, lambda: self._on_load_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_questions_loaded(self, resp):
        if resp and resp.get("status") == "SUCCESS":
            all_q = resp.get("data") or []
            subj_id = self.subject_data.get("id")
            self.questions = [q for q in all_q if q.get("subject_id") == subj_id]
        else:
            self.questions = []

        c_easy = sum(1 for q in self.questions if q.get("difficulty") == "EASY")
        c_med = sum(1 for q in self.questions if q.get("difficulty") == "MEDIUM")
        c_hard = sum(1 for q in self.questions if q.get("difficulty") == "HARD")

        self.stats_label.configure(
            text=f"Tổng số: {len(self.questions)} câu hỏi   |   🟢 {c_easy} Dễ   |   🟡 {c_med} Trung bình   |   🔴 {c_hard} Khó",
            text_color=("gray20", "gray85")
        )

        self._render_questions()

    def _on_load_error(self, err_msg):
        self.loading_label.configure(text=f"❌ Lỗi: {err_msg}", text_color=DANGER_COLOR)

    def _render_questions(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        query = self.search_entry.get().strip().lower()
        diff_filter = self.diff_var.get()

        filtered = []
        for q in self.questions:
            content = str(q.get("content", "")).lower()
            diff = str(q.get("difficulty", "MEDIUM"))
            if query and query not in content:
                continue
            if diff_filter != "Tất cả độ khó" and diff != diff_filter:
                continue
            filtered.append(q)

        if not filtered:
            msg = "ℹ️ Chưa có câu hỏi nào trong ngân hàng này." if not self.questions else "🔍 Không tìm thấy câu hỏi phù hợp với bộ lọc."
            ctk.CTkLabel(
                self.scroll_frame,
                text=msg,
                font=("Helvetica", 13),
                text_color="gray60"
            ).pack(pady=40)
            self.count_label.configure(text=f"Hiển thị 0/{len(self.questions)} câu hỏi")
            return

        self.count_label.configure(text=f"Hiển thị {len(filtered)}/{len(self.questions)} câu hỏi")

        for idx, q in enumerate(filtered, 1):
            self._render_question_card(idx, q)

    def _render_question_card(self, idx: int, q: Dict[str, Any]):
        card = ctk.CTkFrame(self.scroll_frame, corner_radius=8, fg_color=("gray92", "gray17"))
        card.pack(fill="x", pady=6, padx=4)
        card.grid_columnconfigure(0, weight=1)

        # Card Top Row: Câu #{idx} | Badge độ khó | Buttons [Sửa] [Xóa]
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(10, 4))
        top.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            top,
            text=f"Câu {idx} (ID #{q.get('id')}):",
            font=("Helvetica", 13, "bold")
        ).grid(row=0, column=0, sticky="w")

        diff = q.get("difficulty", "MEDIUM")
        diff_colors = {
            "EASY": ("#d4edda", "#155724"),
            "MEDIUM": ("#fff3cd", "#856404"),
            "HARD": ("#f8d7da", "#721c24")
        }
        diff_bg, diff_fg = diff_colors.get(diff, ("gray80", "black"))

        ctk.CTkLabel(
            top,
            text=f" {diff} ",
            font=("Helvetica", 10, "bold"),
            fg_color=diff_bg,
            text_color=diff_fg,
            corner_radius=4
        ).grid(row=0, column=1, sticky="w", padx=(10, 0))

        # Edit and Delete buttons on the right
        btn_sub = ctk.CTkFrame(top, fg_color="transparent")
        btn_sub.grid(row=0, column=2, sticky="e")

        ctk.CTkButton(
            btn_sub,
            text="✏️ Sửa",
            width=55,
            height=26,
            font=("Helvetica", 11),
            fg_color=PRIMARY_COLOR,
            hover_color=PRIMARY_HOVER,
            command=lambda q_data=q: self._edit_question(q_data)
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            btn_sub,
            text="🗑️ Xóa",
            width=55,
            height=26,
            font=("Helvetica", 11),
            fg_color=DANGER_COLOR,
            hover_color="#bd2130",
            command=lambda q_data=q: self._delete_question(q_data)
        ).pack(side="left")

        # Question Content
        ctk.CTkLabel(
            card,
            text=q.get("content", ""),
            font=("Helvetica", 13),
            justify="left",
            anchor="w",
            wraplength=800
        ).pack(fill="x", padx=14, pady=(2, 8))

        # Options A, B, C, D
        correct = str(q.get("correct_answer", "")).upper()
        options = [
            ("A", q.get("option_a", "")),
            ("B", q.get("option_b", "")),
            ("C", q.get("option_c", "")),
            ("D", q.get("option_d", ""))
        ]

        opts_frame = ctk.CTkFrame(card, fg_color="transparent")
        opts_frame.pack(fill="x", padx=14, pady=(0, 10))

        for letter, opt_text in options:
            is_correct = (letter == correct)
            opt_row = ctk.CTkFrame(
                opts_frame,
                fg_color=("#c3e6cb", "#1b3a1e") if is_correct else "transparent",
                corner_radius=6
            )
            opt_row.pack(fill="x", pady=2)

            prefix = f"✅ [{letter}]." if is_correct else f"    [{letter}]."
            txt_color = ("#155724", "#d4edda") if is_correct else None
            font_weight = "bold" if is_correct else "normal"

            lbl = ctk.CTkLabel(
                opt_row,
                text=f"{prefix} {opt_text}",
                font=("Helvetica", 12, font_weight),
                text_color=txt_color,
                justify="left",
                anchor="w",
                wraplength=780
            )
            lbl.pack(side="left", padx=8, pady=4)

    def _open_import(self):
        ImportQuestionsDialog(
            self,
            self.connection,
            self.token,
            subjects=self.subjects_list,
            initial_subject_id=self.subject_data.get("id"),
            on_import_success=self._on_sub_data_changed
        )

    def _open_add(self):
        QuestionDialog(
            self,
            self.connection,
            self.token,
            subjects=self.subjects_list,
            question_data=None,
            initial_subject_id=self.subject_data.get("id"),
            on_save_success=self._on_sub_data_changed
        )

    def _edit_question(self, q_data: Dict[str, Any]):
        QuestionDialog(
            self,
            self.connection,
            self.token,
            subjects=self.subjects_list,
            question_data=q_data,
            initial_subject_id=self.subject_data.get("id"),
            on_save_success=self._on_sub_data_changed
        )

    def _delete_question(self, q_data: Dict[str, Any]):
        qid = q_data.get("id")
        confirm = ask_yes_no(
            "Xác nhận xóa câu hỏi",
            f"Bạn có chắc muốn xóa câu hỏi #{qid} khỏi ngân hàng môn này?",
            parent=self
        )
        if not confirm:
            return

        def worker():
            try:
                resp = self.connection.send_request("DELETE_QUESTION", data={"id": qid, "question_id": qid}, token=self.token)
                self.after(0, lambda: self._on_delete_finished(resp))
            except Exception as e:
                self.after(0, lambda: show_error("Lỗi", str(e), parent=self))

        threading.Thread(target=worker, daemon=True).start()

    def _on_delete_finished(self, resp):
        if resp and resp.get("status") == "SUCCESS":
            show_info("Thành công", resp.get("message", "Đã xóa câu hỏi thành công!"), parent=self)
            self._on_sub_data_changed()
        else:
            show_error("Thất bại", resp.get("message", "Không thể xóa câu hỏi!"), parent=self)

    def _on_sub_data_changed(self):
        self._load_questions()
        if self.on_data_changed:
            self.on_data_changed()

    def _export_to_docx(self):
        if not self.questions:
            show_warning("Trống", "Ngân hàng môn này chưa có câu hỏi để xuất file!", parent=self)
            return

        subj_name = self.subject_data.get("name", "MonHoc")
        dest_file = filedialog.asksaveasfilename(
            parent=self,
            title="Lưu ngân hàng câu hỏi ra Word",
            defaultextension=".docx",
            filetypes=[("Microsoft Word Document (*.docx)", "*.docx")],
            initialfile=f"NganHang_{subj_name.replace(' ', '_')}.docx"
        )
        if not dest_file:
            return

        try:
            import docx
            doc = docx.Document()
            doc.add_heading(f"NGÂN HÀNG CÂU HỎI: {subj_name}", level=0)
            p = doc.add_paragraph()
            p.add_run(f"Tổng số câu hỏi: {len(self.questions)}\n").bold = True

            for idx, q in enumerate(self.questions, 1):
                p_q = doc.add_paragraph()
                p_q.add_run(f"Câu {idx}: {q.get('content', '')}\n").bold = True
                doc.add_paragraph(f"A. {q.get('option_a', '')}")
                doc.add_paragraph(f"B. {q.get('option_b', '')}")
                doc.add_paragraph(f"C. {q.get('option_c', '')}")
                doc.add_paragraph(f"D. {q.get('option_d', '')}")
                doc.add_paragraph(f"Đáp án đúng: {q.get('correct_answer', '')}  |  Độ khó: {q.get('difficulty', 'MEDIUM')}\n")

            doc.save(dest_file)
            show_info("Thành công", f"Đã xuất ngân hàng câu hỏi ra tệp:\n{dest_file}", parent=self)
        except Exception as e:
            show_error("Lỗi xuất file", f"Không thể lưu file Word: {e}", parent=self)


class QuestionBankPanel(ctk.CTkFrame):
    """
    Teacher panel for managing question banks by subject.
    Displays a list of subject banks, allowing teacher to open, view, and manage each bank.
    """

    def __init__(self, master, connection: ServerConnection, token: str, **kwargs):
        super().__init__(master, **kwargs)
        self.connection = connection
        self.token = token
        self.subjects_cache: List[Dict[str, Any]] = []
        self.questions_cache: List[Dict[str, Any]] = []

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
            text="📝 Quản lý Ngân hàng Câu hỏi",
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
            placeholder_text="🔍 Tìm tên môn học...",
            width=240,
            height=34
        )
        self.search_entry.grid(row=0, column=0, padx=(0, 8))
        self.search_entry.bind("<KeyRelease>", lambda e: self._apply_filter())

        self.refresh_btn = ctk.CTkButton(
            left_box,
            text="🔄",
            width=40,
            height=34,
            fg_color="gray40",
            hover_color="gray30",
            command=self.refresh_data
        )
        self.refresh_btn.grid(row=0, column=1)

        # Right buttons: Mở ngân hàng môn, Import file, Thêm câu hỏi
        right_box = ctk.CTkFrame(toolbar, fg_color="transparent")
        right_box.grid(row=0, column=1, sticky="e")

        self.open_btn = ctk.CTkButton(
            right_box,
            text="👁️ Mở ngân hàng môn",
            width=150,
            height=34,
            fg_color="#17a2b8",
            hover_color="#138496",
            command=self._open_selected_bank
        )
        self.open_btn.grid(row=0, column=0, padx=(0, 6))

        self.import_btn = ctk.CTkButton(
            right_box,
            text="📥 Import file",
            width=115,
            height=34,
            fg_color=PRIMARY_COLOR,
            hover_color=PRIMARY_HOVER,
            command=self._open_import_dialog
        )
        self.import_btn.grid(row=0, column=1, padx=(0, 6))

        self.add_btn = ctk.CTkButton(
            right_box,
            text="➕ Thêm câu hỏi",
            width=120,
            height=34,
            fg_color=SUCCESS_COLOR,
            hover_color="#218838",
            command=self._open_add_dialog
        )
        self.add_btn.grid(row=0, column=2)

        # 3. Treeview Table (List of Subject Banks)
        table_frame = ctk.CTkFrame(self, corner_radius=8)
        table_frame.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="nsew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        columns = ("id", "name", "desc", "total", "easy", "medium", "hard")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )
        style = ttk.Style()
        style_treeview(style)

        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Ngân hàng Môn học")
        self.tree.heading("desc", text="Mô tả môn")
        self.tree.heading("total", text="Tổng số câu")
        self.tree.heading("easy", text="Dễ")
        self.tree.heading("medium", text="Trung bình")
        self.tree.heading("hard", text="Khó")

        self.tree.column("id", width=50, anchor="center")
        self.tree.column("name", width=220, anchor="w")
        self.tree.column("desc", width=340, anchor="w")
        self.tree.column("total", width=100, anchor="center")
        self.tree.column("easy", width=70, anchor="center")
        self.tree.column("medium", width=90, anchor="center")
        self.tree.column("hard", width=70, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Double click to open bank
        self.tree.bind("<Double-1>", lambda event: self._open_selected_bank())
        self.tree.bind("<Return>", lambda event: self._open_selected_bank())

        # 4. Status Bar
        self.status_label = ctk.CTkLabel(
            self,
            text="Đang tải danh sách ngân hàng...",
            font=("Helvetica", 11),
            text_color="gray60"
        )
        self.status_label.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="w")

    def refresh_data(self):
        self.status_label.configure(text="Đang làm mới dữ liệu...")

        def worker():
            try:
                s_resp = self.connection.send_request("GET_SUBJECTS", token=self.token)
                q_resp = self.connection.send_request("GET_QUESTIONS", token=self.token)
                self.after(0, lambda: self._on_data_loaded(s_resp, q_resp))
            except Exception as e:
                self.after(0, lambda: self._on_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_data_loaded(self, s_resp, q_resp):
        if s_resp and s_resp.get("status") == "SUCCESS":
            self.subjects_cache = s_resp.get("data") or []
        else:
            self.subjects_cache = []

        if q_resp and q_resp.get("status") == "SUCCESS":
            self.questions_cache = q_resp.get("data") or []
        else:
            self.questions_cache = []

        self._apply_filter()

    def _on_error(self, err):
        self.status_label.configure(text=f"Lỗi: {err}")
        show_error("Lỗi kết nối", err, parent=self)

    def _apply_filter(self):
        query = self.search_entry.get().strip().lower()

        for item in self.tree.get_children():
            self.tree.delete(item)

        count = 0
        total_questions = 0
        for subj in self.subjects_cache:
            name = str(subj.get("name", ""))
            desc = str(subj.get("description", ""))

            if query and query not in name.lower() and query not in desc.lower():
                continue

            sid = subj.get("id")
            subj_questions = [q for q in self.questions_cache if q.get("subject_id") == sid]
            c_total = len(subj_questions)
            c_easy = sum(1 for q in subj_questions if q.get("difficulty") == "EASY")
            c_med = sum(1 for q in subj_questions if q.get("difficulty") == "MEDIUM")
            c_hard = sum(1 for q in subj_questions if q.get("difficulty") == "HARD")

            total_questions += c_total

            self.tree.insert(
                "",
                "end",
                iid=str(sid),
                values=(
                    sid,
                    name,
                    desc,
                    f"{c_total} câu",
                    c_easy,
                    c_med,
                    c_hard
                )
            )
            count += 1

        self.status_label.configure(
            text=f"Hiển thị {count}/{len(self.subjects_cache)} ngân hàng môn học   •   Tổng cộng: {total_questions} câu hỏi"
        )

    def _get_selected_subject(self) -> Optional[Dict[str, Any]]:
        selected = self.tree.selection()
        if not selected:
            return None
        sid = int(selected[0])
        for s in self.subjects_cache:
            if s.get("id") == sid:
                return s
        return None

    def _open_selected_bank(self):
        subj = self._get_selected_subject()
        if not subj:
            show_warning("Chưa chọn", "Vui lòng chọn môn học cần mở ngân hàng câu hỏi!", parent=self)
            return

        SubjectBankDialog(
            self,
            self.connection,
            self.token,
            subject_data=subj,
            subjects_list=self.subjects_cache,
            on_data_changed=self.refresh_data
        )

    def _open_import_dialog(self):
        subj = self._get_selected_subject()
        init_id = subj.get("id") if subj else (self.subjects_cache[0].get("id") if self.subjects_cache else None)
        ImportQuestionsDialog(
            self,
            self.connection,
            self.token,
            subjects=self.subjects_cache,
            initial_subject_id=init_id,
            on_import_success=self.refresh_data
        )

    def _open_add_dialog(self):
        subj = self._get_selected_subject()
        init_id = subj.get("id") if subj else (self.subjects_cache[0].get("id") if self.subjects_cache else None)
        QuestionDialog(
            self,
            self.connection,
            self.token,
            subjects=self.subjects_cache,
            question_data=None,
            initial_subject_id=init_id,
            on_save_success=self.refresh_data
        )
