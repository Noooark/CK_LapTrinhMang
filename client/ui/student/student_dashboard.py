from typing import Callable, Dict, Any, Optional
import customtkinter as ctk

from client.network import ServerConnection
from client.ui.utils import PRIMARY_COLOR, DANGER_COLOR, ask_yes_no, show_error
from client.ui.student.camera_check_dialog import CameraCheckDialog
from client.ui.student.exam_list import ExamListPanel
from client.ui.student.result_history import ResultHistoryPanel
from client.ui.student.change_password import ChangePasswordPanel
from client.ui.student.exam_taking import ExamTakingPanel


class StudentDashboard(ctk.CTkFrame):
    """
    Main Student Dashboard managing available exams, test-taking view, history, and profile.
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
        self.in_exam_mode = False

        self._build_ui()
        self._show_panel("exams")

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ----------------- SIDEBAR -----------------
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=("gray85", "#1c1e24"))
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)  # Spacer

        # App Brand
        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frame.grid(row=0, column=0, padx=20, pady=(25, 20), sticky="ew")

        ctk.CTkLabel(
            brand_frame,
            text="🎓 QUIZ APP",
            font=("Helvetica", 18, "bold"),
            text_color=PRIMARY_COLOR
        ).pack(anchor="w")

        ctk.CTkLabel(
            brand_frame,
            text="Cổng Học sinh / Sinh viên",
            font=("Helvetica", 11),
            text_color="gray60"
        ).pack(anchor="w")

        # User profile
        profile_frame = ctk.CTkFrame(self.sidebar, corner_radius=8, fg_color=("gray80", "#262930"))
        profile_frame.grid(row=1, column=0, padx=15, pady=(0, 20), sticky="ew")

        student_name = self.user_info.get("full_name") or self.user_info.get("username", "Sinh viên")
        ctk.CTkLabel(
            profile_frame,
            text=f"👤 {student_name}",
            font=("Helvetica", 12, "bold"),
            anchor="w"
        ).pack(fill="x", padx=10, pady=(8, 2))

        ctk.CTkLabel(
            profile_frame,
            text="Vai trò: Học sinh / Sinh viên",
            font=("Helvetica", 10),
            text_color=PRIMARY_COLOR,
            anchor="w"
        ).pack(fill="x", padx=10, pady=(0, 8))

        # Menu navigation items
        menu_items = [
            ("exams", "📝 Bài thi có sẵn"),
            ("history", "📜 Lịch sử bài thi"),
            ("password", "🔑 Đổi mật khẩu"),
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

        # Logout button
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
        if self.in_exam_mode:
            return

        for key, btn in self.menu_buttons.items():
            if key == panel_name:
                btn.configure(fg_color=PRIMARY_COLOR, text_color="#ffffff")
            else:
                btn.configure(fg_color="transparent", text_color=("gray10", "#e0e0e0"))

        if self.current_panel:
            self.current_panel.destroy()
            self.current_panel = None

        if panel_name == "exams":
            self.current_panel = ExamListPanel(
                self.content_container,
                connection=self.connection,
                token=self.token,
                on_start_exam=self._start_exam_taking
            )
        elif panel_name == "history":
            self.current_panel = ResultHistoryPanel(
                self.content_container,
                connection=self.connection,
                token=self.token
            )
        elif panel_name == "password":
            self.current_panel = ChangePasswordPanel(
                self.content_container,
                connection=self.connection,
                token=self.token
            )

        if self.current_panel:
            self.current_panel.grid(row=0, column=0, sticky="nsew")

    def _start_exam_taking(self, exam_data: Dict[str, Any]):
        retention_days = exam_data.get("snapshot_retention_days")
        if exam_data.get("snapshot_enabled") and not retention_days:
            show_error("Chưa thể vào thi", "Đề thi yêu cầu lưu ảnh bằng chứng nhưng kết nối bảo mật "
                       "hoặc thư mục lưu ảnh chưa sẵn sàng. Vui lòng liên hệ giáo viên.", parent=self)
            return
        if exam_data.get("camera_required"):
            CameraCheckDialog(self, lambda camera: self._open_exam(exam_data, camera),
                              retention_days=retention_days)
        else:
            self._open_exam(exam_data)

    def _open_exam(self, exam_data, camera=None):
        """Switches content area to the interactive ExamTakingPanel."""
        self.in_exam_mode = True
        self.sidebar.grid_remove()

        # Unselect all menu buttons during exam
        for btn in self.menu_buttons.values():
            btn.configure(fg_color="transparent", text_color=("gray10", "#e0e0e0"))

        if self.current_panel:
            self.current_panel.destroy()
            self.current_panel = None

        self.current_panel = ExamTakingPanel(
            self.content_container,
            connection=self.connection,
            token=self.token,
            exam_data=exam_data,
            camera=camera,
            on_submitted=self._on_exam_submitted
        )
        self.current_panel.grid(row=0, column=0, sticky="nsew")

    def _on_exam_submitted(self, result_data: Dict[str, Any]):
        """Callback when an exam has been submitted."""
        self.in_exam_mode = False
        if result_data.get("close_window"):
            self.winfo_toplevel().on_closing()
            return
        self.sidebar.grid()
        self._show_panel("exams" if result_data.get("status") == "ABORTED" else "history")

    def request_close(self):
        if self.in_exam_mode:
            self.current_panel.request_close()
            return True
        return False

    def _handle_logout(self):
        if self.in_exam_mode:
            return

        confirm = ask_yes_no("Đăng xuất", "Bạn có chắc chắn muốn đăng xuất?", parent=self)
        if confirm:
            self.on_logout()
