import threading
from typing import Callable, Dict, Any, Optional
import customtkinter as ctk

from client.network import ServerConnection
from client.ui.utils import PRIMARY_COLOR, PRIMARY_HOVER, DANGER_COLOR


class LoginFrame(ctk.CTkFrame):
    """
    Centered login view with authentication against TCP QuizServer.
    """

    def __init__(
        self,
        master: Any,
        connection: ServerConnection,
        on_login_success: Callable[[Dict[str, Any], str], None],
        **kwargs
    ):
        super().__init__(master, **kwargs)
        self.connection = connection
        self.on_login_success = on_login_success

        self._build_ui()

    def _build_ui(self):
        # Configure layout for centering
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Card container
        self.card = ctk.CTkFrame(self, width=420, corner_radius=16, fg_color=("gray90", "#242830"))
        self.card.grid(row=0, column=0, padx=20, pady=20)
        self.card.grid_columnconfigure(0, weight=1)

        # Title and header
        title_icon = ctk.CTkLabel(
            self.card,
            text="📝",
            font=("Segoe UI Emoji", 48)
        )
        title_icon.grid(row=0, column=0, pady=(30, 5))

        app_title = ctk.CTkLabel(
            self.card,
            text="Ứng dụng Trắc nghiệm Trực tuyến",
            font=("Helvetica", 20, "bold"),
            text_color=("gray10", "#ffffff")
        )
        app_title.grid(row=1, column=0, padx=20, pady=(0, 4))

        subtitle = ctk.CTkLabel(
            self.card,
            text="Hệ thống thi trắc nghiệm Client - Server",
            font=("Helvetica", 12),
            text_color=("gray40", "gray70")
        )
        subtitle.grid(row=2, column=0, padx=20, pady=(0, 25))

        # Username Field
        self.username_entry = ctk.CTkEntry(
            self.card,
            placeholder_text="Tên đăng nhập",
            width=320,
            height=40,
            corner_radius=8,
            font=("Helvetica", 13)
        )
        self.username_entry.grid(row=3, column=0, padx=30, pady=(0, 15))
        self.username_entry.bind("<Return>", lambda event: self.password_entry.focus())

        # Password Field
        self.password_entry = ctk.CTkEntry(
            self.card,
            placeholder_text="Mật khẩu",
            show="*",
            width=320,
            height=40,
            corner_radius=8,
            font=("Helvetica", 13)
        )
        self.password_entry.grid(row=4, column=0, padx=30, pady=(0, 10))
        self.password_entry.bind("<Return>", lambda event: self._start_login())

        # Show password toggle
        self.show_pass_var = ctk.BooleanVar(value=False)
        self.show_pass_check = ctk.CTkCheckBox(
            self.card,
            text="Hiển thị mật khẩu",
            variable=self.show_pass_var,
            command=self._toggle_password_visibility,
            font=("Helvetica", 12),
            checkbox_width=18,
            checkbox_height=18
        )
        self.show_pass_check.grid(row=5, column=0, padx=30, pady=(0, 15), sticky="w")

        # Error label
        self.error_label = ctk.CTkLabel(
            self.card,
            text="",
            text_color=DANGER_COLOR,
            font=("Helvetica", 12),
            wraplength=320
        )
        self.error_label.grid(row=6, column=0, padx=30, pady=(0, 10))

        # Login button
        self.login_btn = ctk.CTkButton(
            self.card,
            text="Đăng nhập",
            command=self._start_login,
            width=320,
            height=42,
            corner_radius=8,
            fg_color=PRIMARY_COLOR,
            hover_color=PRIMARY_HOVER,
            font=("Helvetica", 14, "bold")
        )
        self.login_btn.grid(row=7, column=0, padx=30, pady=(0, 20))

        # Server connection status info
        self.status_label = ctk.CTkLabel(
            self.card,
            text=f"Máy chủ: {self.connection.host}:{self.connection.port}",
            font=("Helvetica", 11),
            text_color=("gray50", "gray60")
        )
        self.status_label.grid(row=8, column=0, padx=30, pady=(0, 25))

        # Focus initial field
        self.username_entry.focus()

    def _toggle_password_visibility(self):
        if self.show_pass_var.get():
            self.password_entry.configure(show="")
        else:
            self.password_entry.configure(show="*")

    def _start_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username:
            self._show_error("Vui lòng nhập tên đăng nhập!")
            self.username_entry.focus()
            return

        if not password:
            self._show_error("Vui lòng nhập mật khẩu!")
            self.password_entry.focus()
            return

        # UI state during request
        self.error_label.configure(text="")
        self.login_btn.configure(state="disabled", text="Đang đăng nhập...")

        # Asynchronous network call
        threading.Thread(
            target=self._login_worker,
            args=(username, password),
            daemon=True
        ).start()

    def _login_worker(self, username: str, password: str):
        try:
            response = self.connection.send_request(
                command="LOGIN",
                data={"username": username, "password": password}
            )

            if response and response.get("status") == "SUCCESS":
                data = response.get("data", {})
                user_info = data.get("user", {})
                token = data.get("token", "")
                self.after(0, lambda: self._on_success(user_info, token))
            else:
                msg = response.get("message", "Đăng nhập thất bại!") if response else "Không nhận được phản hồi từ máy chủ."
                self.after(0, lambda: self._show_error(msg))
        except Exception as e:
            self.after(0, lambda: self._show_error(f"Lỗi kết nối: {e}"))

    def _on_success(self, user_info: dict, token: str):
        self.login_btn.configure(state="normal", text="Đăng nhập")
        self.on_login_success(user_info, token)

    def _show_error(self, message: str):
        self.login_btn.configure(state="normal", text="Đăng nhập")
        self.error_label.configure(text=message)

    def reset_fields(self):
        """Clears inputs when returning to login screen."""
        self.username_entry.delete(0, "end")
        self.password_entry.delete(0, "end")
        self.error_label.configure(text="")
        self.login_btn.configure(state="normal", text="Đăng nhập")
        self.username_entry.focus()
