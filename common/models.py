from enum import Enum
from dataclasses import dataclass, asdict
from typing import Optional, Any


class Role(str, Enum):
    ADMIN = "ADMIN"
    TEACHER = "TEACHER"
    STUDENT = "STUDENT"


@dataclass
class User:
    id: Optional[int] = None
    username: str = ""
    password: str = ""
    full_name: str = ""
    email: str = ""
    role: str = Role.STUDENT.value
    is_active: bool = True
    created_at: Optional[Any] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(
            id=data.get("id"),
            username=data.get("username", ""),
            password=data.get("password", ""),
            full_name=data.get("full_name", ""),
            email=data.get("email", ""),
            role=data.get("role", Role.STUDENT.value),
            is_active=bool(data.get("is_active", True)),
            created_at=data.get("created_at")
        )


@dataclass
class Subject:
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    teacher_id: Optional[int] = None
    teacher_name: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Subject":
        return cls(
            id=data.get("id"),
            name=data.get("name", ""),
            description=data.get("description", ""),
            teacher_id=data.get("teacher_id"),
            teacher_name=data.get("teacher_name")
        )


@dataclass
class Question:
    id: Optional[int] = None
    subject_id: Optional[int] = None
    content: str = ""
    option_a: str = ""
    option_b: str = ""
    option_c: str = ""
    option_d: str = ""
    correct_answer: str = "A"
    difficulty: str = "MEDIUM"
    subject_name: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Question":
        return cls(
            id=data.get("id"),
            subject_id=data.get("subject_id"),
            content=data.get("content", ""),
            option_a=data.get("option_a", ""),
            option_b=data.get("option_b", ""),
            option_c=data.get("option_c", ""),
            option_d=data.get("option_d", ""),
            correct_answer=data.get("correct_answer", "A"),
            difficulty=data.get("difficulty", "MEDIUM"),
            subject_name=data.get("subject_name")
        )


@dataclass
class Exam:
    id: Optional[int] = None
    title: str = ""
    subject_id: Optional[int] = None
    teacher_id: Optional[int] = None
    duration_minutes: int = 30
    total_questions: int = 0
    status: str = "DRAFT"  # DRAFT, ACTIVE, ENDED
    start_time: Optional[Any] = None
    end_time: Optional[Any] = None
    subject_name: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Exam":
        return cls(
            id=data.get("id"),
            title=data.get("title", ""),
            subject_id=data.get("subject_id"),
            teacher_id=data.get("teacher_id"),
            duration_minutes=int(data.get("duration_minutes", 30)),
            total_questions=int(data.get("total_questions", 0)),
            status=data.get("status", "DRAFT"),
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            subject_name=data.get("subject_name")
        )


@dataclass
class ExamResult:
    id: Optional[int] = None
    exam_id: Optional[int] = None
    student_id: Optional[int] = None
    correct_count: int = 0
    total_questions: int = 0
    score: float = 0.0
    submitted_at: Optional[Any] = None
    exam_title: Optional[str] = None
    student_name: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ExamResult":
        return cls(
            id=data.get("id"),
            exam_id=data.get("exam_id"),
            student_id=data.get("student_id"),
            correct_count=int(data.get("correct_count", 0)),
            total_questions=int(data.get("total_questions", 0)),
            score=float(data.get("score", 0.0)),
            submitted_at=data.get("submitted_at"),
            exam_title=data.get("exam_title"),
            student_name=data.get("student_name")
        )
