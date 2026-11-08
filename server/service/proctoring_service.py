"""Server-authoritative exam lifecycle and monitoring."""
from datetime import timedelta
from uuid import UUID

from common.camera import CAMERA_EVENTS, CAMERA_PHONE_DETECTED, CAMERA_RECOVERED, CAMERA_THRESHOLDS, PHONE_THRESHOLD_SECONDS
from server.dao.exam_dao import ExamDAO
from server.dao.proctoring_dao import HEARTBEAT_TIMEOUT, ProctoringDAO, SUBMIT_GRACE
from server.dao.result_dao import ResultDAO
from server.database import DatabaseConnection


STUDENT_EVENTS = {'FOCUS_LOST', 'FULLSCREEN_EXIT', 'EXAM_EXIT_REQUESTED', *CAMERA_EVENTS}


def valid_id(value, maximum=2**31 - 1):
    return type(value) is int and 0 < value <= maximum


def error(message):
    return False, message, None


def cutoff(exam, attempt):
    deadline = attempt['deadline_at']
    if exam['status'] == 'ENDED' and exam['end_time']:
        return min(deadline, exam['end_time'])
    return deadline


def remaining(exam, attempt):
    return (cutoff(exam, attempt) - attempt['server_now']).total_seconds()


def accepts_work(exam, attempt):
    return exam['status'] in ('ACTIVE', 'ENDED') and remaining(exam, attempt) >= -SUBMIT_GRACE


class ProctoringService:
    @staticmethod
    def start(data, user, snapshot_days=None):
        exam_id = data.get('exam_id')
        if not valid_id(exam_id):
            return error("Mã đề thi không hợp lệ")
        with DatabaseConnection() as conn, conn.cursor() as cur:
            exam = ProctoringDAO.exam(cur, exam_id)
            if not exam or exam['status'] != 'ACTIVE' or (exam['duration_minutes'] or 0) <= 0:
                return error("Đề thi chưa mở hoặc đã kết thúc")
            camera_required = bool(exam['camera_required'])
            if camera_required and data.get('camera_ready') is not True:
                return error("Đề thi yêu cầu kiểm tra camera trước khi bắt đầu")
            snapshot_required = bool(exam["snapshot_enabled"])
            if snapshot_required:
                if not snapshot_days:
                    return error("Đề thi yêu cầu lưu ảnh bằng chứng qua kết nối TLS")
                if data.get("snapshot_consent") is not True:
                    return error("Cần chấp nhận điều kiện lưu ảnh bằng chứng trước khi vào thi")
            snapshot_consent = snapshot_required
            if ResultDAO.find_submission(cur, exam_id, user['id']):
                return error("Bạn đã nộp bài thi này")
            questions = ExamDAO.read_questions(cur, exam_id, include_answer=False)
            if not questions:
                return error("Đề thi chưa có câu hỏi")
            cur.execute(
                "INSERT INTO exam_attempts (exam_id, student_id, started_at, deadline_at, "
                "last_heartbeat, status, camera_status, snapshot_consent) VALUES (%s, %s, NOW(6), "
                "TIMESTAMPADD(MINUTE, %s, NOW(6)), NOW(6), 'IN_PROGRESS', %s, %s) "
                "ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id), "
                "snapshot_consent = snapshot_consent AND VALUES(snapshot_consent)",
                (exam_id, user['id'], exam['duration_minutes'], CAMERA_RECOVERED if camera_required else None,
                 snapshot_consent)
            )
            attempt_id = cur.lastrowid
            cur.execute("SELECT *, NOW(6) AS server_now FROM exam_attempts WHERE id = %s FOR UPDATE",
                        (attempt_id,))
            attempt = cur.fetchone()
            if snapshot_required and not attempt["snapshot_consent"]:
                return error("Lượt thi cũ chưa chấp nhận lưu ảnh. Vui lòng liên hệ giáo viên.")
            seconds = remaining(exam, attempt)
            if attempt['status'] == 'SUBMITTED' or seconds <= 0:
                return error("Lượt thi đã kết thúc")
            if camera_required:
                cur.execute("UPDATE exam_attempts SET camera_status = %s WHERE id = %s",
                            (CAMERA_RECOVERED, attempt_id))
            ProctoringService._touch(cur, attempt)
            return True, "Đã mở lượt thi", {
                'attempt_id': attempt_id, 'remaining_seconds': seconds, 'questions': questions,
                'submit_grace_seconds': SUBMIT_GRACE,
                'camera_required': camera_required,
                'snapshot_consent': bool(attempt['snapshot_consent']),
                'camera_thresholds': {key: exam[key] for key, _ in CAMERA_THRESHOLDS.values()},
            }

    @staticmethod
    def _touch(cur, attempt):
        ProctoringDAO.record_timeout(cur, attempt)
        cur.execute("UPDATE exam_attempts SET last_heartbeat = NOW(6), status = 'IN_PROGRESS' "
                    "WHERE id = %s", (attempt['id'],))

    @staticmethod
    def heartbeat(data, user):
        attempt_id = data.get('attempt_id')
        if not valid_id(attempt_id):
            return error("Mã lượt thi không hợp lệ")
        with DatabaseConnection() as conn, conn.cursor() as cur:
            locked = ProctoringDAO.lock_attempt(cur, attempt_id, user['id'])
            if not locked:
                return error("Không tìm thấy lượt thi")
            exam, attempt = locked
            seconds = remaining(exam, attempt)
            if attempt['status'] == 'SUBMITTED':
                return True, "Lượt thi đã nộp", {'remaining_seconds': 0, 'finished': True}
            if accepts_work(exam, attempt):
                ProctoringService._touch(cur, attempt)
            return True, "Đã cập nhật trạng thái", {
                'remaining_seconds': seconds, 'finished': not accepts_work(exam, attempt),
            }

    @staticmethod
    def report_event(data, user):
        attempt_id = data.get('attempt_id')
        event_id = data.get('event_id')
        event_type = data.get('event_type')
        duration = data.get('duration_seconds')
        if not valid_id(attempt_id) or not isinstance(event_id, str) or len(event_id) != 36:
            return error("Mã lượt thi hoặc mã sự kiện không hợp lệ")
        try:
            event_id = str(UUID(event_id))
        except ValueError:
            return error("Mã sự kiện không hợp lệ")
        if not isinstance(event_type, str) or event_type not in STUDENT_EVENTS:
            return error("Loại sự kiện không hợp lệ")
        camera_event = event_type in CAMERA_EVENTS
        faces = data.get('face_count')
        if camera_event and data.keys() - {'attempt_id', 'event_id', 'event_type', 'duration_seconds', 'face_count'}:
            return error("Sự kiện camera chỉ chấp nhận metadata")
        if event_type == 'CAMERA_MULTIPLE_FACES':
            if type(faces) is not int or not 2 <= faces <= 100:
                return error("Số khuôn mặt không hợp lệ")
        elif faces is not None:
            return error("Loại sự kiện này không có số khuôn mặt")
        if event_type in CAMERA_THRESHOLDS or event_type in {'FOCUS_LOST', CAMERA_PHONE_DETECTED}:
            minimum = 0 if event_type == 'CAMERA_DISCONNECTED' else 0.001
            if type(duration) not in (int, float) or not minimum <= duration <= 86400:
                return error("Thời lượng sự kiện không hợp lệ")
            if event_type == CAMERA_PHONE_DETECTED and duration < PHONE_THRESHOLD_SECONDS:
                return error("Thời lượng thấp hơn ngưỡng phát hiện điện thoại")
        elif duration is not None:
            return error("Loại sự kiện này không có thời lượng")

        with DatabaseConnection() as conn, conn.cursor() as cur:
            locked = ProctoringDAO.lock_attempt(cur, attempt_id, user['id'])
            if not locked:
                return error("Không tìm thấy lượt thi")
            exam, attempt = locked
            cur.execute("SELECT id FROM proctoring_events WHERE attempt_id = %s AND event_id = %s "
                        "FOR UPDATE", (attempt_id, event_id))
            if cur.fetchone():
                return True, "Sự kiện đã được ghi nhận", None
            if attempt['status'] == 'SUBMITTED' or not accepts_work(exam, attempt):
                return error("Lượt thi đã kết thúc")
            if camera_event:
                if not attempt['camera_status']:
                    return error("Lượt thi không yêu cầu camera")
                if event_type in CAMERA_THRESHOLDS:
                    key, _ = CAMERA_THRESHOLDS[event_type]
                    withdrew_consent = event_type == 'CAMERA_DISCONNECTED' and duration == 0
                    if duration < exam[key] and not withdrew_consent:
                        return error("Thời lượng thấp hơn ngưỡng camera của đề thi")
                if ProctoringDAO.camera_rate_exceeded(cur, attempt_id):
                    return False, "Quá nhiều sự kiện camera, vui lòng thử lại", {'retry_after_seconds': 2}
                if event_type != CAMERA_PHONE_DETECTED:
                    cur.execute("UPDATE exam_attempts SET camera_status = %s WHERE id = %s",
                                (event_type, attempt_id))
            ProctoringDAO.add_event(cur, attempt_id, event_id, event_type, duration, faces)
            return True, "Đã ghi nhận sự kiện", None

    @staticmethod
    def submit(data, user):
        attempt_id = data.get('attempt_id')
        exam_id = data.get('exam_id')
        answers = data.get('answers', {})
        if not valid_id(attempt_id) or not valid_id(exam_id) or not isinstance(answers, dict):
            return error("Lượt thi hoặc đáp án không hợp lệ")
        if any(not isinstance(value, str) or len(value) > 1 or value.upper() not in ('', 'A', 'B', 'C', 'D')
               for value in answers.values()):
            return error("Đáp án không hợp lệ")

        with DatabaseConnection() as conn, conn.cursor() as cur:
            locked = ProctoringDAO.lock_attempt(cur, attempt_id, user['id'])
            if not locked or locked[1]['exam_id'] != exam_id:
                return error("Không tìm thấy lượt thi")
            exam, attempt = locked
            if attempt['status'] == 'SUBMITTED':
                result = ResultDAO.find_submission(cur, exam_id, user['id'], current=True)
                if result:
                    return True, "Bài thi đã được lưu", result
                return error("Không tìm thấy kết quả đã nộp")
            if not accepts_work(exam, attempt):
                return error("Đã quá thời hạn nộp bài")
            questions = ExamDAO.read_questions(cur, exam_id, include_answer=True)
            if not questions:
                return error("Không tìm thấy câu hỏi cho đề thi")
            records = []
            for question in questions:
                selected = answers.get(str(question['id']), '').upper()
                records.append((question['id'], selected, selected == question['correct_answer'].upper()))
            correct = sum(record[2] for record in records)
            total = len(records)
            score = round(correct / total * 10, 2)
            ProctoringDAO.record_timeout(cur, attempt)
            result_id = ResultDAO.insert_submission(cur, exam_id, user['id'], correct, total, score, records)
            cur.execute("UPDATE exam_attempts SET status = 'SUBMITTED', submitted_at = NOW(6) "
                        "WHERE id = %s", (attempt_id,))
            return True, "Nộp bài thành công", {
                'result_id': result_id, 'correct_count': correct, 'total_questions': total, 'score': score,
            }

    @staticmethod
    def sweep_timeouts():
        for row in ProctoringDAO.stale_attempts():
            with DatabaseConnection() as conn, conn.cursor() as cur:
                locked = ProctoringDAO.lock_attempt(cur, row['id'], row['student_id'])
                if locked:
                    exam, attempt = locked
                    last_seen = attempt['last_heartbeat']
                    if (exam['status'] in ('ACTIVE', 'ENDED')
                            and (cutoff(exam, attempt) - last_seen).total_seconds() + SUBMIT_GRACE >= HEARTBEAT_TIMEOUT):
                        ProctoringDAO.record_timeout(cur, attempt)

    @staticmethod
    def monitor(data, user, action, snapshots_available=False):
        exam_id = data.get('exam_id')
        event_id = data.get('id')
        before_id = data.get('before_id')
        if not valid_id(exam_id):
            return error("Mã đề thi không hợp lệ")
        if action == 'ack' and not valid_id(event_id, 2**63 - 1):
            return error("Mã cảnh báo không hợp lệ")
        if before_id is not None and not valid_id(before_id, 2**63 - 1):
            return error("Mốc lịch sử không hợp lệ")
        with DatabaseConnection() as conn, conn.cursor() as cur:
            exam = ProctoringDAO.exam(cur, exam_id)
            if not exam or (user['role'] != 'ADMIN' and exam['teacher_id'] != user['id']):
                return error("Bạn không có quyền giám sát đề thi này")
            if action == 'status':
                return True, "Trạng thái giám sát", ProctoringDAO.monitoring_status(cur, exam_id)
            if action == 'history':
                rows = ProctoringDAO.history(cur, exam_id, before_id, snapshots_available)
                return True, "Lịch sử cảnh báo", {
                    'events': rows[:100], 'next_before_id': rows[99]['id'] if len(rows) > 100 else None,
                    'snapshot_access': snapshots_available,
                }
            cur.execute(
                "SELECT p.id FROM proctoring_events p JOIN exam_attempts a ON a.id = p.attempt_id "
                "WHERE a.exam_id = %s AND p.id = %s", (exam_id, event_id)
            )
            if not cur.fetchone():
                return error("Không tìm thấy cảnh báo")
            cur.execute("UPDATE proctoring_events SET reviewed = TRUE, reviewed_by = %s, "
                        "reviewed_at = NOW(6) WHERE id = %s AND reviewed = FALSE", (user['id'], event_id))
            return True, "Đã đánh dấu cảnh báo", None
