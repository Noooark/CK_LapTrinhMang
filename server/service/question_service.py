"""
Question Service - Business logic for question management.
"""

import logging
from server.dao.question_dao import QuestionDAO
from server.dao.subject_dao import SubjectDAO

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
    def batch_create_questions(data: dict, user: dict) -> tuple[bool, str, dict | None]:
        """Create multiple questions at once (e.g. from file import)."""
        questions = data.get('questions', [])
        default_subject_id = data.get('subject_id')

        if not questions:
            return False, "Danh sách câu hỏi trống", None

        if user['role'] == 'TEACHER' and default_subject_id:
            subj = SubjectDAO.find_by_id(int(default_subject_id))
            if subj and subj.get('teacher_id') and subj['teacher_id'] != user['id']:
                return False, "Bạn không được phân công giảng dạy môn học này", None

        valid_questions = []
        required = ['content', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer']

        for idx, q in enumerate(questions, 1):
            sid = q.get('subject_id') or default_subject_id
            if not sid:
                return False, f"Câu số {idx} thiếu ID môn học", None

            for field in required:
                if not q.get(field):
                    return False, f"Câu số {idx} thiếu trường bắt buộc: {field}", None

            ans = str(q['correct_answer']).strip().upper()
            if ans not in ('A', 'B', 'C', 'D'):
                return False, f"Câu số {idx} có đáp án không hợp lệ: {ans}", None

            valid_questions.append({
                'subject_id': int(sid),
                'content': str(q['content']).strip(),
                'option_a': str(q['option_a']).strip(),
                'option_b': str(q['option_b']).strip(),
                'option_c': str(q['option_c']).strip(),
                'option_d': str(q['option_d']).strip(),
                'correct_answer': ans,
                'difficulty': q.get('difficulty', 'MEDIUM')
            })

        created_ids = QuestionDAO.create_batch(valid_questions)
        if created_ids:
            return True, f"Nạp thành công {len(created_ids)} câu hỏi vào ngân hàng đề!", {
                'created_ids': created_ids,
                'count': len(created_ids)
            }
        return False, "Lỗi cơ sở dữ liệu khi lưu danh sách câu hỏi", None

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
