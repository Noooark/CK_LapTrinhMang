"""
User Service - Business logic for user management.
"""

import bcrypt
import logging
from server.dao.user_dao import UserDAO

logger = logging.getLogger(__name__)

DEFAULT_PASSWORD = "123456"


class UserService:
    """Business logic for user operations."""

    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash password with bcrypt."""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    @staticmethod
    def get_all_users(role: str = None) -> tuple[bool, str, list]:
        """Get all users, optionally filtered by role."""
        users = UserDAO.find_all(role=role)
        # Remove password from response
        for u in users:
            u.pop('password', None)
        return True, "Lấy danh sách người dùng thành công", users

    @staticmethod
    def create_user(data: dict) -> tuple[bool, str, dict | None]:
        """Create a new user."""
        username = data.get('username', '').strip()
        if not username:
            return False, "Tên đăng nhập không được để trống", None

        # Check if username exists
        existing = UserDAO.find_by_username(username)
        if existing:
            return False, f"Tên đăng nhập '{username}' đã tồn tại", None

        # Hash password
        password = data.get('password', DEFAULT_PASSWORD)
        data['password'] = UserService._hash_password(password)

        new_id = UserDAO.create(data)
        if new_id:
            return True, f"Tạo người dùng '{username}' thành công", {'id': new_id}
        return False, "Lỗi khi tạo người dùng", None

    @staticmethod
    def update_user(user_id: int, data: dict) -> tuple[bool, str, None]:
        """Update user info."""
        if UserDAO.update(user_id, data):
            return True, "Cập nhật người dùng thành công", None
        return False, "Lỗi khi cập nhật người dùng", None

    @staticmethod
    def delete_user(user_id: int) -> tuple[bool, str, None]:
        """Soft-delete a user."""
        if UserDAO.delete(user_id):
            return True, "Vô hiệu hóa người dùng thành công", None
        return False, "Lỗi khi vô hiệu hóa người dùng", None

    @staticmethod
    def reset_password(user_id: int, new_password: str = None) -> tuple[bool, str, None]:
        """Reset user password to default or specified password."""
        pwd = new_password if new_password else DEFAULT_PASSWORD
        hashed = UserService._hash_password(pwd)
        if UserDAO.update_password(user_id, hashed):
            return True, f"Đặt lại mật khẩu thành '{pwd}' thành công", None
        return False, "Lỗi khi đặt lại mật khẩu", None

    @staticmethod
    def change_password(user_id: int, old_password: str, new_password: str) -> tuple[bool, str, None]:
        """Change user password (requires old password verification)."""
        user = UserDAO.find_by_id(user_id)
        if not user:
            return False, "Không tìm thấy người dùng", None

        # Verify old password
        try:
            if not bcrypt.checkpw(old_password.encode('utf-8'), user['password'].encode('utf-8')):
                return False, "Mật khẩu cũ không chính xác", None
        except Exception:
            return False, "Lỗi xác thực mật khẩu", None

        if len(new_password) < 4:
            return False, "Mật khẩu mới phải có ít nhất 4 ký tự", None

        hashed = UserService._hash_password(new_password)
        if UserDAO.update_password(user_id, hashed):
            return True, "Đổi mật khẩu thành công", None
        return False, "Lỗi khi đổi mật khẩu", None
