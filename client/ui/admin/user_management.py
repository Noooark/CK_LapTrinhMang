import threading
import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional, List
import customtkinter as ctk

from client.network import ServerConnection
from client.ui.utils import (
    PRIMARY_COLOR, PRIMARY_HOVER, DANGER_COLOR, SUCCESS_COLOR, WARNING_COLOR,
    style_treeview, show_error, show_info, show_warning, ask_yes_no
)


class UserDialog(ctk.CTkToplevel):
    """Dialog for creating or editing a user account."""

    def __init__(
        self,
        parent,
        connection: ServerConnection,
        token: str,
        user_data: Optional[Dict[str, Any]] = None,
        on_save_success=None
    ):
        super().__init__(parent)
        self.connection = connection
        self.token = token
        self.user_data = user_data
        self.on_save_success = on_save_success
        self.is_edit = user_data is not None

        self.title("Chỉnh sửa người dùng" if self.is_edit else "Thêm người dùng mới")
        self.geometry("480x560")
        self.minsize(440, 450)
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
        title_text = "Chỉnh sửa tài khoản" if self.is_edit else "Thêm tài khoản mới"
        header = ctk.CTkLabel(
            self,
            text=title_text,
            font=("Helvetica", 18, "bold")
        )
        header.grid(row=0, column=0, padx=25, pady=(15, 10), sticky="w")

        # Form container - Scrollable so fields never push buttons off screen
        form_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        form_frame.grid(row=1, column=0, padx=20, pady=0, sticky="nsew")
        form_frame.grid_columnconfigure(0, weight=1)

        # Username
        ctk.CTkLabel(form_frame, text="Tên đăng nhập:", font=("Helvetica", 12, "bold")).grid(row=0, column=0, sticky="w", pady=(5, 2))
        self.username_entry = ctk.CTkEntry(form_frame, height=36)
        self.username_entry.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        # Password
        pwd_label_text = "Mật khẩu (để trống nếu không đổi):" if self.is_edit else "Mật khẩu:"
        ctk.CTkLabel(form_frame, text=pwd_label_text, font=("Helvetica", 12, "bold")).grid(row=2, column=0, sticky="w", pady=(5, 2))
        self.password_entry = ctk.CTkEntry(form_frame, height=36, show="*")
        self.password_entry.grid(row=3, column=0, sticky="ew", pady=(0, 10))

        # Full Name
        ctk.CTkLabel(form_frame, text="Họ và tên:", font=("Helvetica", 12, "bold")).grid(row=4, column=0, sticky="w", pady=(5, 2))
        self.fullname_entry = ctk.CTkEntry(form_frame, height=36)
        self.fullname_entry.grid(row=5, column=0, sticky="ew", pady=(0, 10))

        # Email
        ctk.CTkLabel(form_frame, text="Email:", font=("Helvetica", 12, "bold")).grid(row=6, column=0, sticky="w", pady=(5, 2))
        self.email_entry = ctk.CTkEntry(form_frame, height=36)
        self.email_entry.grid(row=7, column=0, sticky="ew", pady=(0, 10))

        # Role
        ctk.CTkLabel(form_frame, text="Vai trò (Role):", font=("Helvetica", 12, "bold")).grid(row=8, column=0, sticky="w", pady=(5, 2))
        self.role_var = ctk.StringVar(value="STUDENT")
        self.role_menu = ctk.CTkOptionMenu(
            form_frame,
            values=["STUDENT", "TEACHER", "ADMIN"],
            variable=self.role_var,
            height=36
        )
        self.role_menu.grid(row=9, column=0, sticky="ew", pady=(0, 10))

        # Is Active (in edit mode)
        self.active_var = ctk.BooleanVar(value=True)
        self.active_check = ctk.CTkCheckBox(
            form_frame,
            text="Tài khoản kích hoạt",
            variable=self.active_var,
            font=("Helvetica", 12)
        )
        self.active_check.grid(row=10, column=0, sticky="w", pady=(5, 10))

        # Buttons
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
            text="Lưu thay đổi" if self.is_edit else "Thêm mới",
            fg_color=PRIMARY_COLOR,
            hover_color=PRIMARY_HOVER,
            command=self._save_user,
            height=38
        )
        self.save_btn.grid(row=0, column=1, padx=(10, 0), sticky="ew")

    def _populate_fields(self):
        if self.is_edit and self.user_data:
            self.username_entry.insert(0, self.user_data.get("username", ""))
            self.username_entry.configure(state="disabled")
            self.fullname_entry.insert(0, self.user_data.get("full_name", ""))
            self.email_entry.insert(0, self.user_data.get("email", "") or "")
            self.role_var.set(self.user_data.get("role", "STUDENT"))
            self.active_var.set(bool(self.user_data.get("is_active", True)))

    def _save_user(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        full_name = self.fullname_entry.get().strip()
        email = self.email_entry.get().strip()
        role = self.role_var.get()
        is_active = self.active_var.get()

        if not self.is_edit:
            if not username:
                show_error("Thiếu thông tin", "Vui lòng nhập tên đăng nhập!", parent=self)
                return
            if not password:
                show_error("Thiếu thông tin", "Vui lòng nhập mật khẩu!", parent=self)
                return

        if not full_name:
            show_error("Thiếu thông tin", "Vui lòng nhập họ và tên!", parent=self)
            return

        self.save_btn.configure(state="disabled", text="Đang lưu...")

        def worker():
            try:
                if self.is_edit:
                    payload = {
                        "user_id": self.user_data["id"],
                        "full_name": full_name,
                        "email": email,
                        "role": role,
                        "is_active": is_active
                    }
                    if password:
                        payload["password"] = password

                    resp = self.connection.send_request("UPDATE_USER", data=payload, token=self.token)
                else:
                    payload = {
                        "username": username,
                        "password": password,
                        "full_name": full_name,
                        "email": email,
                        "role": role
                    }
                    resp = self.connection.send_request("CREATE_USER", data=payload, token=self.token)

                self.after(0, lambda: self._handle_response(resp))
            except Exception as e:
                self.after(0, lambda: self._handle_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_response(self, resp):
        self.save_btn.configure(state="normal", text="Lưu thay đổi" if self.is_edit else "Thêm mới")
        if resp and resp.get("status") == "SUCCESS":
            show_info("Thành công", resp.get("message", "Thao tác thành công!"), parent=self)
            if self.on_save_success:
                self.on_save_success()
            self.destroy()
        else:
            msg = resp.get("message", "Không thể lưu thông tin người dùng!") if resp else "Lỗi máy chủ"
            show_error("Lỗi", msg, parent=self)

    def _handle_error(self, err_msg):
        self.save_btn.configure(state="normal", text="Lưu thay đổi" if self.is_edit else "Thêm mới")
        show_error("Lỗi kết nối", err_msg, parent=self)


class ResetPasswordDialog(ctk.CTkToplevel):
    """Dialog for resetting user password."""

    def __init__(self, parent, connection: ServerConnection, token: str, user_data: dict, on_success=None):
        super().__init__(parent)
        self.connection = connection
        self.token = token
        self.user_data = user_data
        self.on_success = on_success

        self.title("Đặt lại mật khẩu")
        self.geometry("380x240")
        self.resizable(False, False)
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

        ctk.CTkLabel(
            self,
            text=f"Reset mật khẩu cho: {self.user_data.get('username')}",
            font=("Helvetica", 14, "bold")
        ).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        ctk.CTkLabel(
            self,
            text="Nhập mật khẩu mới:",
            font=("Helvetica", 12)
        ).grid(row=1, column=0, padx=20, pady=(5, 2), sticky="w")

        self.password_entry = ctk.CTkEntry(self, height=36, show="*", placeholder_text="Mật khẩu mới (vd: 123456)")
        self.password_entry.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="ew")
        self.password_entry.insert(0, "123456")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=3, column=0, padx=20, pady=(10, 20), sticky="ew")
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            btn_frame,
            text="Hủy",
            fg_color="gray50",
            hover_color="gray40",
            command=self.destroy,
            height=36
        ).grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.submit_btn = ctk.CTkButton(
            btn_frame,
            text="Xác nhận",
            fg_color=WARNING_COLOR,
            hover_color="#d3680e",
            command=self._do_reset,
            height=36
        )
        self.submit_btn.grid(row=0, column=1, padx=(5, 0), sticky="ew")

    def _do_reset(self):
        new_pwd = self.password_entry.get().strip()
        if not new_pwd:
            show_error("Lỗi", "Vui lòng nhập mật khẩu mới!", parent=self)
            return

        self.submit_btn.configure(state="disabled", text="Đang gửi...")

        def worker():
            try:
                resp = self.connection.send_request(
                    "RESET_PASSWORD",
                    data={"user_id": self.user_data["id"], "new_password": new_pwd},
                    token=self.token
                )
                self.after(0, lambda: self._handle_result(resp))
            except Exception as e:
                self.after(0, lambda: show_error("Lỗi", str(e), parent=self))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_result(self, resp):
        self.submit_btn.configure(state="normal", text="Xác nhận")
        if resp and resp.get("status") == "SUCCESS":
            show_info("Thành công", resp.get("message", "Mật khẩu đã được đặt lại!"), parent=self)
            if self.on_success:
                self.on_success()
            self.destroy()
        else:
            show_error("Thất bại", resp.get("message", "Không thể đặt lại mật khẩu!"), parent=self)


class UserManagementPanel(ctk.CTkFrame):
    """
    Main user management panel for Administrator: CRUD users, filter, reset password.
    """

    def __init__(self, master, connection: ServerConnection, token: str, **kwargs):
        super().__init__(master, **kwargs)
        self.connection = connection
        self.token = token
        self.users_cache: List[Dict[str, Any]] = []

        self._build_ui()
        self.refresh_users()

    def _build_ui(self):
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # 1. Top action header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header_frame,
            text="👥 Quản lý Người dùng",
            font=("Helvetica", 20, "bold")
        )
        title.grid(row=0, column=0, sticky="w")

        # 2. Controls & Filter toolbar
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        toolbar.grid_columnconfigure(0, weight=1)

        # Left filter section
        filter_box = ctk.CTkFrame(toolbar, fg_color="transparent")
        filter_box.grid(row=0, column=0, sticky="w")

        # Search field
        self.search_entry = ctk.CTkEntry(
            filter_box,
            placeholder_text="🔍 Tìm username hoặc họ tên...",
            width=240,
            height=34
        )
        self.search_entry.grid(row=0, column=0, padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda e: self._apply_filter())

        # Role filter
        ctk.CTkLabel(filter_box, text="Vai trò:", font=("Helvetica", 12)).grid(row=0, column=1, padx=(0, 5))
        self.role_filter_var = ctk.StringVar(value="Tất cả")
        self.role_filter_menu = ctk.CTkOptionMenu(
            filter_box,
            values=["Tất cả", "ADMIN", "TEACHER", "STUDENT"],
            variable=self.role_filter_var,
            command=lambda val: self._apply_filter(),
            width=120,
            height=34
        )
        self.role_filter_menu.grid(row=0, column=2, padx=(0, 10))

        # Refresh button
        self.refresh_btn = ctk.CTkButton(
            filter_box,
            text="🔄 Làm mới",
            width=90,
            height=34,
            fg_color="gray40",
            hover_color="gray30",
            command=self.refresh_users
        )
        self.refresh_btn.grid(row=0, column=3, padx=(0, 10))

        # Right buttons section
        btn_box = ctk.CTkFrame(toolbar, fg_color="transparent")
        btn_box.grid(row=0, column=1, sticky="e")

        self.add_btn = ctk.CTkButton(
            btn_box,
            text="➕ Thêm",
            width=85,
            height=34,
            fg_color=SUCCESS_COLOR,
            hover_color="#218838",
            command=self._open_add_dialog
        )
        self.add_btn.grid(row=0, column=0, padx=(0, 6))

        self.edit_btn = ctk.CTkButton(
            btn_box,
            text="✏️ Sửa",
            width=80,
            height=34,
            fg_color=PRIMARY_COLOR,
            hover_color=PRIMARY_HOVER,
            command=self._open_edit_dialog
        )
        self.edit_btn.grid(row=0, column=1, padx=(0, 6))

        self.reset_pwd_btn = ctk.CTkButton(
            btn_box,
            text="🔑 Reset MK",
            width=95,
            height=34,
            fg_color=WARNING_COLOR,
            hover_color="#d3680e",
            command=self._open_reset_pwd_dialog
        )
        self.reset_pwd_btn.grid(row=0, column=2, padx=(0, 6))

        self.delete_btn = ctk.CTkButton(
            btn_box,
            text="🗑️ Xóa",
            width=80,
            height=34,
            fg_color=DANGER_COLOR,
            hover_color="#bd2130",
            command=self._delete_selected_user
        )
        self.delete_btn.grid(row=0, column=3)

        # 3. Treeview Table Container
        table_frame = ctk.CTkFrame(self, corner_radius=8)
        table_frame.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="nsew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        columns = ("id", "username", "full_name", "email", "role", "is_active", "created_at")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )
        style = ttk.Style()
        style_treeview(style)

        # Define column headings and widths
        self.tree.heading("id", text="ID")
        self.tree.heading("username", text="Tên đăng nhập")
        self.tree.heading("full_name", text="Họ và tên")
        self.tree.heading("email", text="Email")
        self.tree.heading("role", text="Vai trò")
        self.tree.heading("is_active", text="Trạng thái")
        self.tree.heading("created_at", text="Ngày tạo")

        self.tree.column("id", width=50, anchor="center")
        self.tree.column("username", width=140, anchor="w")
        self.tree.column("full_name", width=180, anchor="w")
        self.tree.column("email", width=180, anchor="w")
        self.tree.column("role", width=100, anchor="center")
        self.tree.column("is_active", width=110, anchor="center")
        self.tree.column("created_at", width=140, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.tree.bind("<Double-1>", lambda event: self._open_edit_dialog())

        # 4. Status Bar
        self.status_label = ctk.CTkLabel(
            self,
            text="Đang tải dữ liệu...",
            font=("Helvetica", 11),
            text_color="gray60"
        )
        self.status_label.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="w")

    def refresh_users(self):
        self.status_label.configure(text="Đang làm mới danh sách người dùng...")

        def worker():
            try:
                resp = self.connection.send_request("GET_USERS", token=self.token)
                self.after(0, lambda: self._on_users_loaded(resp))
            except Exception as e:
                self.after(0, lambda: self._on_load_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_users_loaded(self, resp):
        if resp and resp.get("status") == "SUCCESS":
            self.users_cache = resp.get("data") or []
            self._apply_filter()
            self.status_label.configure(text=f"Tổng số: {len(self.users_cache)} người dùng")
        else:
            msg = resp.get("message", "Lỗi tải người dùng") if resp else "Không có phản hồi từ máy chủ"
            self.status_label.configure(text=f"Lỗi: {msg}")
            show_error("Lỗi", msg, parent=self)

    def _on_load_error(self, err_msg):
        self.status_label.configure(text=f"Lỗi kết nối: {err_msg}")
        show_error("Lỗi kết nối", err_msg, parent=self)

    def _apply_filter(self):
        query = self.search_entry.get().strip().lower()
        role_filter = self.role_filter_var.get()

        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        count = 0
        for user in self.users_cache:
            username = str(user.get("username", "")).lower()
            fullname = str(user.get("full_name", "")).lower()
            role = str(user.get("role", ""))

            # Filter conditions
            if query and (query not in username and query not in fullname):
                continue
            if role_filter != "Tất cả" and role != role_filter:
                continue

            active_str = "Hoạt động" if user.get("is_active", True) else "Đã khóa"
            created_at = str(user.get("created_at", "") or "")[:19]

            self.tree.insert(
                "",
                "end",
                iid=str(user.get("id")),
                values=(
                    user.get("id"),
                    user.get("username"),
                    user.get("full_name"),
                    user.get("email") or "-",
                    user.get("role"),
                    active_str,
                    created_at
                )
            )
            count += 1

        self.status_label.configure(text=f"Hiển thị {count}/{len(self.users_cache)} người dùng")

    def _get_selected_user(self) -> Optional[Dict[str, Any]]:
        selected = self.tree.selection()
        if not selected:
            return None
        user_id = int(selected[0])
        for u in self.users_cache:
            if u.get("id") == user_id:
                return u
        return None

    def _open_add_dialog(self):
        UserDialog(self, self.connection, self.token, user_data=None, on_save_success=self.refresh_users)

    def _open_edit_dialog(self):
        user = self._get_selected_user()
        if not user:
            show_warning("Chưa chọn", "Vui lòng chọn người dùng cần sửa từ danh sách!", parent=self)
            return
        UserDialog(self, self.connection, self.token, user_data=user, on_save_success=self.refresh_users)

    def _open_reset_pwd_dialog(self):
        user = self._get_selected_user()
        if not user:
            show_warning("Chưa chọn", "Vui lòng chọn người dùng cần đặt lại mật khẩu!", parent=self)
            return
        ResetPasswordDialog(self, self.connection, self.token, user_data=user, on_success=self.refresh_users)

    def _delete_selected_user(self):
        user = self._get_selected_user()
        if not user:
            show_warning("Chưa chọn", "Vui lòng chọn người dùng cần xóa!", parent=self)
            return

        confirm = ask_yes_no(
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa tài khoản '{user.get('username')}'?\n(Tài khoản sẽ được chuyển sang trạng thái ngưng hoạt động)",
            parent=self
        )
        if not confirm:
            return

        def worker():
            try:
                resp = self.connection.send_request("DELETE_USER", data={"user_id": user["id"]}, token=self.token)
                self.after(0, lambda: self._on_delete_result(resp))
            except Exception as e:
                self.after(0, lambda: show_error("Lỗi", str(e), parent=self))

        threading.Thread(target=worker, daemon=True).start()

    def _on_delete_result(self, resp):
        if resp and resp.get("status") == "SUCCESS":
            show_info("Thành công", resp.get("message", "Đã xóa người dùng thành công!"), parent=self)
            self.refresh_users()
        else:
            show_error("Thất bại", resp.get("message", "Không thể xóa người dùng!"), parent=self)
