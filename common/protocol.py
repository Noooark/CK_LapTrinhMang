import json
import struct
import socket
from enum import Enum
from typing import Any, Optional
from dataclasses import dataclass, asdict


class CommandType(str, Enum):
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    GET_USERS = "GET_USERS"
    CREATE_USER = "CREATE_USER"
    UPDATE_USER = "UPDATE_USER"
    DELETE_USER = "DELETE_USER"
    GET_SUBJECTS = "GET_SUBJECTS"
    CREATE_SUBJECT = "CREATE_SUBJECT"
    UPDATE_SUBJECT = "UPDATE_SUBJECT"
    DELETE_SUBJECT = "DELETE_SUBJECT"
    GET_QUESTIONS = "GET_QUESTIONS"
    CREATE_QUESTION = "CREATE_QUESTION"
    BATCH_CREATE_QUESTIONS = "BATCH_CREATE_QUESTIONS"
    UPDATE_QUESTION = "UPDATE_QUESTION"
    DELETE_QUESTION = "DELETE_QUESTION"
    GET_EXAMS = "GET_EXAMS"
    CREATE_EXAM = "CREATE_EXAM"
    UPDATE_EXAM = "UPDATE_EXAM"
    DELETE_EXAM = "DELETE_EXAM"
    START_EXAM = "START_EXAM"
    END_EXAM = "END_EXAM"
    GET_AVAILABLE_EXAMS = "GET_AVAILABLE_EXAMS"
    GET_EXAM_QUESTIONS = "GET_EXAM_QUESTIONS"
    SUBMIT_EXAM = "SUBMIT_EXAM"
    GET_RESULTS = "GET_RESULTS"
    GET_MY_RESULTS = "GET_MY_RESULTS"
    GET_EXAM_RESULTS = "GET_EXAM_RESULTS"
    GET_STATS = "GET_STATS"
    CHANGE_PASSWORD = "CHANGE_PASSWORD"
    RESET_PASSWORD = "RESET_PASSWORD"


@dataclass
class Request:
    command: str
    token: Optional[str] = None
    data: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "command": str(self.command),
            "token": self.token,
            "data": self.data or {}
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Request":
        return cls(
            command=data.get("command", ""),
            token=data.get("token"),
            data=data.get("data")
        )


@dataclass
class Response:
    status: str  # "SUCCESS" or "ERROR"
    message: str = ""
    data: Any = None

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "message": self.message,
            "data": self.data
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Response":
        return cls(
            status=data.get("status", "ERROR"),
            message=data.get("message", ""),
            data=data.get("data")
        )


def _recvall(sock: socket.socket, n: int) -> Optional[bytes]:
    """Helper to receive exactly n bytes or None on EOF/error."""
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return bytes(data)


def send_message(sock: socket.socket, obj: Any) -> bool:
    """
    Serialize obj to JSON and send with a 4-byte big-endian length prefix.
    obj can be a dict, Request, Response, or any JSON-serializable object.
    """
    try:
        if hasattr(obj, "to_dict"):
            payload_dict = obj.to_dict()
        elif isinstance(obj, dict):
            payload_dict = obj
        else:
            payload_dict = asdict(obj)

        raw_data = json.dumps(payload_dict, ensure_ascii=False, default=str).encode("utf-8")
        header = struct.pack(">I", len(raw_data))
        sock.sendall(header + raw_data)
        return True
    except (socket.error, OSError, TypeError) as e:
        print(f"[Protocol] Error sending message: {e}")
        return False


def receive_message(sock: socket.socket) -> Optional[dict]:
    """
    Read 4-byte length prefix, then read full payload and parse JSON.
    Returns dict or None on error/disconnection.
    """
    try:
        header = _recvall(sock, 4)
        if not header or len(header) < 4:
            return None
        length = struct.unpack(">I", header)[0]
        payload = _recvall(sock, length)
        if payload is None or len(payload) < length:
            return None
        return json.loads(payload.decode("utf-8"))
    except (socket.error, OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"[Protocol] Error receiving message: {e}")
        return None
