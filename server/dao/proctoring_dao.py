"""Persistence for attempts and their event history."""
from uuid import uuid4

from common.camera import CAMERA_RECOVERED
from server.database import DatabaseConnection


HEARTBEAT_TIMEOUT = 30
SUBMIT_GRACE = 120


class ProctoringDAO:
    @staticmethod
    def exam(cur, exam_id):
        cur.execute("SELECT * FROM exams WHERE id = %s LOCK IN SHARE MODE", (exam_id,))
        return cur.fetchone()

    @staticmethod
    def lock_attempt(cur, attempt_id, student_id):
        # Acquire locks in exam -> attempt order, like START_EXAM_ATTEMPT.
        cur.execute("SELECT exam_id FROM exam_attempts WHERE id = %s AND student_id = %s",
                    (attempt_id, student_id))
        row = cur.fetchone()
        if not row:
            return None
        exam = ProctoringDAO.exam(cur, row['exam_id'])
        if not exam:
            return None
        cur.execute(
            "SELECT a.*, NOW(6) AS server_now FROM exam_attempts a "
            "WHERE a.id = %s AND a.student_id = %s FOR UPDATE",
            (attempt_id, student_id)
        )
        attempt = cur.fetchone()
        return (exam, attempt) if attempt else None

    @staticmethod
    def add_event(cur, attempt_id, event_id, event_type, duration, faces=None):
        severity = "INFO" if event_type == CAMERA_RECOVERED else "WARNING"
        cur.execute(
            "INSERT INTO proctoring_events (attempt_id, event_id, event_type, duration_seconds, "
            "face_count, severity) VALUES (%s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE id = id",
            (attempt_id, event_id, event_type, duration, faces, severity)
        )

    @staticmethod
    def camera_rate_exceeded(cur, attempt_id):
        cur.execute(
            "SELECT id FROM proctoring_events "
            "WHERE attempt_id = %s AND created_at >= NOW(6) - INTERVAL 10 SECOND "
            "AND event_type LIKE %s LIMIT 10 FOR UPDATE", (attempt_id, "CAMERA_%")
        )
        return len(cur.fetchall()) >= 10

    @staticmethod
    def record_timeout(cur, attempt):
        elapsed = (attempt['server_now'] - attempt['last_heartbeat']).total_seconds()
        if attempt['status'] == 'IN_PROGRESS' and elapsed >= HEARTBEAT_TIMEOUT:
            cur.execute("UPDATE exam_attempts SET status = 'INTERRUPTED' WHERE id = %s",
                        (attempt['id'],))
            ProctoringDAO.add_event(cur, attempt['id'], str(uuid4()),
                                   'HEARTBEAT_TIMEOUT', HEARTBEAT_TIMEOUT)

    @staticmethod
    def stale_attempts():
        with DatabaseConnection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT a.id, a.student_id FROM exam_attempts a JOIN exams e ON e.id = a.exam_id "
                "WHERE a.status = 'IN_PROGRESS' "
                "AND a.last_heartbeat <= TIMESTAMPADD(SECOND, -%s, NOW(6)) "
                "AND e.status IN ('ACTIVE', 'ENDED') "
                "AND TIMESTAMPADD(SECOND, %s, a.last_heartbeat) "
                "<= LEAST(a.deadline_at, COALESCE(e.end_time, a.deadline_at))",
                (HEARTBEAT_TIMEOUT, HEARTBEAT_TIMEOUT - SUBMIT_GRACE)
            )
            return cur.fetchall()

    @staticmethod
    def monitoring_status(cur, exam_id):
        cur.execute(
            "SELECT a.id, u.username, a.started_at, a.last_heartbeat, a.status, a.camera_status, "
            "TIMESTAMPADD(SECOND, %s, LEAST(a.deadline_at, COALESCE(e.end_time, a.deadline_at))) "
            "< NOW(6) AS expired, "
            "(SELECT COUNT(*) FROM proctoring_events p WHERE p.attempt_id = a.id AND p.severity = 'WARNING') AS event_count, "
            "p.event_type AS latest_event, p.created_at AS latest_at "
            "FROM exam_attempts a JOIN users u ON u.id = a.student_id "
            "JOIN exams e ON e.id = a.exam_id "
            "LEFT JOIN proctoring_events p ON p.id = "
            "(SELECT MAX(pe.id) FROM proctoring_events pe WHERE pe.attempt_id = a.id AND pe.severity = 'WARNING') "
            "WHERE a.exam_id = %s ORDER BY u.username",
            (SUBMIT_GRACE, exam_id)
        )
        return cur.fetchall()

    @staticmethod
    def history(cur, exam_id, before_id, snapshots_available=False):
        cur.execute(
            "SELECT p.id, p.created_at, u.username, p.event_type, p.duration_seconds, p.face_count, "
            "p.severity, p.reviewed, (%s AND sn.event_id IS NOT NULL) AS has_snapshot "
            "FROM proctoring_events p JOIN exam_attempts a ON a.id = p.attempt_id "
            "LEFT JOIN proctoring_snapshots sn ON sn.event_id = p.id AND sn.expires_at > NOW(6) "
            "JOIN users u ON u.id = a.student_id "
            "WHERE a.exam_id = %s AND p.severity = 'WARNING' "
            "AND (%s IS NULL OR p.id < %s) ORDER BY p.id DESC LIMIT 101",
            (snapshots_available, exam_id, before_id, before_id)
        )
        return cur.fetchall()
