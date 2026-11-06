import threading
from typing import Dict, Any
import customtkinter as ctk

from client.network import ServerConnection
from client.ui.utils import PRIMARY_COLOR, PRIMARY_HOVER, show_error, show_info


class ChangePasswordPanel(ctk.CTkFrame):
    """
    Panel allowing students to update their account password.
    """

    def __init__(self, master, connection: ServerConnection, token: str, **kwargs):
        super().__init__(master, **kwargs)
        self.connection = connection
        self.token = token

        self._build_ui()

    def _build_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="ew")

        ctk.CTkLabel(
            header,
            text="🔑 Đổi Mật Khẩu",
            font=("Helvetica", 20, "bold")
        ).pack(anchor="w")

        # Centered form card
        card = ctk.CTkFrame(self, width=420, corner_radius=12, fg_color=("gray85", "#242830"))
        card.grid(row=1, column=0, padx=20, pady=20)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text="Thay đổi mật khẩu đăng nhập", font=("Helvetica", 14, "bold")).grid(row=0, column=0, padx=25, pady=(25, 15), sticky="w")

        # Current password
        ctk.CTkLabel(card, text="Mật khẩu hiện tại:", font=("Helvetica", 12)).grid(row=1, column=0, padx=25, pady=(5, 2), sticky="w")
        self.old_pwd_entry = ctk.CTkEntry(card, width=320, height=38, show="*")
        self.old_pwd_entry.grid(row=2, column=0, padx=25, pady=(0, 10))

        # New password
        ctk.CTkLabel(card, text="Mật khẩu mới:", font=("Helvetica", 12)).grid(row=3, column=0, padx=25, pady=(5, 2), sticky="w")
        self.new_pwd_entry = ctk.CTkEntry(card, width=320, height=38, show="*")
        self.new_pwd_entry.grid(row=4, column=0, padx=25, pady=(0, 10))

        # Confirm new password
        ctk.CTkLabel(card, text="Xác nhận mật khẩu mới:", font=("Helvetica", 12)).grid(row=5, column=0, padx=25, pady=(5, 2), sticky="w")
        self.confirm_pwd_entry = ctk.CTkEntry(card, width=320, height=38, show="*")
        self.confirm_pwd_entry.grid(row=6, column=0, padx=25, pady=(0, 15))

        # Submit button
        self.submit_btn = ctk.CTkButton(
            card,
            text="Cập nhật mật khẩu",
            width=320,
            height=40,
            fg_color=PRIMARY_COLOR,
            hover_color=PRIMARY_HOVER,
            command=self._do_change_password
        )
        self.submit_btn.grid(row=7, column=0, padx=25, pady=(5, 25))

    def _do_change_password(self):
        old_pwd = self.old_pwd_entry.get().strip()
        new_pwd = self.new_pwd_entry.get().strip()
        confirm_pwd = self.confirm_pwd_entry.get().strip()

        if not old_pwd or not new_pwd:
            show_error("Thiếu thông tin", "Vui lòng nhập đầy đủ mật khẩu cũ và mới!", parent=self)
            return

        if new_pwd != confirm_pwd:
            show_error("Không khớp", "Mật khẩu xác nhận không khớp với mật khẩu mới!", parent=self)
            return

        if len(new_pwd) < 4:
            show_error("Mật khẩu yếu", "Mật khẩu mới phải có ít nhất 4 ký tự!", parent=self)
            return

        self.submit_btn.configure(state="disabled", text="Đang xử lý...")

        def worker():
            try:
                resp = self.connection.send_request(
                    "CHANGE_PASSWORD",
                    data={"old_password": old_pwd, "new_password": new_pwd},
                    token=self.token
                )
                self.after(0, lambda: self._handle_result(resp))
            except Exception as e:
                self.after(0, lambda: show_error("Lỗi", str(e), parent=self))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_result(self, resp):
        self.submit_btn.configure(state="normal", text="Cập nhật mật khẩu")
        if resp and resp.get("status") == "SUCCESS":
            show_info("Thành công", resp.get("message", "Đã đổi mật khẩu thành công!"), parent=self)
            self.old_pwd_entry.delete(0, "end")
            self.new_pwd_entry.delete(0, "end")
            self.confirm_pwd_entry.delete(0, "end")
        else:
            show_error("Thất bại", resp.get("message", "Đổi mật khẩu không thành công!"), parent=self)
