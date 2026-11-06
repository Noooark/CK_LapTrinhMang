"""
Authentication Service - Login, logout, token management.
"""

import uuid
import bcrypt
import logging
from server.dao.user_dao import UserDAO

logger = logging.getLogger(__name__)


class AuthService:
    """Handles authentication and session management."""

    def __init__(self):
        # In-memory session store: {token: user_data}
        self._sessions: dict[str, dict] = {}

    def login(self, username: str, password: str) -> tuple[bool, str, dict | None]:
        """
        Authenticate user.
        Returns: (success, message, data) where data includes token and user info.
        """
        if not username or not password:
            return False, "Vui lòng nhập tên đăng nhập và mật khẩu", None

        user = UserDAO.find_by_username(username)
        if not user:
            return False, "Tên đăng nhập không tồn tại", None

        if not user.get('is_active', False):
            return False, "Tài khoản đã bị vô hiệu hóa", None

        # Verify password with bcrypt
        try:
            stored_hash = user['password'].encode('utf-8')
            if not bcrypt.checkpw(password.encode('utf-8'), stored_hash):
                return False, "Mật khẩu không chính xác", None
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False, "Lỗi xác thực mật khẩu", None

        # Generate session token
        token = str(uuid.uuid4())
        user_info = {
            'id': user['id'],
            'username': user['username'],
            'full_name': user['full_name'],
            'email': user.get('email', ''),
            'role': user['role'],
        }
        self._sessions[token] = user_info

        logger.info(f"User '{username}' logged in successfully (role: {user['role']})")
        return True, "Đăng nhập thành công", {'token': token, 'user': user_info}

    def logout(self, token: str) -> tuple[bool, str, None]:
        """Remove session."""
        if token in self._sessions:
            username = self._sessions[token].get('username', 'unknown')
            del self._sessions[token]
            logger.info(f"User '{username}' logged out")
            return True, "Đăng xuất thành công", None
        return True, "Đăng xuất thành công", None

    def validate_token(self, token: str) -> dict | None:
        """Validate session token. Returns user info or None."""
        return self._sessions.get(token)

    def get_active_sessions_count(self) -> int:
        """Get number of active sessions."""
        return len(self._sessions)
