"""
Exam Data Access Object - CRUD operations for exams and exam_questions tables.
"""

import logging
from datetime import datetime
from server.database import DatabaseConnection

logger = logging.getLogger(__name__)


class ExamDAO:
    """Data access for exams and exam_questions tables."""

    @staticmethod
    def _serialize_row(row: dict) -> dict:
        """Convert datetime fields to strings for JSON serialization."""
        if row:
            for key in ('start_time', 'end_time', 'created_at'):
                if row.get(key) and isinstance(row[key], datetime):
                    row[key] = str(row[key])
        return row

    @staticmethod
    def find_all() -> list:
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT e.*, s.name AS subject_name, u.full_name AS teacher_name "
                        "FROM exams e "
                        "JOIN subjects s ON e.subject_id = s.id "
                        "JOIN users u ON e.teacher_id = u.id "
                        "ORDER BY e.created_at DESC"
                    )
                    rows = cur.fetchall()
                    return [ExamDAO._serialize_row(r) for r in rows]
        except Exception as e:
            logger.error(f"Error finding all exams: {e}")
            return []

    @staticmethod
    def find_by_id(exam_id: int) -> dict | None:
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT e.*, s.name AS subject_name, u.full_name AS teacher_name "
                        "FROM exams e "
                        "JOIN subjects s ON e.subject_id = s.id "
                        "JOIN users u ON e.teacher_id = u.id "
                        "WHERE e.id = %s",
                        (exam_id,)
                    )
                    row = cur.fetchone()
                    return ExamDAO._serialize_row(row) if row else None
        except Exception as e:
            logger.error(f"Error finding exam by id: {e}")
            return None

    @staticmethod
    def find_by_teacher(teacher_id: int) -> list:
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT e.*, s.name AS subject_name "
                        "FROM exams e JOIN subjects s ON e.subject_id = s.id "
                        "WHERE e.teacher_id = %s ORDER BY e.created_at DESC",
                        (teacher_id,)
                    )
                    rows = cur.fetchall()
                    return [ExamDAO._serialize_row(r) for r in rows]
        except Exception as e:
            logger.error(f"Error finding exams by teacher: {e}")
            return []

    @staticmethod
    def find_active() -> list:
        """Find all currently active exams (for students)."""
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT e.*, s.name AS subject_name, u.full_name AS teacher_name "
                        "FROM exams e "
                        "JOIN subjects s ON e.subject_id = s.id "
                        "JOIN users u ON e.teacher_id = u.id "
                        "WHERE e.status = 'ACTIVE' "
                        "ORDER BY e.start_time DESC"
                    )
                    rows = cur.fetchall()
                    return [ExamDAO._serialize_row(r) for r in rows]
        except Exception as e:
            logger.error(f"Error finding active exams: {e}")
            return []

    @staticmethod
    def create(data: dict) -> int | None:
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO exams (title, subject_id, teacher_id, duration_minutes, "
                        "total_questions, status) VALUES (%s, %s, %s, %s, %s, %s)",
                        (
                            data['title'], data['subject_id'], data['teacher_id'],
                            data.get('duration_minutes', 30),
                            data.get('total_questions', 0),
                            data.get('status', 'DRAFT')
                        )
                    )
                    return cur.lastrowid
        except Exception as e:
            logger.error(f"Error creating exam: {e}")
            return None

    @staticmethod
    def update(exam_id: int, data: dict) -> bool:
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE exams SET title=%s, subject_id=%s, duration_minutes=%s, "
                        "total_questions=%s WHERE id=%s",
                        (
                            data['title'], data['subject_id'],
                            data.get('duration_minutes', 30),
                            data.get('total_questions', 0),
                            exam_id
                        )
                    )
                    return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating exam: {e}")
            return False

    @staticmethod
    def delete(exam_id: int) -> bool:
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM exams WHERE id = %s", (exam_id,))
                    return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting exam: {e}")
            return False

    @staticmethod
    def update_status(exam_id: int, status: str) -> bool:
        """Update exam status (DRAFT -> ACTIVE -> ENDED)."""
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    if status == 'ACTIVE':
                        cur.execute(
                            "UPDATE exams SET status=%s, start_time=NOW() WHERE id=%s",
                            (status, exam_id)
                        )
                    elif status == 'ENDED':
                        cur.execute(
                            "UPDATE exams SET status=%s, end_time=NOW() WHERE id=%s",
                            (status, exam_id)
                        )
                    else:
                        cur.execute(
                            "UPDATE exams SET status=%s WHERE id=%s",
                            (status, exam_id)
                        )
                    return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating exam status: {e}")
            return False

    @staticmethod
    def add_questions(exam_id: int, question_ids: list) -> bool:
        """Add questions to an exam."""
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    # Remove existing questions first
                    cur.execute("DELETE FROM exam_questions WHERE exam_id = %s", (exam_id,))
                    # Add new questions
                    for order, qid in enumerate(question_ids, 1):
                        cur.execute(
                            "INSERT INTO exam_questions (exam_id, question_id, order_number) "
                            "VALUES (%s, %s, %s)",
                            (exam_id, qid, order)
                        )
                    # Update total_questions count
                    cur.execute(
                        "UPDATE exams SET total_questions = %s WHERE id = %s",
                        (len(question_ids), exam_id)
                    )
                    return True
        except Exception as e:
            logger.error(f"Error adding questions to exam: {e}")
            return False

    @staticmethod
    def get_exam_questions(exam_id: int, include_answer: bool = True) -> list:
        """Get all questions for an exam, ordered by order_number."""
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    if include_answer:
                        cur.execute(
                            "SELECT q.*, eq.order_number "
                            "FROM exam_questions eq "
                            "JOIN questions q ON eq.question_id = q.id "
                            "WHERE eq.exam_id = %s ORDER BY eq.order_number",
                            (exam_id,)
                        )
                    else:
                        # Hide correct_answer for students during exam
                        cur.execute(
                            "SELECT q.id, q.content, q.option_a, q.option_b, "
                            "q.option_c, q.option_d, q.difficulty, eq.order_number "
                            "FROM exam_questions eq "
                            "JOIN questions q ON eq.question_id = q.id "
                            "WHERE eq.exam_id = %s ORDER BY eq.order_number",
                            (exam_id,)
                        )
                    return cur.fetchall()
        except Exception as e:
            logger.error(f"Error getting exam questions: {e}")
            return []

    @staticmethod
    def count() -> int:
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) as cnt FROM exams")
                    return cur.fetchone()['cnt']
        except Exception as e:
            logger.error(f"Error counting exams: {e}")
            return 0
