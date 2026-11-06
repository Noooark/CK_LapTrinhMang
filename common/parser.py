"""
Quiz Question Parser - Supports parsing quiz questions from Word (.docx) and Text (.txt) files.
Conforms to standard Vietnamese quiz test formats.
"""

import os
import re
from typing import List, Dict, Any, Tuple, Optional


def normalize_difficulty(val: str) -> str:
    """Normalize difficulty string to 'EASY', 'MEDIUM', or 'HARD'."""
    v = val.strip().upper()
    if any(k in v for k in ["DE", "DỄ", "EASY", "NHẬN BIẾT", "1"]):
        return "EASY"
    if any(k in v for k in ["KHO", "KHÓ", "HARD", "VẬN DỤNG", "3"]):
        return "HARD"
    return "MEDIUM"


class QuestionParser:
    """Parses quiz questions from text, .docx, or .txt files."""

    QUESTION_HEADER_REGEX = re.compile(
        r'^(?:(?:câu|bài|question)\s*(\d+)[\.:\-\)\s]|(?:câu|bài|question)\s+(\d+)|(\d+)[\.:\)\/]\s+)',
        re.IGNORECASE
    )

    ANSWER_REGEX = re.compile(
        r'^(?:đáp án|đáp án đúng|đ\/a|key|answer|dap an)[\s\:\-\=]+([A-D])\b',
        re.IGNORECASE
    )

    DIFFICULTY_REGEX = re.compile(
        r'^(?:độ khó|mức độ|do kho|muc do|difficulty|level)[\s\:\-\=]+(.+)$',
        re.IGNORECASE
    )

    # Single option on line: A. or *A. or [A] or A)
    OPTION_REGEX = re.compile(
        r'^(?:\*|\s)*(\[)?([A-D])(\])?[\*\.:\-\)\s]\s*(.*)$',
        re.IGNORECASE
    )

    @classmethod
    def parse_file(cls, file_path: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Parse questions from a .docx or .txt file.
        Returns: (questions, errors)
        """
        if not os.path.exists(file_path):
            return [], [f"Tệp tin không tồn tại: {file_path}"]

        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".docx":
            return cls.parse_docx(file_path)
        elif ext in [".txt", ".text"]:
            return cls.parse_txt(file_path)
        else:
            return [], [f"Định dạng tệp không được hỗ trợ ({ext}). Vui lòng chọn tệp .docx hoặc .txt!"]

    @classmethod
    def parse_docx(cls, file_path: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Parse questions from a Microsoft Word .docx file."""
        try:
            import docx
        except ImportError:
            return [], ["Thư viện python-docx chưa được cài đặt."]

        try:
            doc = docx.Document(file_path)
            lines = []
            for p in doc.paragraphs:
                txt = p.text.strip()
                if txt:
                    lines.append(txt)
            for tbl in doc.tables:
                for row in tbl.rows:
                    for cell in row.cells:
                        txt = cell.text.strip()
                        if txt:
                            lines.append(txt)
            return cls.parse_lines(lines)
        except Exception as e:
            return [], [f"Lỗi khi đọc file Word: {str(e)}"]

    @classmethod
    def parse_txt(cls, file_path: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Parse questions from a plain text file."""
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1258", "cp1252"]
        content = None
        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue

        if content is None:
            return [], ["Không thể đọc file text (lỗi bảng mã mã hóa font tiếng Việt)."]

        return cls.parse_text(content)

    @classmethod
    def parse_text(cls, text: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Parse questions from a raw string."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return cls.parse_lines(lines)

    @classmethod
    def parse_lines(cls, lines: List[str]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        State-machine parser for list of text lines.
        """
        raw_blocks: List[List[str]] = []
        current_block: List[str] = []

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Check if this line starts a new question
            if cls.QUESTION_HEADER_REGEX.match(line_str):
                if current_block:
                    raw_blocks.append(current_block)
                current_block = [line_str]
            else:
                if current_block:
                    current_block.append(line_str)
                else:
                    # Header/title lines before Question 1 are ignored
                    pass

        if current_block:
            raw_blocks.append(current_block)

        questions: List[Dict[str, Any]] = []
        errors: List[str] = []

        if not raw_blocks:
            errors.append("Không tìm thấy câu hỏi nào. Đảm bảo câu hỏi bắt đầu bằng 'Câu 1:', '1.' hoặc tương tự.")
            return questions, errors

        for idx, block in enumerate(raw_blocks, 1):
            q_dict, err = cls._parse_single_block(block, idx)
            if err:
                errors.append(f"Câu {idx}: {err}")
            elif q_dict:
                questions.append(q_dict)

        return questions, errors

    @classmethod
    def _parse_single_block(cls, block: List[str], q_index: int) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Parse lines for one single question block."""
        if not block:
            return None, "Khối câu hỏi rỗng"

        header_line = block[0]
        # Remove question prefix like "Câu 1:" or "1."
        match_head = cls.QUESTION_HEADER_REGEX.match(header_line)
        if match_head:
            content_first_line = header_line[match_head.end():].strip()
        else:
            content_first_line = header_line

        content_parts = [content_first_line] if content_first_line else []
        options: Dict[str, str] = {}
        correct_answer: Optional[str] = None
        difficulty: str = "MEDIUM"

        current_opt = None

        for line in block[1:]:
            # 1. Check if line is explicit Answer
            ans_match = cls.ANSWER_REGEX.match(line)
            if ans_match:
                correct_answer = ans_match.group(1).upper()
                current_opt = None
                continue

            # 2. Check if line is explicit Difficulty
            diff_match = cls.DIFFICULTY_REGEX.match(line)
            if diff_match:
                difficulty = normalize_difficulty(diff_match.group(1))
                current_opt = None
                continue

            # 3. Check for multiple options in one line: e.g. "A. 10   B. 20   C. 30   D. 40"
            multi_opts = cls._try_parse_inline_options(line)
            if multi_opts:
                for letter, opt_text, is_correct in multi_opts:
                    options[letter] = opt_text
                    if is_correct:
                        correct_answer = letter
                current_opt = None
                continue

            # 4. Check for single option: A. or *A. or [A].
            single_opt = cls._try_parse_single_option(line)
            if single_opt:
                letter, opt_text, is_correct = single_opt
                options[letter] = opt_text
                if is_correct:
                    correct_answer = letter
                current_opt = letter
                continue

            # 5. Otherwise, line is a continuation
            if current_opt and current_opt in options:
                # Continuation of current option text
                options[current_opt] += " " + line
            else:
                # Continuation of question content
                content_parts.append(line)

        content = "\n".join(content_parts).strip()

        # Validation
        if not content:
            return None, "Nội dung câu hỏi bị trống"

        missing_opts = [opt for opt in ["A", "B", "C", "D"] if opt not in options or not options[opt].strip()]
        if missing_opts:
            return None, f"Thiếu phương án lựa chọn: {', '.join(missing_opts)}"

        if not correct_answer:
            return None, "Chưa chỉ định đáp án đúng (ví dụ: 'Đáp án: A' hoặc đánh dấu '*A.')"

        if correct_answer not in ("A", "B", "C", "D"):
            return None, f"Đáp án '{correct_answer}' không hợp lệ (phải là A, B, C, hoặc D)"

        return {
            "content": content,
            "option_a": options["A"].strip(),
            "option_b": options["B"].strip(),
            "option_c": options["C"].strip(),
            "option_d": options["D"].strip(),
            "correct_answer": correct_answer,
            "difficulty": difficulty
        }, None

    @classmethod
    def _try_parse_single_option(cls, line: str) -> Optional[Tuple[str, str, bool]]:
        """
        Check if line starts with an option like A., *A., [A], etc.
        Returns: (letter, text, is_correct) or None
        """
        line_clean = line.strip()
        is_marked = False

        # Check starting asterisk: *A.
        if line_clean.startswith("*"):
            is_marked = True
            line_clean = line_clean.lstrip("*").strip()

        # Check bracketed: [A] or [A].
        m_bracket = re.match(r'^\[([A-D])\][\.\:\-\s]*(.*)$', line_clean, re.IGNORECASE)
        if m_bracket:
            return m_bracket.group(1).upper(), m_bracket.group(2).strip(), True

        # Check standard: A. or A) or A: or A - or A*.
        m_std = re.match(r'^([A-D])(\*)?[\.:\-\)\s]\s*(.*)$', line_clean, re.IGNORECASE)
        if m_std:
            letter = m_std.group(1).upper()
            if m_std.group(2) == "*":
                is_marked = True
            return letter, m_std.group(3).strip(), is_marked

        return None

    @classmethod
    def _try_parse_inline_options(cls, line: str) -> Optional[List[Tuple[str, str, bool]]]:
        """
        Parse lines with multiple options, e.g.:
        "A. TCP    B. UDP    C. IP    D. ICMP"
        """
        # Find all option boundaries: A., B., C., D.
        # Pattern to split while keeping markers
        pattern = r'(?:^|\s+)([\*\[\(]?)([A-D])([\]\*\)]?[\.:\-\)\s])'
        matches = list(re.finditer(pattern, line, re.IGNORECASE))
        if len(matches) < 2:
            return None

        # Check if consecutive letters match (e.g. A then B, or B then C)
        letters = [m.group(2).upper() for m in matches]
        if letters != sorted(letters):
            return None

        results = []
        for i in range(len(matches)):
            m = matches[i]
            prefix_punct = m.group(1)
            letter = m.group(2).upper()
            suffix_punct = m.group(3)

            is_correct = ("*" in prefix_punct or "*" in suffix_punct or "[" in prefix_punct)

            start_idx = m.end()
            end_idx = matches[i+1].start() if i+1 < len(matches) else len(line)
            opt_text = line[start_idx:end_idx].strip()
            results.append((letter, opt_text, is_correct))

        return results
