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


class SubjectDialog(ctk.CTkToplevel):
    """Dialog for creating or editing a subject."""

    def __init__(
        self,
        parent,
        connection: ServerConnection,
        token: str,
        subject_data: Optional[Dict[str, Any]] = None,
        teachers: Optional[List[Dict[str, Any]]] = None,
        on_save_success=None
    ):
        super().__init__(parent)
        self.connection = connection
        self.token = token
        self.subject_data = subject_data
        self.teachers = teachers or []
        self.on_save_success = on_save_success
        self.is_edit = subject_data is not None

        self.title("Chỉnh sửa môn học" if self.is_edit else "Thêm môn học mới")
        self.geometry("480x480")
        self.minsize(440, 420)
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
        title_text = "Chỉnh sửa thông tin môn học" if self.is_edit else "Thêm môn học mới"
        header = ctk.CTkLabel(
            self,
            text=title_text,
            font=("Helvetica", 18, "bold")
        )
        header.grid(row=0, column=0, padx=25, pady=(15, 10), sticky="w")

        # Form container
        form_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        form_frame.grid(row=1, column=0, padx=20, pady=0, sticky="nsew")
        form_frame.grid_columnconfigure(0, weight=1)

        # Subject Name
        ctk.CTkLabel(form_frame, text="Tên môn học:", font=("Helvetica", 12, "bold")).grid(row=0, column=0, sticky="w", pady=(5, 2))
        self.name_entry = ctk.CTkEntry(form_frame, height=36, placeholder_text="Nhập tên môn học...")
        self.name_entry.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        # Teacher In Charge
        ctk.CTkLabel(form_frame, text="Giáo viên phụ trách:", font=("Helvetica", 12, "bold")).grid(row=2, column=0, sticky="w", pady=(5, 2))

        # Prepare teacher options
        self.teacher_map = {}
        teacher_names = ["-- Chưa phân công --"]
        for t in self.teachers:
            display_name = f"{t.get('full_name')} ({t.get('username')})"
            teacher_names.append(display_name)
            self.teacher_map[display_name] = t.get("id")

        self.teacher_var = ctk.StringVar(value=teacher_names[0])
        self.teacher_menu = ctk.CTkOptionMenu(
            form_frame,
            values=teacher_names,
            variable=self.teacher_var,
            height=36
        )
        self.teacher_menu.grid(row=3, column=0, sticky="ew", pady=(0, 10))

        # Description
        ctk.CTkLabel(form_frame, text="Mô tả môn học:", font=("Helvetica", 12, "bold")).grid(row=4, column=0, sticky="w", pady=(5, 2))
        self.desc_textbox = ctk.CTkTextbox(form_frame, height=90, font=("Helvetica", 12))
        self.desc_textbox.grid(row=5, column=0, sticky="ew", pady=(0, 15))

        # Action Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=2, column=0, padx=25, pady=(15, 20), sticky="ew")
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        self.cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Hủy bỏ",
            fg_color="gray50",
            hover_color="gray40",
            command=self.destroy,
            height=38
        )
        self.cancel_btn.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        self.save_btn = ctk.CTkButton(
            btn_frame,
            text="Lưu môn học",
            fg_color=PRIMARY_COLOR,
            hover_color=PRIMARY_HOVER,
            command=self._save_subject,
            height=38
        )
        self.save_btn.grid(row=0, column=1, padx=(10, 0), sticky="ew")

    def _populate_fields(self):
        if self.is_edit and self.subject_data:
            self.name_entry.insert(0, self.subject_data.get("name", ""))
            self.desc_textbox.insert("1.0", self.subject_data.get("description", "") or "")

            current_teacher_id = self.subject_data.get("teacher_id")
            for name, tid in self.teacher_map.items():
                if tid == current_teacher_id:
                    self.teacher_var.set(name)
                    break

    def _save_subject(self):
        name = self.name_entry.get().strip()
        description = self.desc_textbox.get("1.0", "end-1c").strip()
        selected_teacher_str = self.teacher_var.get()
        teacher_id = self.teacher_map.get(selected_teacher_str)

        if not name:
            show_error("Thiếu thông tin", "Vui lòng nhập tên môn học!", parent=self)
            return

        self.save_btn.configure(state="disabled", text="Đang lưu...")

        def worker():
            try:
                if self.is_edit:
                    payload = {
                        "subject_id": self.subject_data["id"],
                        "name": name,
                        "description": description,
                        "teacher_id": teacher_id
                    }
                    resp = self.connection.send_request("UPDATE_SUBJECT", data=payload, token=self.token)
                else:
                    payload = {
                        "name": name,
                        "description": description,
                        "teacher_id": teacher_id
                    }
                    resp = self.connection.send_request("CREATE_SUBJECT", data=payload, token=self.token)

                self.after(0, lambda: self._handle_response(resp))
            except Exception as e:
                self.after(0, lambda: self._handle_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_response(self, resp):
        self.save_btn.configure(state="normal", text="Lưu môn học")
        if resp and resp.get("status") == "SUCCESS":
            show_info("Thành công", resp.get("message", "Thao tác thành công!"), parent=self)
            if self.on_save_success:
                self.on_save_success()
            self.destroy()
        else:
            msg = resp.get("message", "Không thể lưu môn học!") if resp else "Lỗi kết nối máy chủ"
            show_error("Lỗi", msg, parent=self)

    def _handle_error(self, err_msg):
        self.save_btn.configure(state="normal", text="Lưu môn học")
        show_error("Lỗi kết nối", err_msg, parent=self)


class SubjectManagementPanel(ctk.CTkFrame):
    """
    Subject management view for Administrator: List, Add, Edit, Delete subjects.
    """

    def __init__(self, master, connection: ServerConnection, token: str, **kwargs):
        super().__init__(master, **kwargs)
        self.connection = connection
        self.token = token
        self.subjects_cache: List[Dict[str, Any]] = []
        self.teachers_cache: List[Dict[str, Any]] = []

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
            text="📚 Quản lý Môn học",
            font=("Helvetica", 20, "bold")
        ).grid(row=0, column=0, sticky="w")

        # 2. Controls Toolbar
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        toolbar.grid_columnconfigure(0, weight=1)

        # Search box & refresh
        left_box = ctk.CTkFrame(toolbar, fg_color="transparent")
        left_box.grid(row=0, column=0, sticky="w")

        self.search_entry = ctk.CTkEntry(
            left_box,
            placeholder_text="🔍 Tìm kiếm tên môn học...",
            width=280,
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

        # Action Buttons
        right_box = ctk.CTkFrame(toolbar, fg_color="transparent")
        right_box.grid(row=0, column=1, sticky="e")

        self.add_btn = ctk.CTkButton(
            right_box,
            text="➕ Thêm môn học",
            width=120,
            height=34,
            fg_color=SUCCESS_COLOR,
            hover_color="#218838",
            command=self._open_add_dialog
        )
        self.add_btn.grid(row=0, column=0, padx=(0, 8))

        self.edit_btn = ctk.CTkButton(
            right_box,
            text="✏️ Sửa",
            width=80,
            height=34,
            fg_color=PRIMARY_COLOR,
            hover_color=PRIMARY_HOVER,
            command=self._open_edit_dialog
        )
        self.edit_btn.grid(row=0, column=1, padx=(0, 8))

        self.delete_btn = ctk.CTkButton(
            right_box,
            text="🗑️ Xóa",
            width=80,
            height=34,
            fg_color=DANGER_COLOR,
            hover_color="#bd2130",
            command=self._delete_selected_subject
        )
        self.delete_btn.grid(row=0, column=2)

        # 3. Treeview Table
        table_frame = ctk.CTkFrame(self, corner_radius=8)
        table_frame.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="nsew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        columns = ("id", "name", "description", "teacher")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )
        style = ttk.Style()
        style_treeview(style)

        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Tên môn học")
        self.tree.heading("description", text="Mô tả môn học")
        self.tree.heading("teacher", text="Giáo viên phụ trách")

        self.tree.column("id", width=60, anchor="center")
        self.tree.column("name", width=220, anchor="w")
        self.tree.column("description", width=400, anchor="w")
        self.tree.column("teacher", width=200, anchor="w")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.tree.bind("<Double-1>", lambda event: self._open_edit_dialog())

        # 4. Status Bar
        self.status_label = ctk.CTkLabel(
            self,
            text="Đang tải dữ liệu môn học...",
            font=("Helvetica", 11),
            text_color="gray60"
        )
        self.status_label.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="w")

    def refresh_data(self):
        self.status_label.configure(text="Đang làm mới dữ liệu...")

        def worker():
            try:
                # Fetch subjects and teachers concurrently
                subj_resp = self.connection.send_request("GET_SUBJECTS", token=self.token)
                user_resp = self.connection.send_request("GET_USERS", data={"role": "TEACHER"}, token=self.token)

                self.after(0, lambda: self._on_data_loaded(subj_resp, user_resp))
            except Exception as e:
                self.after(0, lambda: self._on_load_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_data_loaded(self, subj_resp, user_resp):
        if subj_resp and subj_resp.get("status") == "SUCCESS":
            self.subjects_cache = subj_resp.get("data") or []
        else:
            self.subjects_cache = []

        if user_resp and user_resp.get("status") == "SUCCESS":
            all_users = user_resp.get("data") or []
            self.teachers_cache = [u for u in all_users if u.get("role") == "TEACHER"]
        else:
            self.teachers_cache = []

        self._apply_filter()

    def _on_load_error(self, err_msg):
        self.status_label.configure(text=f"Lỗi tải dữ liệu: {err_msg}")
        show_error("Lỗi kết nối", err_msg, parent=self)

    def _apply_filter(self):
        query = self.search_entry.get().strip().lower()

        for item in self.tree.get_children():
            self.tree.delete(item)

        # Build teacher lookup
        teacher_lookup = {t.get("id"): f"{t.get('full_name')} ({t.get('username')})" for t in self.teachers_cache}

        count = 0
        for subj in self.subjects_cache:
            name = str(subj.get("name", "")).lower()
            desc = str(subj.get("description", "") or "").lower()

            if query and (query not in name and query not in desc):
                continue

            teacher_name = subj.get("teacher_name")
            if not teacher_name:
                tid = subj.get("teacher_id")
                teacher_name = teacher_lookup.get(tid, "- Chưa phân công -")

            self.tree.insert(
                "",
                "end",
                iid=str(subj.get("id")),
                values=(
                    subj.get("id"),
                    subj.get("name"),
                    subj.get("description") or "-",
                    teacher_name
                )
            )
            count += 1

        self.status_label.configure(text=f"Hiển thị {count}/{len(self.subjects_cache)} môn học")

    def _get_selected_subject(self) -> Optional[Dict[str, Any]]:
        selected = self.tree.selection()
        if not selected:
            return None
        subj_id = int(selected[0])
        for s in self.subjects_cache:
            if s.get("id") == subj_id:
                return s
        return None

    def _open_add_dialog(self):
        SubjectDialog(
            self,
            self.connection,
            self.token,
            subject_data=None,
            teachers=self.teachers_cache,
            on_save_success=self.refresh_data
        )

    def _open_edit_dialog(self):
        subject = self._get_selected_subject()
        if not subject:
            show_warning("Chưa chọn", "Vui lòng chọn môn học cần sửa!", parent=self)
            return
        SubjectDialog(
            self,
            self.connection,
            self.token,
            subject_data=subject,
            teachers=self.teachers_cache,
            on_save_success=self.refresh_data
        )

    def _delete_selected_subject(self):
        subject = self._get_selected_subject()
        if not subject:
            show_warning("Chưa chọn", "Vui lòng chọn môn học cần xóa!", parent=self)
            return

        confirm = ask_yes_no(
            "Xác nhận xóa môn học",
            f"Bạn có chắc muốn xóa môn học '{subject.get('name')}'?",
            parent=self
        )
        if not confirm:
            return

        def worker():
            try:
                resp = self.connection.send_request("DELETE_SUBJECT", data={"subject_id": subject["id"]}, token=self.token)
                self.after(0, lambda: self._on_delete_result(resp))
            except Exception as e:
                self.after(0, lambda: show_error("Lỗi", str(e), parent=self))

        threading.Thread(target=worker, daemon=True).start()

    def _on_delete_result(self, resp):
        if resp and resp.get("status") == "SUCCESS":
            show_info("Thành công", resp.get("message", "Đã xóa môn học thành công!"), parent=self)
            self.refresh_data()
        else:
            show_error("Thất bại", resp.get("message", "Không thể xóa môn học!"), parent=self)
