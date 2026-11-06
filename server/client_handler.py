"""
Client Handler - Processes incoming requests from each connected client.
Each client connection runs in its own thread.
"""

import threading
import logging

from common.protocol import send_message, receive_message, CommandType
from server.service.auth_service import AuthService
from server.service.user_service import UserService
from server.service.question_service import QuestionService
from server.service.exam_service import ExamService
from server.dao.subject_dao import SubjectDAO

logger = logging.getLogger(__name__)


class ClientHandler(threading.Thread):
    """Handles communication with a single connected client."""

    def __init__(self, client_socket, address, auth_service: AuthService):
        super().__init__(daemon=True)
        self.client_socket = client_socket
        self.address = address
        self.auth_service = auth_service
        self.running = True

    def run(self):
        """Main loop: receive and process requests."""
        addr_str = f"{self.address[0]}:{self.address[1]}"
        logger.info(f"[+] Client connected: {addr_str}")

        try:
            while self.running:
                request = receive_message(self.client_socket)
                if request is None:
                    logger.info(f"[-] Client disconnected: {addr_str}")
                    break

                response = self._handle_request(request)
                if not send_message(self.client_socket, response):
                    logger.warning(f"Failed to send response to {addr_str}")
                    break

        except Exception as e:
            logger.error(f"Error handling client {addr_str}: {e}")
        finally:
            self._cleanup()

    def _handle_request(self, request: dict) -> dict:
        """Route request to appropriate handler based on command."""
        command = request.get('command', '')
        token = request.get('token')
        data = request.get('data', {})

        # --- LOGIN doesn't require authentication ---
        if command == CommandType.LOGIN:
            return self._handle_login(data)

        # --- All other commands require authentication ---
        user = self.auth_service.validate_token(token)
        if not user:
            return self._error("Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.")

        # --- Route to handler ---
        try:
            handler_map = {
                CommandType.LOGOUT: lambda: self._handle_logout(token),

                # User management (ADMIN only)
                CommandType.GET_USERS: lambda: self._require_role(user, ['ADMIN'], lambda: UserService.get_all_users(data.get('role'))),
                CommandType.CREATE_USER: lambda: self._require_role(user, ['ADMIN'], lambda: UserService.create_user(data)),
                CommandType.UPDATE_USER: lambda: self._require_role(user, ['ADMIN'], lambda: UserService.update_user(data.get('id') or data.get('user_id'), data)),
                CommandType.DELETE_USER: lambda: self._require_role(user, ['ADMIN'], lambda: UserService.delete_user(data.get('id') or data.get('user_id'))),
                CommandType.RESET_PASSWORD: lambda: self._require_role(user, ['ADMIN'], lambda: UserService.reset_password(data.get('id') or data.get('user_id'), data.get('new_password'))),

                # Subject management (ADMIN only)
                CommandType.GET_SUBJECTS: lambda: self._handle_get_subjects(user),
                CommandType.CREATE_SUBJECT: lambda: self._require_role(user, ['ADMIN'], lambda: self._handle_create_subject(data)),
                CommandType.UPDATE_SUBJECT: lambda: self._require_role(user, ['ADMIN'], lambda: self._handle_update_subject(data)),
                CommandType.DELETE_SUBJECT: lambda: self._require_role(user, ['ADMIN'], lambda: self._handle_delete_subject(data)),

                # Question management (TEACHER, ADMIN)
                CommandType.GET_QUESTIONS: lambda: self._require_role(user, ['ADMIN', 'TEACHER'], lambda: QuestionService.get_questions(data, user)),
                CommandType.CREATE_QUESTION: lambda: self._require_role(user, ['ADMIN', 'TEACHER'], lambda: QuestionService.create_question(data)),
                CommandType.UPDATE_QUESTION: lambda: self._require_role(user, ['ADMIN', 'TEACHER'], lambda: QuestionService.update_question(data)),
                CommandType.DELETE_QUESTION: lambda: self._require_role(user, ['ADMIN', 'TEACHER'], lambda: QuestionService.delete_question(data)),

                # Exam management (TEACHER, ADMIN)
                CommandType.GET_EXAMS: lambda: ExamService.get_exams(data, user),
                CommandType.CREATE_EXAM: lambda: self._require_role(user, ['ADMIN', 'TEACHER'], lambda: ExamService.create_exam(data, user)),
                CommandType.UPDATE_EXAM: lambda: self._require_role(user, ['ADMIN', 'TEACHER'], lambda: ExamService.update_exam(data)),
                CommandType.DELETE_EXAM: lambda: self._require_role(user, ['ADMIN', 'TEACHER'], lambda: ExamService.delete_exam(data)),
                CommandType.START_EXAM: lambda: self._require_role(user, ['ADMIN', 'TEACHER'], lambda: ExamService.start_exam(data)),
                CommandType.END_EXAM: lambda: self._require_role(user, ['ADMIN', 'TEACHER'], lambda: ExamService.end_exam(data)),

                # Student exam operations
                CommandType.GET_AVAILABLE_EXAMS: lambda: ExamService.get_available_exams(user),
                CommandType.GET_EXAM_QUESTIONS: lambda: ExamService.get_exam_questions(data, user),
                CommandType.SUBMIT_EXAM: lambda: self._require_role(user, ['STUDENT'], lambda: ExamService.submit_exam(data, user)),

                # Results
                CommandType.GET_RESULTS: lambda: ExamService.get_results(data, user),
                CommandType.GET_MY_RESULTS: lambda: ExamService.get_my_results(user),
                CommandType.GET_EXAM_RESULTS: lambda: self._require_role(user, ['ADMIN', 'TEACHER'], lambda: ExamService.get_exam_results(data)),

                # Stats
                CommandType.GET_STATS: lambda: ExamService.get_stats(),

                # Password
                CommandType.CHANGE_PASSWORD: lambda: UserService.change_password(
                    user['id'], data.get('old_password', ''), data.get('new_password', '')
                ),
            }

            handler = handler_map.get(command)
            if handler:
                success, message, result_data = handler()
                return self._response("SUCCESS" if success else "ERROR", message, result_data)
            else:
                return self._error(f"Lệnh không hợp lệ: {command}")

        except Exception as e:
            logger.error(f"Error processing command '{command}': {e}", exc_info=True)
            return self._error(f"Lỗi server: {str(e)}")

    def _handle_login(self, data: dict) -> dict:
        """Handle login request."""
        username = data.get('username', '')
        password = data.get('password', '')
        success, message, result_data = self.auth_service.login(username, password)
        return self._response("SUCCESS" if success else "ERROR", message, result_data)

    def _handle_logout(self, token: str) -> tuple:
        """Handle logout request."""
        return self.auth_service.logout(token)

    def _handle_get_subjects(self, user: dict) -> tuple:
        """Get subjects - teachers see only their subjects."""
        if user['role'] == 'TEACHER':
            subjects = SubjectDAO.find_by_teacher(user['id'])
        else:
            subjects = SubjectDAO.find_all()
        return True, "Lấy danh sách môn học thành công", subjects

    def _handle_create_subject(self, data: dict) -> tuple:
        name = data.get('name', '').strip()
        if not name:
            return False, "Tên môn học không được để trống", None
        new_id = SubjectDAO.create(data)
        if new_id:
            return True, "Tạo môn học thành công", {'id': new_id}
        return False, "Lỗi khi tạo môn học", None

    def _handle_update_subject(self, data: dict) -> tuple:
        subject_id = data.get('id') or data.get('subject_id')
        if not subject_id:
            return False, "Thiếu ID môn học", None
        if SubjectDAO.update(subject_id, data):
            return True, "Cập nhật môn học thành công", None
        return False, "Lỗi khi cập nhật môn học", None

    def _handle_delete_subject(self, data: dict) -> tuple:
        subject_id = data.get('id') or data.get('subject_id')
        if not subject_id:
            return False, "Thiếu ID môn học", None
        if SubjectDAO.delete(subject_id):
            return True, "Xóa môn học thành công", None
        return False, "Lỗi khi xóa môn học", None

    def _require_role(self, user: dict, allowed_roles: list, func):
        """Check if user has required role before executing function."""
        if user['role'] not in allowed_roles:
            return False, "Bạn không có quyền thực hiện thao tác này", None
        return func()

    @staticmethod
    def _response(status: str, message: str, data=None) -> dict:
        return {"status": status, "message": message, "data": data}

    @staticmethod
    def _error(message: str) -> dict:
        return {"status": "ERROR", "message": message, "data": None}

    def _cleanup(self):
        """Clean up client socket."""
        try:
            self.running = False
            self.client_socket.close()
        except Exception:
            pass

    def stop(self):
        """Stop the client handler."""
        self.running = False
