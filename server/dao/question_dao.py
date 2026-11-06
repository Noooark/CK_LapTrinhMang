"""
Question Data Access Object - CRUD operations for questions table.
"""

import logging
from server.database import DatabaseConnection

logger = logging.getLogger(__name__)


class QuestionDAO:
    """Data access for questions table."""

    @staticmethod
    def find_all(subject_id: int = None) -> list:
        """Find all questions, optionally filtered by subject."""
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    if subject_id:
                        cur.execute(
                            "SELECT q.*, s.name AS subject_name "
                            "FROM questions q JOIN subjects s ON q.subject_id = s.id "
                            "WHERE q.subject_id = %s ORDER BY q.id",
                            (subject_id,)
                        )
                    else:
                        cur.execute(
                            "SELECT q.*, s.name AS subject_name "
                            "FROM questions q JOIN subjects s ON q.subject_id = s.id "
                            "ORDER BY q.id"
                        )
                    return cur.fetchall()
        except Exception as e:
            logger.error(f"Error finding questions: {e}")
            return []

    @staticmethod
    def find_by_id(question_id: int) -> dict | None:
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT q.*, s.name AS subject_name "
                        "FROM questions q JOIN subjects s ON q.subject_id = s.id "
                        "WHERE q.id = %s",
                        (question_id,)
                    )
                    return cur.fetchone()
        except Exception as e:
            logger.error(f"Error finding question by id: {e}")
            return None

    @staticmethod
    def find_by_subject(subject_id: int) -> list:
        """Find all questions for a given subject."""
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT q.*, s.name AS subject_name "
                        "FROM questions q JOIN subjects s ON q.subject_id = s.id "
                        "WHERE q.subject_id = %s ORDER BY q.id",
                        (subject_id,)
                    )
                    return cur.fetchall()
        except Exception as e:
            logger.error(f"Error finding questions by subject: {e}")
            return []

    @staticmethod
    def find_by_teacher(teacher_id: int) -> list:
        """Find all questions belonging to subjects taught by a teacher."""
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT q.*, s.name AS subject_name "
                        "FROM questions q "
                        "JOIN subjects s ON q.subject_id = s.id "
                        "WHERE s.teacher_id = %s ORDER BY q.id",
                        (teacher_id,)
                    )
                    return cur.fetchall()
        except Exception as e:
            logger.error(f"Error finding questions by teacher: {e}")
            return []

    @staticmethod
    def find_random(subject_id: int, count: int) -> list:
        """Get random questions from a subject."""
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT q.*, s.name AS subject_name "
                        "FROM questions q JOIN subjects s ON q.subject_id = s.id "
                        "WHERE q.subject_id = %s ORDER BY RAND() LIMIT %s",
                        (subject_id, count)
                    )
                    return cur.fetchall()
        except Exception as e:
            logger.error(f"Error finding random questions: {e}")
            return []

    @staticmethod
    def create(data: dict) -> int | None:
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO questions (subject_id, content, option_a, option_b, "
                        "option_c, option_d, correct_answer, difficulty) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                        (
                            data['subject_id'], data['content'],
                            data['option_a'], data['option_b'],
                            data['option_c'], data['option_d'],
                            data['correct_answer'],
                            data.get('difficulty', 'MEDIUM')
                        )
                    )
                    return cur.lastrowid
        except Exception as e:
            logger.error(f"Error creating question: {e}")
            return None

    @staticmethod
    def update(question_id: int, data: dict) -> bool:
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE questions SET subject_id=%s, content=%s, option_a=%s, "
                        "option_b=%s, option_c=%s, option_d=%s, correct_answer=%s, "
                        "difficulty=%s WHERE id=%s",
                        (
                            data['subject_id'], data['content'],
                            data['option_a'], data['option_b'],
                            data['option_c'], data['option_d'],
                            data['correct_answer'],
                            data.get('difficulty', 'MEDIUM'),
                            question_id
                        )
                    )
                    return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating question: {e}")
            return False

    @staticmethod
    def delete(question_id: int) -> bool:
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM questions WHERE id = %s", (question_id,))
                    return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting question: {e}")
            return False

    @staticmethod
    def count(subject_id: int = None) -> int:
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    if subject_id:
                        cur.execute("SELECT COUNT(*) as cnt FROM questions WHERE subject_id=%s", (subject_id,))
                    else:
                        cur.execute("SELECT COUNT(*) as cnt FROM questions")
                    return cur.fetchone()['cnt']
        except Exception as e:
            logger.error(f"Error counting questions: {e}")
            return 0
