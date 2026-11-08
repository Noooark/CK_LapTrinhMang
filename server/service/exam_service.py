"""
Exam Service - Business logic for exam management and submission.
"""

from common.camera import CAMERA_THRESHOLDS
from server.dao.exam_dao import ExamDAO
from server.dao.question_dao import QuestionDAO
from server.dao.result_dao import ResultDAO
from server.dao.subject_dao import SubjectDAO
from server.dao.user_dao import UserDAO

class ExamService:
    """Business logic for exam operations."""

    @staticmethod
    def get_exams(data: dict, user: dict) -> tuple[bool, str, list]:
        """Get exams. Teachers see only their exams."""
        if user['role'] == 'TEACHER':
            exams = ExamDAO.find_by_teacher(user['id'])
        else:
            exams = ExamDAO.find_all()
        return True, "Lấy danh sách đề thi thành công", exams

    @staticmethod
    def create_exam(data: dict, user: dict) -> tuple[bool, str, dict | None]:
        """Create an exam with questions."""
        title = data.get('title', '').strip()
        subject_id = data.get('subject_id')
        if not title or not subject_id:
            return False, "Thiếu tiêu đề hoặc môn học", None

        if type(data.get('camera_required', False)) is not bool:
            return False, "Cấu hình bắt buộc camera không hợp lệ", None
        snapshot_enabled = data.get("snapshot_enabled", False)
        if type(snapshot_enabled) is not bool or (snapshot_enabled and not data.get("camera_required")):
            return False, "Lưu ảnh bằng chứng cần bật camera", None
        for key, default in CAMERA_THRESHOLDS.values():
            value = data.get(key, default)
            if type(value) is not int or not 1 <= value <= 300:
                return False, "Ngưỡng camera phải là số nguyên từ 1 đến 300 giây", None

        # Set teacher_id from logged-in user
        data['teacher_id'] = user['id']

        # Handle question selection
        question_ids = list(data.get('question_ids', []))
        new_questions = data.get('new_questions', [])

        # If new questions were supplied directly (e.g. from file import during exam creation)
        if new_questions:
            valid_new = []
            for q in new_questions:
                valid_new.append({
                    'subject_id': int(subject_id),
                    'content': str(q['content']).strip(),
                    'option_a': str(q['option_a']).strip(),
                    'option_b': str(q['option_b']).strip(),
                    'option_c': str(q['option_c']).strip(),
                    'option_d': str(q['option_d']).strip(),
                    'correct_answer': str(q['correct_answer']).strip().upper(),
                    'difficulty': q.get('difficulty', 'MEDIUM')
                })
            created_new_ids = QuestionDAO.create_batch(valid_new)
            question_ids.extend(created_new_ids)

        random_count = data.get('random_count', 0)
        if not random_count and data.get('random'):
            random_count = data.get('total_questions', 0)

        if random_count > 0:
            # Random selection from subject
            random_questions = QuestionDAO.find_random(subject_id, random_count)
            question_ids = [q['id'] for q in random_questions]

        if not question_ids:
            return False, "Đề thi phải có ít nhất 1 câu hỏi", None

        data['total_questions'] = len(question_ids)

        exam_id = ExamDAO.create(data)
        if not exam_id:
            return False, "Lỗi khi tạo đề thi", None

        # Add questions to exam
        if not ExamDAO.add_questions(exam_id, question_ids):
            ExamDAO.delete(exam_id)
            return False, "Lỗi khi thêm câu hỏi vào đề thi", None

        return True, "Tạo đề thi thành công", {'id': exam_id, 'total_questions': len(question_ids)}

    @staticmethod
    def start_exam(data: dict, user: dict) -> tuple[bool, str, None]:
        """Start an exam (DRAFT -> ACTIVE)."""
        exam_id = data.get('exam_id') or data.get('id')
        if not exam_id:
            return False, "Thiếu ID đề thi", None

        exam = ExamDAO.find_by_id(exam_id)
        if not exam or (user['role'] != 'ADMIN' and exam['teacher_id'] != user['id']):
            return False, "Bạn không có quyền quản lý đề thi này", None

        if exam['status'] != 'DRAFT':
            return False, "Chỉ có thể bắt đầu đề thi ở trạng thái Nháp", None

        if ExamDAO.update_status(exam_id, 'ACTIVE'):
            return True, "Bắt đầu phiên thi thành công", None
        return False, "Lỗi khi bắt đầu phiên thi", None

    @staticmethod
    def end_exam(data: dict, user: dict) -> tuple[bool, str, None]:
        """End an exam (ACTIVE -> ENDED)."""
        exam_id = data.get('exam_id') or data.get('id')
        if not exam_id:
            return False, "Thiếu ID đề thi", None

        exam = ExamDAO.find_by_id(exam_id)
        if not exam or (user['role'] != 'ADMIN' and exam['teacher_id'] != user['id']):
            return False, "Bạn không có quyền quản lý đề thi này", None

        if exam['status'] != 'ACTIVE':
            return False, "Chỉ có thể kết thúc đề thi đang hoạt động", None

        if ExamDAO.update_status(exam_id, 'ENDED'):
            return True, "Kết thúc phiên thi thành công", None
        return False, "Lỗi khi kết thúc phiên thi", None

    @staticmethod
    def delete_exam(data: dict, user: dict) -> tuple[bool, str, None]:
        """Delete an exam."""
        exam_id = data.get('exam_id') or data.get('id')
        if not exam_id:
            return False, "Thiếu ID đề thi", None

        exam = ExamDAO.find_by_id(exam_id)
        if not exam or (user['role'] != 'ADMIN' and exam['teacher_id'] != user['id']):
            return False, "Bạn không có quyền quản lý đề thi này", None

        if ExamDAO.delete(exam_id):
            return True, "Xóa đề thi thành công", None
        return False, "Lỗi khi xóa đề thi", None

    @staticmethod
    def get_available_exams(user: dict) -> tuple[bool, str, list]:
        """Get active exams for students."""
        exams = ExamDAO.find_active()
        # Mark which exams the student has already taken
        for exam in exams:
            exam['already_taken'] = ResultDAO.has_taken_exam(user['id'], exam['id'])
        return True, "Lấy danh sách bài thi thành công", exams

    @staticmethod
    def get_exam_questions(data: dict, user: dict) -> tuple[bool, str, list]:
        """Get questions for an exam."""
        exam_id = data.get('exam_id') or data.get('id')
        if not exam_id:
            return False, "Thiếu ID đề thi", None

        # Students don't see correct answers during exam
        include_answer = user['role'] != 'STUDENT'
        questions = ExamDAO.get_exam_questions(exam_id, include_answer=include_answer)
        return True, "Lấy câu hỏi đề thi thành công", questions

    @staticmethod
    def get_results(data: dict, user: dict) -> tuple[bool, str, list]:
        """Get exam results (for teachers viewing their exams)."""
        exam_id = data.get('exam_id') or data.get('id')
        if exam_id:
            results = ResultDAO.get_results_by_exam(exam_id)
        else:
            results = []
        return True, "Lấy kết quả thành công", results

    @staticmethod
    def get_my_results(user: dict) -> tuple[bool, str, list]:
        """Get results for the logged-in student."""
        results = ResultDAO.get_results_by_student(user['id'])
        return True, "Lấy lịch sử bài thi thành công", results

    @staticmethod
    def get_exam_results(data: dict) -> tuple[bool, str, dict]:
        """Get detailed results and stats for an exam."""
        exam_id = data.get('exam_id') or data.get('id')
        if not exam_id:
            return False, "Thiếu ID đề thi", None

        results = ResultDAO.get_results_by_exam(exam_id)
        stats = ResultDAO.get_exam_stats(exam_id)
        return True, "Lấy kết quả đề thi thành công", {'results': results, 'stats': stats}

    @staticmethod
    def get_stats() -> tuple[bool, str, dict]:
        """Get overall system statistics."""
        stats = {
            'total_users': UserDAO.count_by_role(),
            'total_teachers': UserDAO.count_by_role('TEACHER'),
            'total_students': UserDAO.count_by_role('STUDENT'),
            'total_subjects': SubjectDAO.count(),
            'total_questions': QuestionDAO.count(),
            'total_exams': ExamDAO.count(),
        }
        return True, "Lấy thống kê thành công", stats
