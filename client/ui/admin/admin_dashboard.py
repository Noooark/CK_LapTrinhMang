from typing import Callable, Dict, Any, Optional
import customtkinter as ctk

from client.network import ServerConnection
from client.ui.utils import PRIMARY_COLOR, PRIMARY_HOVER, DANGER_COLOR, ask_yes_no
from client.ui.admin.user_management import UserManagementPanel
from client.ui.admin.subject_management import SubjectManagementPanel
from client.ui.admin.stats_panel import SystemStatsPanel


class AdminDashboard(ctk.CTkFrame):
    """
    Main Administration Dashboard frame containing sidebar menu and dynamic content area.
    """

    def __init__(
        self,
        master,
        connection: ServerConnection,
        user_info: Dict[str, Any],
        token: str,
        on_logout: Callable[[], None],
        **kwargs
    ):
        super().__init__(master, **kwargs)
        self.connection = connection
        self.user_info = user_info
        self.token = token
        self.on_logout = on_logout

        self.current_panel: Optional[ctk.CTkFrame] = None
        self.menu_buttons = {}

        self._build_ui()
        self._show_panel("users")

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ----------------- SIDEBAR -----------------
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=("gray85", "#1c1e24"))
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)  # Spacer before logout

        # App Brand / Logo
        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frame.grid(row=0, column=0, padx=20, pady=(25, 20), sticky="ew")

        ctk.CTkLabel(
            brand_frame,
            text="👑 QUIZ APP",
            font=("Helvetica", 18, "bold"),
            text_color=PRIMARY_COLOR
        ).pack(anchor="w")

        ctk.CTkLabel(
            brand_frame,
            text="Quản trị hệ thống",
            font=("Helvetica", 11),
            text_color="gray60"
        ).pack(anchor="w")

        # User profile badge
        profile_frame = ctk.CTkFrame(self.sidebar, corner_radius=8, fg_color=("gray80", "#262930"))
        profile_frame.grid(row=1, column=0, padx=15, pady=(0, 20), sticky="ew")

        user_name = self.user_info.get("full_name") or self.user_info.get("username", "Admin")
        ctk.CTkLabel(
            profile_frame,
            text=f"👤 {user_name}",
            font=("Helvetica", 12, "bold"),
            anchor="w"
        ).pack(fill="x", padx=10, pady=(8, 2))

        ctk.CTkLabel(
            profile_frame,
            text="Vai trò: Quản trị viên (ADMIN)",
            font=("Helvetica", 10),
            text_color=PRIMARY_COLOR,
            anchor="w"
        ).pack(fill="x", padx=10, pady=(0, 8))

        # Menu navigation items
        menu_items = [
            ("users", "👥 Quản lý người dùng"),
            ("subjects", "📚 Quản lý môn học"),
            ("stats", "📊 Thống kê hệ thống"),
        ]

        for idx, (key, label) in enumerate(menu_items, start=2):
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                font=("Helvetica", 13),
                anchor="w",
                height=40,
                corner_radius=8,
                fg_color="transparent",
                text_color=("gray10", "#e0e0e0"),
                hover_color=("gray75", "#2a2d36"),
                command=lambda k=key: self._show_panel(k)
            )
            btn.grid(row=idx, column=0, padx=15, pady=4, sticky="ew")
            self.menu_buttons[key] = btn

        # Logout button at bottom
        self.logout_btn = ctk.CTkButton(
            self.sidebar,
            text="🚪 Đăng xuất",
            font=("Helvetica", 13),
            anchor="w",
            height=40,
            corner_radius=8,
            fg_color="transparent",
            text_color=DANGER_COLOR,
            hover_color=("#ffdddd", "#3b1a1f"),
            command=self._handle_logout
        )
        self.logout_btn.grid(row=7, column=0, padx=15, pady=20, sticky="ew")

        # ----------------- CONTENT CONTAINER -----------------
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.grid(row=0, column=1, sticky="nsew")
        self.content_container.grid_rowconfigure(0, weight=1)
        self.content_container.grid_columnconfigure(0, weight=1)

    def _show_panel(self, panel_name: str):
        # Update sidebar button active state
        for key, btn in self.menu_buttons.items():
            if key == panel_name:
                btn.configure(fg_color=PRIMARY_COLOR, text_color="#ffffff")
            else:
                btn.configure(fg_color="transparent", text_color=("gray10", "#e0e0e0"))

        # Destroy old panel
        if self.current_panel:
            self.current_panel.destroy()
            self.current_panel = None

        # Mount new panel
        if panel_name == "users":
            self.current_panel = UserManagementPanel(
                self.content_container,
                connection=self.connection,
                token=self.token
            )
        elif panel_name == "subjects":
            self.current_panel = SubjectManagementPanel(
                self.content_container,
                connection=self.connection,
                token=self.token
            )
        elif panel_name == "stats":
            self.current_panel = SystemStatsPanel(
                self.content_container,
                connection=self.connection,
                token=self.token
            )

        if self.current_panel:
            self.current_panel.grid(row=0, column=0, sticky="nsew")

    def _handle_logout(self):
        confirm = ask_yes_no("Đăng xuất", "Bạn có chắc chắn muốn đăng xuất?", parent=self)
        if confirm:
            self.on_logout()
