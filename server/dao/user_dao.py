"""
User Data Access Object - CRUD operations for users table.
"""

import logging
from server.database import DatabaseConnection

logger = logging.getLogger(__name__)


class UserDAO:
    """Data access for users table."""

    @staticmethod
    def find_by_username(username: str) -> dict | None:
        """Find user by username."""
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM users WHERE username = %s", (username,))
                    row = cur.fetchone()
                    if row and row.get('created_at'):
                        row['created_at'] = str(row['created_at'])
                    return row
        except Exception as e:
            logger.error(f"Error finding user by username: {e}")
            return None

    @staticmethod
    def find_by_id(user_id: int) -> dict | None:
        """Find user by ID."""
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                    row = cur.fetchone()
                    if row and row.get('created_at'):
                        row['created_at'] = str(row['created_at'])
                    return row
        except Exception as e:
            logger.error(f"Error finding user by id: {e}")
            return None

    @staticmethod
    def find_all(role: str = None) -> list:
        """Find all users, optionally filtered by role."""
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    if role:
                        cur.execute(
                            "SELECT id, username, full_name, email, role, is_active, created_at "
                            "FROM users WHERE role = %s ORDER BY id",
                            (role,)
                        )
                    else:
                        cur.execute(
                            "SELECT id, username, full_name, email, role, is_active, created_at "
                            "FROM users ORDER BY id"
                        )
                    rows = cur.fetchall()
                    for row in rows:
                        if row.get('created_at'):
                            row['created_at'] = str(row['created_at'])
                    return rows
        except Exception as e:
            logger.error(f"Error finding all users: {e}")
            return []

    @staticmethod
    def create(user_data: dict) -> int | None:
        """Create a new user. Returns new user ID."""
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO users (username, password, full_name, email, role) "
                        "VALUES (%s, %s, %s, %s, %s)",
                        (
                            user_data['username'],
                            user_data['password'],
                            user_data.get('full_name', ''),
                            user_data.get('email', ''),
                            user_data.get('role', 'STUDENT')
                        )
                    )
                    return cur.lastrowid
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None

    @staticmethod
    def update(user_id: int, user_data: dict) -> bool:
        """Update user info (excluding password)."""
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE users SET full_name=%s, email=%s, role=%s, is_active=%s "
                        "WHERE id=%s",
                        (
                            user_data.get('full_name', ''),
                            user_data.get('email', ''),
                            user_data.get('role', 'STUDENT'),
                            user_data.get('is_active', True),
                            user_id
                        )
                    )
                    return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return False

    @staticmethod
    def delete(user_id: int) -> bool:
        """Soft delete user (set is_active=False)."""
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE users SET is_active = FALSE WHERE id = %s",
                        (user_id,)
                    )
                    return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False

    @staticmethod
    def update_password(user_id: int, new_password_hash: str) -> bool:
        """Update user password."""
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE users SET password = %s WHERE id = %s",
                        (new_password_hash, user_id)
                    )
                    return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating password: {e}")
            return False

    @staticmethod
    def count_by_role(role: str = None) -> int:
        """Count users by role."""
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    if role:
                        cur.execute("SELECT COUNT(*) as cnt FROM users WHERE role=%s AND is_active=TRUE", (role,))
                    else:
                        cur.execute("SELECT COUNT(*) as cnt FROM users WHERE is_active=TRUE")
                    return cur.fetchone()['cnt']
        except Exception as e:
            logger.error(f"Error counting users: {e}")
            return 0
