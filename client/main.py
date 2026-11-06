import os
import sys
import threading
from typing import Optional, Dict, Any
import customtkinter as ctk

# Ensure root directory is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from common.models import Role
from client.network import ServerConnection
from client.ui.login_frame import LoginFrame
from client.ui.admin.admin_dashboard import AdminDashboard
from client.ui.teacher.teacher_dashboard import TeacherDashboard
from client.ui.student.student_dashboard import StudentDashboard
from client.ui.utils import ask_yes_no


class QuizApp(ctk.CTk):
    """
    Main desktop client application for Online Quiz System.
    Manages session lifecycle, network connection, and role-based dashboard routing.
    """

    def __init__(self):
        super().__init__()

        # Window configuration
        self.title("Ứng dụng Trắc nghiệm Trực tuyến")
        self.minsize(1050, 650)
        self._center_window(1200, 720)

        # Networking & session state
        self.connection = ServerConnection()
        self.current_user: Optional[Dict[str, Any]] = None
        self.token: Optional[str] = None

        # Main dynamic container
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.grid(row=0, column=0, sticky="nsew")
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.current_view: Optional[ctk.CTkFrame] = None

        # Intercept window close
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Show Login Screen first
        self.show_login()

    def _center_window(self, width: int, height: int):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def show_login(self):
        """Displays login frame and resets session state."""
        self.current_user = None
        self.token = None

        if self.current_view:
            self.current_view.destroy()
            self.current_view = None

        self.current_view = LoginFrame(
            self.container,
            connection=self.connection,
            on_login_success=self.on_login_success
        )
        self.current_view.grid(row=0, column=0, sticky="nsew")

    def on_login_success(self, user_info: Dict[str, Any], token: str):
        """
        Callback upon successful authentication.
        Routes to the appropriate dashboard according to user's role.
        """
        self.current_user = user_info
        self.token = token

        role = str(user_info.get("role", "")).upper()
        print(f"[Client] User '{user_info.get('username')}' logged in with role: {role}")

        if self.current_view:
            self.current_view.destroy()
            self.current_view = None

        if role == Role.ADMIN.value:
            self.current_view = AdminDashboard(
                self.container,
                connection=self.connection,
                user_info=self.current_user,
                token=self.token,
                on_logout=self.logout
            )
        elif role == Role.TEACHER.value:
            self.current_view = TeacherDashboard(
                self.container,
                connection=self.connection,
                user_info=self.current_user,
                token=self.token,
                on_logout=self.logout
            )
        else:  # Role.STUDENT or default
            self.current_view = StudentDashboard(
                self.container,
                connection=self.connection,
                user_info=self.current_user,
                token=self.token,
                on_logout=self.logout
            )

        self.current_view.grid(row=0, column=0, sticky="nsew")

    def logout(self):
        """Performs logout: notifies server and switches back to login view."""
        if self.token:
            # Send logout request in background thread
            token_to_clear = self.token

            def worker():
                try:
                    self.connection.send_request("LOGOUT", token=token_to_clear)
                except Exception as e:
                    print(f"[Client] Error sending LOGOUT: {e}")

            threading.Thread(target=worker, daemon=True).start()

        self.show_login()

    def on_closing(self):
        """Gracefully disconnects network socket and closes application window."""
        try:
            if self.connection:
                self.connection.disconnect()
        except Exception:
            pass
        self.destroy()


def main():
    # Appearance and theme configuration
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")

    app = QuizApp()
    app.mainloop()


if __name__ == "__main__":
    main()
