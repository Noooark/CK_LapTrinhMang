"""Authorized JPEG evidence, private file storage and retention."""
import base64
import binascii
from io import BytesIO
import logging
import os
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from time import time
from uuid import UUID, uuid4

from PIL import Image, UnidentifiedImageError

from common.snapshots import MAX_BASE64_CHARS, MAX_HEIGHT, MAX_JPEG_BYTES, MAX_WIDTH, SNAPSHOT_EVENTS
from server.database import DatabaseConnection
from server.service.proctoring_service import error, valid_id


logger = logging.getLogger(__name__)
KEY = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")
UNAVAILABLE = "Ảnh bằng chứng không còn khả dụng."


class SnapshotService:
    def __init__(self, directory, days=7):
        if not 1 <= days <= 365:
            raise ValueError("QUIZ_SNAPSHOT_DAYS must be between 1 and 365")
        self.directory = Path(directory).resolve()
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if os.name != "nt" and self.directory.stat().st_mode & 0o077:
            raise PermissionError("Snapshot directory permissions must be private (0700)")
        self.days = days

    @classmethod
    def from_env(cls):
        directory = os.getenv("QUIZ_SNAPSHOT_DIR")
        return cls(directory, int(os.getenv("QUIZ_SNAPSHOT_DAYS", "7"))) if directory else None

    def _path(self, key):
        if not isinstance(key, str) or not KEY.fullmatch(key):
            raise ValueError("Invalid snapshot storage key")
        return self.directory / f"{key}.jpg"

    @staticmethod
    def _decode(value):
        if not isinstance(value, str) or not 0 < len(value) <= MAX_BASE64_CHARS:
            return None
        try:
            raw = base64.b64decode(value, validate=True)
            if not 0 < len(raw) <= MAX_JPEG_BYTES or not raw.endswith(b"\xff\xd9"):
                return None
            with Image.open(BytesIO(raw), formats=["JPEG"]) as image:
                if not (0 < image.width <= MAX_WIDTH and 0 < image.height <= MAX_HEIGHT):
                    return None
                # Normalize the JPEG and strip metadata or trailing data from untrusted clients.
                with BytesIO() as output:
                    image.convert("RGB").save(output, "JPEG", quality=75)
                    return output.getvalue() if output.tell() <= MAX_JPEG_BYTES else None
        except (binascii.Error, ValueError, OSError, UnidentifiedImageError, Image.DecompressionBombError):
            return None

    def _write(self, path, raw):
        temporary = None
        try:
            with NamedTemporaryFile(dir=self.directory, prefix=".evidence-", suffix=".tmp", delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def upload(self, data, user):
        if set(data) - {"attempt_id", "event_id", "image_format", "image_base64"}:
            return error("Thông tin ảnh bằng chứng không hợp lệ")
        attempt = data.get("attempt_id")
        event = data.get("event_id")
        if (not valid_id(attempt) or not isinstance(event, str) or len(event) != 36
                or data.get("image_format") != "jpeg"):
            return error("Thông tin ảnh bằng chứng không hợp lệ")
        try:
            event = str(UUID(event))
        except ValueError:
            return error("Mã sự kiện không hợp lệ")

        # The event row lock serializes duplicate uploads and keeps metadata tied to the file.
        with DatabaseConnection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT p.id, p.event_type, a.snapshot_consent, a.status, "
                "p.created_at >= NOW(6) - INTERVAL 120 SECOND AND p.created_at <= "
                "LEAST(a.deadline_at, COALESCE(e.end_time, a.deadline_at)) AS recent "
                "FROM proctoring_events p JOIN exam_attempts a ON a.id = p.attempt_id "
                "JOIN exams e ON e.id = a.exam_id "
                "WHERE p.attempt_id = %s AND p.event_id = %s AND a.student_id = %s FOR UPDATE",
                (attempt, event, user["id"]),
            )
            row = cur.fetchone()
            if not row or row["event_type"] not in SNAPSHOT_EVENTS or not row["snapshot_consent"]:
                return error("Sự kiện không cho phép lưu ảnh")
            cur.execute("SELECT event_id FROM proctoring_snapshots WHERE event_id = %s", (row["id"],))
            if cur.fetchone():
                return True, "Ảnh đã được lưu", None
            if not row["recent"] or row["status"] == "SUBMITTED":
                return error("Đã hết thời hạn gửi ảnh")
            raw = self._decode(data.get("image_base64"))
            if raw is None:
                return error("Ảnh JPEG không hợp lệ hoặc vượt giới hạn")
            key = str(uuid4())
            self._write(self._path(key), raw)
            cur.execute(
                "INSERT INTO proctoring_snapshots "
                "(event_id, attempt_id, storage_key, image_size, captured_at, expires_at) "
                "SELECT id, attempt_id, %s, %s, created_at, TIMESTAMPADD(DAY, %s, NOW(6)) "
                "FROM proctoring_events WHERE id = %s", (key, len(raw), self.days, row["id"]),
            )
        return True, "Đã lưu ảnh bằng chứng", None

    def get(self, data, user):
        event_id = data.get("event_id")
        if user["role"] not in {"ADMIN", "TEACHER"} or not valid_id(event_id, 2**63 - 1):
            return error(UNAVAILABLE)
        with DatabaseConnection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT s.storage_key, s.captured_at, p.event_type, p.face_count, e.title, u.username "
                "FROM proctoring_snapshots s JOIN proctoring_events p ON p.id = s.event_id "
                "JOIN exam_attempts a ON a.id = p.attempt_id JOIN exams e ON e.id = a.exam_id "
                "JOIN users u ON u.id = a.student_id WHERE s.event_id = %s AND s.expires_at > NOW(6) "
                "AND (%s = 'ADMIN' OR e.teacher_id = %s)",
                (event_id, user["role"], user["id"]),
            )
            row = cur.fetchone()
        if row:
            try:
                with self._path(row.pop("storage_key")).open("rb") as handle:
                    raw = handle.read(MAX_JPEG_BYTES + 1)
                if 0 < len(raw) <= MAX_JPEG_BYTES:
                    return True, "Đã tải ảnh", {**row, "image_base64": base64.b64encode(raw).decode("ascii")}
            except (OSError, ValueError):
                pass
        return error(UNAVAILABLE)

    def cleanup(self):
        with DatabaseConnection() as conn, conn.cursor() as cur:
            cur.execute("SELECT event_id, storage_key FROM proctoring_snapshots WHERE expires_at <= NOW(6)")
            for row in cur.fetchall():
                try:
                    self._path(row["storage_key"]).unlink(missing_ok=True)
                except (OSError, ValueError):
                    logger.warning("Could not remove expired snapshot for event %s", row["event_id"])
                    continue
                cur.execute("DELETE FROM proctoring_snapshots WHERE event_id = %s", (row["event_id"],))
            # Catch files left by interrupted writes or cascaded deletion of exam records.
            for path in self.directory.iterdir():
                if not (path.suffix == ".jpg" and KEY.fullmatch(path.stem)
                        or path.suffix == ".tmp" and path.name.startswith(".evidence-")):
                    continue
                try:
                    if time() - path.stat().st_mtime < 3600:
                        continue
                    if path.suffix == ".jpg":
                        cur.execute("SELECT 1 FROM proctoring_snapshots WHERE storage_key = %s", (path.stem,))
                        if cur.fetchone():
                            continue
                    path.unlink(missing_ok=True)
                except OSError:
                    logger.warning("Could not remove an orphaned snapshot")


if __name__ == "__main__":
    store = SnapshotService.from_env()
    if store is None:
        raise SystemExit("Set QUIZ_SNAPSHOT_DIR before running snapshot cleanup.")
    store.cleanup()
