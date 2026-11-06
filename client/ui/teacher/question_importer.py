"""
Dialog for importing questions from Word (.docx) and Text (.txt) files.
"""

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
    style_treeview, show_error, show_info, show_warning
)
from common.parser import QuestionParser


class ImportQuestionsDialog(ctk.CTkToplevel):
    """
    Dialog to preview and import quiz questions in bulk from Word (.docx) or Text (.txt).
    """

    def __init__(
        self,
        parent,
        connection: ServerConnection,
        token: str,
        subjects: List[Dict[str, Any]],
        initial_subject_id: Optional[int] = None,
        on_import_success=None
    ):
        super().__init__(parent)
        self.connection = connection
        self.token = token
        self.subjects = subjects
        self.initial_subject_id = initial_subject_id
        self.on_import_success = on_import_success

        self.parsed_questions: List[Dict[str, Any]] = []
        self.parse_errors: List[str] = []
        self.selected_file_path: Optional[str] = None

        self.title("Nhập câu hỏi từ File (.docx / .txt)")
        self.geometry("900x680")
        self.minsize(750, 500)
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
        self.grid_rowconfigure(2, weight=1)

        # 1. Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header_frame,
            text="📥 Nhập Câu Hỏi Hàng Loạt từ File",
            font=("Helvetica", 18, "bold")
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header_frame,
            text="Hỗ trợ file Microsoft Word (.docx) và tệp văn bản (.txt) định dạng chuẩn trắc nghiệm",
            font=("Helvetica", 11),
            text_color="gray60"
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        # 2. Controls / Selectors Frame
        ctrl_frame = ctk.CTkFrame(self, corner_radius=8)
        ctrl_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        ctrl_frame.grid_columnconfigure(1, weight=1)

        # Row 0: Subject Selection
        ctk.CTkLabel(ctrl_frame, text="Môn học đích:", font=("Helvetica", 12, "bold")).grid(
            row=0, column=0, padx=(15, 10), pady=(12, 6), sticky="w"
        )
        self.subject_map = {}
        subj_names = []
        selected_subj_name = ""
        for s in self.subjects:
            name = s.get("name", f"Subject #{s.get('id')}")
            subj_names.append(name)
            self.subject_map[name] = s.get("id")
            if self.initial_subject_id and s.get("id") == self.initial_subject_id:
                selected_subj_name = name

        if not subj_names:
            subj_names = ["-- Chưa có môn học --"]

        if not selected_subj_name:
            selected_subj_name = subj_names[0]

        self.subj_var = ctk.StringVar(value=selected_subj_name)
        self.subj_menu = ctk.CTkOptionMenu(
            ctrl_frame,
            values=subj_names,
            variable=self.subj_var,
            height=34,
            width=260
        )
        self.subj_menu.grid(row=0, column=1, padx=(0, 10), pady=(12, 6), sticky="w")

        # Row 1: File selection
        ctk.CTkLabel(ctrl_frame, text="Tệp tin nguồn:", font=("Helvetica", 12, "bold")).grid(
            row=1, column=0, padx=(15, 10), pady=(0, 12), sticky="w"
        )

        file_pick_box = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        file_pick_box.grid(row=1, column=1, padx=(0, 15), pady=(0, 12), sticky="ew")
        file_pick_box.grid_columnconfigure(0, weight=1)

        self.file_entry = ctk.CTkEntry(
            file_pick_box,
            placeholder_text="Chọn tệp .docx hoặc .txt trên máy...",
            height=34
        )
        self.file_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.browse_btn = ctk.CTkButton(
            file_pick_box,
            text="📂 Chọn file...",
            width=110,
            height=34,
            command=self._browse_file
        )
        self.browse_btn.grid(row=0, column=1, padx=(0, 6))

        self.sample_btn = ctk.CTkButton(
            file_pick_box,
            text="📄 Tải file mẫu",
            width=100,
            height=34,
            fg_color="gray50",
            hover_color="gray40",
            command=self._save_sample_file
        )
        self.sample_btn.grid(row=0, column=2)

        # 3. Preview Section
        preview_frame = ctk.CTkFrame(self, corner_radius=8)
        preview_frame.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="nsew")
        preview_frame.grid_rowconfigure(1, weight=1)
        preview_frame.grid_columnconfigure(0, weight=1)

        status_bar = ctk.CTkFrame(preview_frame, fg_color="transparent")
        status_bar.grid(row=0, column=0, padx=12, pady=(10, 6), sticky="ew")
        status_bar.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            status_bar,
            text="Chưa chọn tệp tin. Vui lòng bấm 'Chọn file...' để nạp câu hỏi.",
            font=("Helvetica", 12, "bold"),
            text_color="gray60"
        )
        self.status_label.grid(row=0, column=0, sticky="w")

        # Treeview for preview
        tree_container = ctk.CTkFrame(preview_frame, fg_color="transparent")
        tree_container.grid(row=1, column=0, padx=12, pady=(0, 10), sticky="nsew")
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        cols = ("stt", "content", "opt_a", "opt_b", "opt_c", "opt_d", "correct", "diff")
        self.tree = ttk.Treeview(tree_container, columns=cols, show="headings", selectmode="browse")
        style = ttk.Style()
        style_treeview(style)

        self.tree.heading("stt", text="#")
        self.tree.heading("content", text="Nội dung câu hỏi")
        self.tree.heading("opt_a", text="Đáp án A")
        self.tree.heading("opt_b", text="Đáp án B")
        self.tree.heading("opt_c", text="Đáp án C")
        self.tree.heading("opt_d", text="Đáp án D")
        self.tree.heading("correct", text="Đ/A Đúng")
        self.tree.heading("diff", text="Độ khó")

        self.tree.column("stt", width=40, anchor="center")
        self.tree.column("content", width=300, anchor="w")
        self.tree.column("opt_a", width=110, anchor="w")
        self.tree.column("opt_b", width=110, anchor="w")
        self.tree.column("opt_c", width=110, anchor="w")
        self.tree.column("opt_d", width=110, anchor="w")
        self.tree.column("correct", width=70, anchor="center")
        self.tree.column("diff", width=80, anchor="center")

        v_scroll = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        h_scroll = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        # Error notification frame (if any questions have syntax errors)
        self.err_box = ctk.CTkTextbox(preview_frame, height=70, font=("Helvetica", 11), text_color="#dc3545")
        # Hidden by default

        # 4. Action Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=3, column=0, padx=20, pady=(5, 15), sticky="ew")
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            btn_frame,
            text="Đóng",
            fg_color="gray50",
            hover_color="gray40",
            height=38,
            command=self.destroy
        ).grid(row=0, column=0, padx=(0, 10), sticky="ew")

        self.import_btn = ctk.CTkButton(
            btn_frame,
            text="🚀 Nạp vào Ngân Hàng Câu Hỏi",
            fg_color=SUCCESS_COLOR,
            hover_color="#218838",
            height=38,
            state="disabled",
            command=self._do_import
        )
        self.import_btn.grid(row=0, column=1, padx=(10, 0), sticky="ew")

    def _browse_file(self):
        filetypes = [
            ("Tệp trắc nghiệm (*.docx, *.txt)", "*.docx;*.txt"),
            ("Microsoft Word Document (*.docx)", "*.docx"),
            ("Văn bản thuần (*.txt)", "*.txt"),
            ("Tất cả tệp", "*.*")
        ]
        chosen = filedialog.askopenfilename(
            parent=self,
            title="Chọn file chứa câu hỏi trắc nghiệm",
            filetypes=filetypes
        )
        if not chosen:
            return

        self.selected_file_path = chosen
        self.file_entry.delete(0, "end")
        self.file_entry.insert(0, chosen)
        self._parse_and_display()

    def _parse_and_display(self):
        if not self.selected_file_path:
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        self.status_label.configure(text="Đang phân tích tệp...", text_color="gray60")
        self.update_idletasks()

        questions, errors = QuestionParser.parse_file(self.selected_file_path)
        self.parsed_questions = questions
        self.parse_errors = errors

        # Populate table
        for idx, q in enumerate(questions, 1):
            c_preview = q["content"].replace("\n", " ")
            self.tree.insert("", "end", values=(
                idx,
                c_preview,
                q["option_a"][:40],
                q["option_b"][:40],
                q["option_c"][:40],
                q["option_d"][:40],
                q["correct_answer"],
                q["difficulty"]
            ))

        # Show status and error feedback
        if questions:
            msg = f"✅ Đã nhận diện thành công: {len(questions)} câu hỏi hợp lệ!"
            if errors:
                msg += f" (Bỏ qua {len(errors)} câu bị lỗi định dạng)"
            self.status_label.configure(text=msg, text_color=SUCCESS_COLOR)
            self.import_btn.configure(
                state="normal",
                text=f"🚀 Nạp {len(questions)} câu hỏi vào Ngân Hàng"
            )
        else:
            self.status_label.configure(
                text=f"❌ Không tìm thấy câu hỏi hợp lệ nào trong tệp!",
                text_color=DANGER_COLOR
            )
            self.import_btn.configure(state="disabled", text="🚀 Nạp vào Ngân Hàng Câu Hỏi")

        # Show error box if there are errors
        if errors:
            self.err_box.grid(row=2, column=0, padx=12, pady=(0, 10), sticky="ew")
            self.err_box.delete("1.0", "end")
            self.err_box.insert("end", "⚠️ Chi tiết lỗi định dạng:\n" + "\n".join(f"• {e}" for e in errors))
        else:
            self.err_box.grid_forget()

    def _save_sample_file(self):
        """Prompt user to save sample docx or txt file to their local machine."""
        sample_docx = "/home/khoile/Documents/QuizApp/database/mau_cau_hoi.docx"
        dest_file = filedialog.asksaveasfilename(
            parent=self,
            title="Lưu file đề thi mẫu",
            defaultextension=".docx",
            filetypes=[("Microsoft Word (*.docx)", "*.docx"), ("Văn bản (*.txt)", "*.txt")],
            initialfile="mau_cau_hoi.docx"
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

    def _do_import(self):
        if not self.parsed_questions:
            show_error("Trống", "Không có câu hỏi hợp lệ nào để nạp!", parent=self)
            return

        subj_name = self.subj_var.get()
        subj_id = self.subject_map.get(subj_name)
        if not subj_id:
            show_error("Lỗi", "Vui lòng chọn môn học hợp lệ!", parent=self)
            return

        self.import_btn.configure(state="disabled", text="Đang lưu lên máy chủ...")

        def worker():
            try:
                payload = {
                    "subject_id": subj_id,
                    "questions": self.parsed_questions
                }
                resp = self.connection.send_request("BATCH_CREATE_QUESTIONS", data=payload, token=self.token)
                self.after(0, lambda: self._handle_import_result(resp))
            except Exception as e:
                self.after(0, lambda: self._handle_import_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_import_result(self, resp):
        self.import_btn.configure(state="normal", text="🚀 Nạp vào Ngân Hàng Câu Hỏi")
        if resp and resp.get("status") == "SUCCESS":
            msg = resp.get("message", "Đã nạp câu hỏi thành công!")
            show_info("Thành công", msg, parent=self)
            if self.on_import_success:
                self.on_import_success()
            self.destroy()
        else:
            err = resp.get("message", "Lỗi không xác định khi nạp câu hỏi") if resp else "Máy chủ không phản hồi"
            show_error("Thất bại", err, parent=self)

    def _handle_import_error(self, err_str):
        self.import_btn.configure(state="normal", text="🚀 Nạp vào Ngân Hàng Câu Hỏi")
        show_error("Lỗi kết nối", err_str, parent=self)
