"""
Question Service - Business logic for question management.
"""

import logging
from server.dao.question_dao import QuestionDAO

logger = logging.getLogger(__name__)


class QuestionService:
    """Business logic for question operations."""

    @staticmethod
    def get_questions(data: dict, user: dict) -> tuple[bool, str, list]:
        """Get questions. Teachers see only their subjects' questions."""
        subject_id = data.get('subject_id')
        
        if user['role'] == 'TEACHER':
            # Teachers see questions from their subjects
            questions = QuestionDAO.find_by_teacher(user['id'])
            if subject_id:
                questions = [q for q in questions if q['subject_id'] == int(subject_id)]
        else:
            questions = QuestionDAO.find_all(subject_id=subject_id)
        
        return True, "Lấy danh sách câu hỏi thành công", questions

    @staticmethod
    def create_question(data: dict) -> tuple[bool, str, dict | None]:
        """Create a new question."""
        required = ['subject_id', 'content', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer']
        for field in required:
            if not data.get(field):
                return False, f"Thiếu trường bắt buộc: {field}", None

        if data['correct_answer'] not in ('A', 'B', 'C', 'D'):
            return False, "Đáp án đúng phải là A, B, C hoặc D", None

        new_id = QuestionDAO.create(data)
        if new_id:
            return True, "Tạo câu hỏi thành công", {'id': new_id}
        return False, "Lỗi khi tạo câu hỏi", None

    @staticmethod
    def update_question(data: dict) -> tuple[bool, str, None]:
        """Update a question."""
        question_id = data.get('id')
        if not question_id:
            return False, "Thiếu ID câu hỏi", None

        if QuestionDAO.update(question_id, data):
            return True, "Cập nhật câu hỏi thành công", None
        return False, "Lỗi khi cập nhật câu hỏi", None

    @staticmethod
    def delete_question(data: dict) -> tuple[bool, str, None]:
        """Delete a question."""
        question_id = data.get('id')
        if not question_id:
            return False, "Thiếu ID câu hỏi", None

        if QuestionDAO.delete(question_id):
            return True, "Xóa câu hỏi thành công", None
        return False, "Lỗi khi xóa câu hỏi", None
