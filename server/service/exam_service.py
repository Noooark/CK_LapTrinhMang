"""
Exam Service - Business logic for exam management and submission.
"""

import logging
from server.dao.exam_dao import ExamDAO
from server.dao.question_dao import QuestionDAO
from server.dao.result_dao import ResultDAO
from server.dao.subject_dao import SubjectDAO
from server.dao.user_dao import UserDAO

logger = logging.getLogger(__name__)


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

        # Set teacher_id from logged-in user
        data['teacher_id'] = user['id']

        # Handle question selection
        question_ids = data.get('question_ids', [])
        random_count = data.get('random_count', 0)

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
    def start_exam(data: dict) -> tuple[bool, str, None]:
        """Start an exam (DRAFT -> ACTIVE)."""
        exam_id = data.get('exam_id') or data.get('id')
        if not exam_id:
            return False, "Thiếu ID đề thi", None

        exam = ExamDAO.find_by_id(exam_id)
        if not exam:
            return False, "Không tìm thấy đề thi", None

        if exam['status'] != 'DRAFT':
            return False, "Chỉ có thể bắt đầu đề thi ở trạng thái Nháp", None

        if ExamDAO.update_status(exam_id, 'ACTIVE'):
            return True, "Bắt đầu phiên thi thành công", None
        return False, "Lỗi khi bắt đầu phiên thi", None

    @staticmethod
    def end_exam(data: dict) -> tuple[bool, str, None]:
        """End an exam (ACTIVE -> ENDED)."""
        exam_id = data.get('exam_id') or data.get('id')
        if not exam_id:
            return False, "Thiếu ID đề thi", None

        exam = ExamDAO.find_by_id(exam_id)
        if not exam:
            return False, "Không tìm thấy đề thi", None

        if exam['status'] != 'ACTIVE':
            return False, "Chỉ có thể kết thúc đề thi đang hoạt động", None

        if ExamDAO.update_status(exam_id, 'ENDED'):
            return True, "Kết thúc phiên thi thành công", None
        return False, "Lỗi khi kết thúc phiên thi", None

    @staticmethod
    def delete_exam(data: dict) -> tuple[bool, str, None]:
        """Delete an exam."""
        exam_id = data.get('exam_id') or data.get('id')
        if not exam_id:
            return False, "Thiếu ID đề thi", None

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
    def submit_exam(data: dict, user: dict) -> tuple[bool, str, dict | None]:
        """Submit exam answers and calculate score."""
        exam_id = data.get('exam_id')
        answers = data.get('answers', {})  # {question_id: selected_answer}

        if not exam_id:
            return False, "Thiếu ID đề thi", None

        # Check if already taken
        if ResultDAO.has_taken_exam(user['id'], exam_id):
            return False, "Bạn đã làm bài thi này rồi", None

        # Get exam questions with correct answers
        questions = ExamDAO.get_exam_questions(exam_id, include_answer=True)
        if not questions:
            return False, "Không tìm thấy câu hỏi cho đề thi", None

        # Grade the exam
        correct_count = 0
        total_questions = len(questions)
        answer_records = []

        for q in questions:
            q_id = str(q['id'])
            selected = answers.get(q_id, '')
            is_correct = selected.upper() == q['correct_answer'].upper() if selected else False
            if is_correct:
                correct_count += 1
            answer_records.append({
                'question_id': q['id'],
                'selected_answer': selected,
                'is_correct': is_correct
            })

        # Calculate score (10-point scale)
        score = round((correct_count / total_questions) * 10, 2) if total_questions > 0 else 0

        # Save result
        result_data = {
            'exam_id': exam_id,
            'student_id': user['id'],
            'correct_count': correct_count,
            'total_questions': total_questions,
            'score': score
        }

        result_id = ResultDAO.create_result(result_data)
        if not result_id:
            return False, "Lỗi khi lưu kết quả", None

        # Save individual answers
        ResultDAO.save_answers(result_id, answer_records)

        result_info = {
            'result_id': result_id,
            'correct_count': correct_count,
            'total_questions': total_questions,
            'score': score
        }

        logger.info(f"Student {user['username']} submitted exam {exam_id}: {score}/10 ({correct_count}/{total_questions})")
        return True, f"Nộp bài thành công! Điểm: {score}/10 ({correct_count}/{total_questions} câu đúng)", result_info

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
