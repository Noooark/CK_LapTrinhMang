"""
Result Data Access Object - operations for exam_results and exam_answers tables.
"""

import logging
from datetime import datetime
from server.database import DatabaseConnection

logger = logging.getLogger(__name__)


class ResultDAO:
    """Data access for exam results and answers."""

    @staticmethod
    def _serialize_row(row: dict) -> dict:
        if row:
            for key in ('submitted_at',):
                if row.get(key) and isinstance(row[key], datetime):
                    row[key] = str(row[key])
        return row

    @staticmethod
    def find_submission(cur, exam_id, student_id, current=False):
        locking = " FOR UPDATE" if current else ""
        cur.execute(
            "SELECT id AS result_id, correct_count, total_questions, score FROM exam_results "
            "WHERE exam_id = %s AND student_id = %s" + locking,
            (exam_id, student_id)
        )
        return cur.fetchone()

    @staticmethod
    def insert_submission(cur, exam_id, student_id, correct, total, score, records):
        cur.execute(
            "INSERT INTO exam_results (exam_id, student_id, correct_count, total_questions, score) "
            "VALUES (%s, %s, %s, %s, %s)", (exam_id, student_id, correct, total, score)
        )
        result_id = cur.lastrowid
        cur.executemany(
            "INSERT INTO exam_answers (result_id, question_id, selected_answer, is_correct) "
            "VALUES (%s, %s, %s, %s)",
            [(result_id, *record) for record in records]
        )
        return result_id

    @staticmethod
    def get_results_by_exam(exam_id: int) -> list:
        """Get all results for an exam."""
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT r.*, u.full_name AS student_name, u.username AS student_username "
                        "FROM exam_results r "
                        "JOIN users u ON r.student_id = u.id "
                        "WHERE r.exam_id = %s ORDER BY r.score DESC",
                        (exam_id,)
                    )
                    rows = cur.fetchall()
                    return [ResultDAO._serialize_row(r) for r in rows]
        except Exception as e:
            logger.error(f"Error getting results by exam: {e}")
            return []

    @staticmethod
    def get_results_by_student(student_id: int) -> list:
        """Get all results for a student."""
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT r.*, e.title AS exam_title, s.name AS subject_name "
                        "FROM exam_results r "
                        "JOIN exams e ON r.exam_id = e.id "
                        "JOIN subjects s ON e.subject_id = s.id "
                        "WHERE r.student_id = %s ORDER BY r.submitted_at DESC",
                        (student_id,)
                    )
                    rows = cur.fetchall()
                    return [ResultDAO._serialize_row(r) for r in rows]
        except Exception as e:
            logger.error(f"Error getting results by student: {e}")
            return []

    @staticmethod
    def has_taken_exam(student_id: int, exam_id: int) -> bool:
        """Check if a student has already taken an exam."""
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT COUNT(*) AS cnt FROM exam_results "
                        "WHERE student_id = %s AND exam_id = %s",
                        (student_id, exam_id)
                    )
                    return cur.fetchone()['cnt'] > 0
        except Exception as e:
            logger.error(f"Error checking if exam taken: {e}")
            return False

    @staticmethod
    def get_exam_stats(exam_id: int) -> dict:
        """Get statistics for an exam."""
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT COUNT(*) AS total_submissions, "
                        "COALESCE(AVG(score), 0) AS avg_score, "
                        "COALESCE(MAX(score), 0) AS max_score, "
                        "COALESCE(MIN(score), 0) AS min_score, "
                        "SUM(CASE WHEN score >= 5.0 THEN 1 ELSE 0 END) AS pass_count "
                        "FROM exam_results WHERE exam_id = %s",
                        (exam_id,)
                    )
                    row = cur.fetchone()
                    if row:
                        row['total_submissions'] = int(row['total_submissions']) if row.get('total_submissions') else 0
                        row['avg_score'] = round(float(row['avg_score']), 2) if row.get('avg_score') is not None else 0.0
                        row['max_score'] = round(float(row['max_score']), 2) if row.get('max_score') is not None else 0.0
                        row['min_score'] = round(float(row['min_score']), 2) if row.get('min_score') is not None else 0.0
                        total = row['total_submissions']
                        pass_cnt = int(row['pass_count']) if row.get('pass_count') is not None else 0
                        row['pass_count'] = pass_cnt
                        row['pass_rate'] = round((pass_cnt / total * 100), 1) if total > 0 else 0.0
                    return row or {}
        except Exception as e:
            logger.error(f"Error getting exam stats: {e}")
            return {}

    @staticmethod
    def get_answers_by_result(result_id: int) -> list:
        """Get all answers for a specific result."""
        try:
            with DatabaseConnection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT a.*, q.content AS question_content, q.correct_answer "
                        "FROM exam_answers a "
                        "JOIN questions q ON a.question_id = q.id "
                        "WHERE a.result_id = %s ORDER BY a.id",
                        (result_id,)
                    )
                    return cur.fetchall()
        except Exception as e:
            logger.error(f"Error getting answers: {e}")
            return []
