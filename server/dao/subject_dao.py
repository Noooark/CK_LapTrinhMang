"""
Subject Data Access Object - CRUD operations for subjects table.
"""

import logging
from server.database import DatabaseConnection

logger = logging.getLogger(__name__)


class SubjectDAO:
    """Data access for subjects table."""

    @staticmethod
    def find_all() -> list:
        """Find all subjects with teacher name."""
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT s.*, u.full_name AS teacher_name "
                        "FROM subjects s LEFT JOIN users u ON s.teacher_id = u.id "
                        "ORDER BY s.id"
                    )
                    return cur.fetchall()
        except Exception as e:
            logger.error(f"Error finding all subjects: {e}")
            return []

    @staticmethod
    def find_by_id(subject_id: int) -> dict | None:
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT s.*, u.full_name AS teacher_name "
                        "FROM subjects s LEFT JOIN users u ON s.teacher_id = u.id "
                        "WHERE s.id = %s",
                        (subject_id,)
                    )
                    return cur.fetchone()
        except Exception as e:
            logger.error(f"Error finding subject by id: {e}")
            return None

    @staticmethod
    def find_by_teacher(teacher_id: int) -> list:
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT s.*, u.full_name AS teacher_name "
                        "FROM subjects s LEFT JOIN users u ON s.teacher_id = u.id "
                        "WHERE s.teacher_id = %s ORDER BY s.id",
                        (teacher_id,)
                    )
                    return cur.fetchall()
        except Exception as e:
            logger.error(f"Error finding subjects by teacher: {e}")
            return []

    @staticmethod
    def create(data: dict) -> int | None:
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO subjects (name, description, teacher_id) VALUES (%s, %s, %s)",
                        (data['name'], data.get('description', ''), data.get('teacher_id'))
                    )
                    return cur.lastrowid
        except Exception as e:
            logger.error(f"Error creating subject: {e}")
            return None

    @staticmethod
    def update(subject_id: int, data: dict) -> bool:
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE subjects SET name=%s, description=%s, teacher_id=%s WHERE id=%s",
                        (data['name'], data.get('description', ''), data.get('teacher_id'), subject_id)
                    )
                    return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating subject: {e}")
            return False

    @staticmethod
    def delete(subject_id: int) -> bool:
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM subjects WHERE id = %s", (subject_id,))
                    return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting subject: {e}")
            return False

    @staticmethod
    def count() -> int:
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) as cnt FROM subjects")
                    return cur.fetchone()['cnt']
        except Exception as e:
            logger.error(f"Error counting subjects: {e}")
            return 0
