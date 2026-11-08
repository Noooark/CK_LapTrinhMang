"""Opt-in test. Creates a uniquely named test schema and keeps it for inspection."""
from concurrent.futures import ThreadPoolExecutor
import base64
from io import BytesIO
import os
from pathlib import Path
import secrets
import subprocess
import sys
import threading
import tempfile
import time
import unittest
from uuid import uuid4
from unittest.mock import Mock, patch

import bcrypt
import pymysql
from PIL import Image

from client.network import ServerConnection
from server.database import DatabaseConnection
from server.main import QuizServer, tls_context_from_env
from server.service.snapshot_service import SnapshotService


@unittest.skipUnless(os.getenv("QUIZ_TEST_DATABASE") == "1", "requires an isolated SQL test schema")
class TCPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = DatabaseConnection._config
        cls.addClassCleanup(setattr, DatabaseConnection, "_config", previous)
        config = DatabaseConnection._get_config().copy()
        schema = "quiz_phase1_test_" + uuid4().hex[:10]
        config["db_name"] = schema
        with pymysql.connect(host=config["host"], port=config["port"], user=config["user"],
                             password=config["password"], autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(f"CREATE DATABASE `{schema}` CHARACTER SET utf8mb4")
        print(f"Isolated test schema: {schema}", flush=True)
        DatabaseConnection._config = config
        root = Path(__file__).resolve().parents[1]
        original = (root / "database/schema.sql").read_text(encoding="utf-8")
        tables = original[original.index("CREATE TABLE"):original.index("-- DỮ LIỆU MẪU")]
        migration = (root / "database/migrations/add_proctoring.sql").read_text(encoding="utf-8")
        cls.password = secrets.token_hex(12)
        password_hash = bcrypt.hashpw(cls.password.encode(), bcrypt.gensalt(rounds=4)).decode()
        with DatabaseConnection() as conn, conn.cursor() as cur:
            for sql in tables.split(";")[:-1]:
                cur.execute(sql)
            for name, role in [("teacher_a", "TEACHER"), ("teacher_b", "TEACHER"),
                               ("student_a", "STUDENT"), ("student_b", "STUDENT"),
                               ("student_c", "STUDENT")]:
                cur.execute("INSERT INTO users (username, password, full_name, role) VALUES (%s, %s, %s, %s)",
                            (name, password_hash, name, role))
            cur.execute("INSERT INTO subjects (name, teacher_id) VALUES ('Test', 1)")
            cur.execute(
                "INSERT INTO questions (subject_id, content, option_a, option_b, option_c, option_d, correct_answer) "
                "VALUES (1, 'Question', 'A', 'B', 'C', 'D', 'A')"
            )
            for sql in migration.split(";")[:-1]:
                cur.execute(sql)
            camera_migration = (root / "database/migrations/add_camera_proctoring.sql").read_text(encoding="utf-8")
            for sql in camera_migration.split(";")[:-1]:
                cur.execute(sql)
            evidence_migration = (root / "database/migrations/add_camera_evidence.sql").read_text(encoding="utf-8")
            for sql in evidence_migration.split(";")[:-1]:
                cur.execute(sql)
            phone_migration = (root / "database/migrations/add_camera_phone_detection.sql").read_text(encoding="utf-8")
            for sql in phone_migration.split(";")[:-1]:
                cur.execute(sql)
            for sql in migration.split(";")[:-1]:
                cur.execute(sql)

        tls_context = tls_context_from_env()
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.snapshots = SnapshotService(directory.name) if tls_context else None
        cls.server = QuizServer(host="127.0.0.1", port=0, tls_context=tls_context, snapshots=cls.snapshots)
        cls.server_thread = threading.Thread(target=cls.server.start, daemon=True)
        cls.server_thread.start()
        cls.addClassCleanup(cls.stop_server)
        limit = time.monotonic() + 5
        while not cls.server.running and time.monotonic() < limit:
            time.sleep(0.01)
        if not cls.server.running:
            raise RuntimeError("Test server did not start")
        cls.port = cls.server.server_socket.getsockname()[1]

    @classmethod
    def stop_server(cls):
        cls.server.stop()
        cls.server_thread.join(3)

    def client(self, username):
        conn = ServerConnection("127.0.0.1", self.port)
        self.addCleanup(conn.disconnect)
        login = conn.send_request("LOGIN", {"username": username, "password": self.password})
        token = self.success(login)["token"]
        return conn, lambda command, **data: conn.send_request(command, data, token)

    def success(self, response):
        self.assertEqual(response["status"], "SUCCESS", response)
        return response["data"]

    def new_exam(self, teacher, **settings):
        exam_id = self.success(teacher("CREATE_EXAM", title="Demo", subject_id=1, question_ids=[1],
                                       duration_minutes=10, **settings))["id"]
        self.success(teacher("START_EXAM", exam_id=exam_id))
        return exam_id

    def test_camera_metadata_validation_and_monitoring(self):
        _, teacher = self.client("teacher_a")
        _, other_teacher = self.client("teacher_b")
        connection, student = self.client("student_a")
        _, other_student = self.client("student_b")
        exam_id = self.new_exam(teacher, camera_required=True, multiple_faces_threshold_seconds=2)
        self.assertEqual(student("START_EXAM_ATTEMPT", exam_id=exam_id)["status"], "ERROR")
        attempt = self.success(student("START_EXAM_ATTEMPT", exam_id=exam_id, camera_ready=True))
        self.assertEqual(attempt["camera_thresholds"]["multiple_faces_threshold_seconds"], 2)
        attempt_id = attempt["attempt_id"]
        event = dict(attempt_id=attempt_id, event_id=str(uuid4()), event_type="CAMERA_MULTIPLE_FACES",
                     duration_seconds=2.3, face_count=2)
        for extra in ({"image": "image-bytes"}, {"face_count": True}, {"duration_seconds": 1.9}):
            self.assertEqual(student("REPORT_EXAM_EVENT", **{**event, **extra})["status"], "ERROR")
        self.assertEqual(other_student("REPORT_EXAM_EVENT", **event)["status"], "ERROR")
        self.assertEqual(other_teacher("GET_EXAM_EVENTS", exam_id=exam_id)["status"], "ERROR")
        self.success(student("REPORT_EXAM_EVENT", **event))
        connection.disconnect()
        self.success(student("EXAM_HEARTBEAT", attempt_id=attempt_id))
        self.success(student("REPORT_EXAM_EVENT", **event))
        status = self.success(teacher("GET_MONITORING_STATUS", exam_id=exam_id))[0]
        self.assertEqual((status["camera_status"], status["event_count"]), ("CAMERA_MULTIPLE_FACES", 1))
        self.success(student("REPORT_EXAM_EVENT", attempt_id=attempt_id, event_id=str(uuid4()),
                             event_type="CAMERA_RECOVERED"))
        events = self.success(teacher("GET_EXAM_EVENTS", exam_id=exam_id))["events"]
        self.assertEqual(len(events), 1)
        self.assertEqual((events[0]["severity"], events[0]["face_count"]), ("WARNING", 2))
        status = self.success(teacher("GET_MONITORING_STATUS", exam_id=exam_id))[0]
        self.assertEqual(status["camera_status"], "CAMERA_RECOVERED")
        for _ in range(8):
            self.success(student("REPORT_EXAM_EVENT", attempt_id=attempt_id, event_id=str(uuid4()),
                                 event_type="CAMERA_RECOVERED"))
        limited = student("REPORT_EXAM_EVENT", attempt_id=attempt_id, event_id=str(uuid4()),
                          event_type="CAMERA_RECOVERED")
        self.assertEqual(limited["data"], {"retry_after_seconds": 2})
        self.success(student("REPORT_EXAM_EVENT", **event))
        result = self.success(student("SUBMIT_EXAM", exam_id=exam_id, attempt_id=attempt_id,
                                      answers={"1": "A"}))
        self.assertEqual(result["score"], 10)

    def test_snapshot_round_trip_roles_retries_and_expiry(self):
        if not self.snapshots:
            self.skipTest("requires QUIZ_TLS_CERT, QUIZ_TLS_KEY and QUIZ_TLS_CA")
        wrong_host = ServerConnection("localhost", self.port)
        self.addCleanup(wrong_host.disconnect)
        self.assertFalse(wrong_host.connect())
        plain = ServerConnection("127.0.0.1", self.port, tls_ca="")
        self.addCleanup(plain.disconnect)
        self.assertEqual(plain.send_request("GET_EXAM_SNAPSHOT", {"event_id": 1})["status"], "ERROR")
        _, teacher = self.client("teacher_a")
        _, other_teacher = self.client("teacher_b")
        student_connection, student = self.client("student_a")
        _, other_student = self.client("student_b")
        exam_id = self.new_exam(teacher, camera_required=True, snapshot_enabled=True)
        settings = {"exam_id": exam_id, "camera_ready": True}
        declined = other_student("START_EXAM_ATTEMPT", **settings)
        self.assertEqual(declined["status"], "ERROR")
        accepted = self.success(other_student("START_EXAM_ATTEMPT", **settings, snapshot_consent=True))
        self.assertTrue(accepted["snapshot_consent"])
        attempt_id = self.success(student("START_EXAM_ATTEMPT", **settings, snapshot_consent=True))["attempt_id"]
        event_uuid = str(uuid4())
        event = {"attempt_id": attempt_id, "event_id": event_uuid,
                 "event_type": "CAMERA_PHONE_DETECTED", "duration_seconds": 2.1}
        self.assertEqual(student("REPORT_EXAM_EVENT", **{**event, "duration_seconds": 1.9})["status"], "ERROR")
        self.success(student("REPORT_EXAM_EVENT", **event))
        row = self.success(teacher("GET_EXAM_EVENTS", exam_id=exam_id))["events"][0]
        self.assertFalse(row["has_snapshot"])
        with BytesIO() as output:
            Image.new("RGB", (40, 30), "#335577").save(output, "JPEG")
            encoded = base64.b64encode(output.getvalue()).decode("ascii")
        upload = {"attempt_id": attempt_id, "event_id": event_uuid,
                  "image_format": "jpeg", "image_base64": encoded}
        for invalid in ({"image_base64": "YQ=="}, {"image_base64": "A" * 300_000}, {"event_id": "../photo"}):
            self.assertEqual(student("UPLOAD_EXAM_SNAPSHOT", **{**upload, **invalid})["status"], "ERROR")
        self.assertEqual(other_student("UPLOAD_EXAM_SNAPSHOT", **upload)["status"], "ERROR")
        student_connection.disconnect()
        self.assertFalse(self.success(teacher("GET_EXAM_EVENTS", exam_id=exam_id))["events"][0]["has_snapshot"])
        self.success(student("UPLOAD_EXAM_SNAPSHOT", **upload))
        self.success(student("UPLOAD_EXAM_SNAPSHOT", **upload))
        self.assertEqual(len(list(self.snapshots.directory.glob("*.jpg"))), 1)
        self.assertTrue(self.success(teacher("GET_EXAM_EVENTS", exam_id=exam_id))["events"][0]["has_snapshot"])
        snapshot = self.success(teacher("GET_EXAM_SNAPSHOT", event_id=row["id"]))
        with Image.open(BytesIO(base64.b64decode(snapshot["image_base64"]))) as decoded:
            self.assertEqual(decoded.size, (40, 30))
        self.assertNotIn("storage_key", snapshot)
        self.assertEqual(other_teacher("GET_EXAM_SNAPSHOT", event_id=row["id"])["status"], "ERROR")
        self.assertEqual(other_student("GET_EXAM_SNAPSHOT", event_id=row["id"])["status"], "ERROR")
        with DatabaseConnection() as conn, conn.cursor() as cur:
            cur.execute("UPDATE proctoring_snapshots SET expires_at=NOW(6) WHERE event_id=%s", (row["id"],))
        self.assertEqual(teacher("GET_EXAM_SNAPSHOT", event_id=row["id"])["status"], "ERROR")
        self.snapshots.cleanup()
        self.assertFalse(list(self.snapshots.directory.glob("*.jpg")))
        self.assertFalse(self.success(teacher("GET_EXAM_EVENTS", exam_id=exam_id))["events"][0]["has_snapshot"])

    def test_event_ownership_idempotence_timeout_reconnect_and_grading(self):
        _, teacher = self.client("teacher_a")
        _, other_teacher = self.client("teacher_b")
        connection, student = self.client("student_a")
        _, other_student = self.client("student_b")
        exam_id = self.new_exam(teacher)
        self.assertEqual(other_teacher("END_EXAM", exam_id=exam_id)["status"], "ERROR")
        attempt = self.success(student("START_EXAM_ATTEMPT", exam_id=exam_id))
        self.assertNotIn("correct_answer", attempt["questions"][0])
        attempt_id = attempt["attempt_id"]
        event = dict(attempt_id=attempt_id, event_id=str(uuid4()), event_type="FOCUS_LOST",
                     duration_seconds=6.5)
        self.assertEqual(other_student("REPORT_EXAM_EVENT", **event)["status"], "ERROR")
        self.assertEqual(student("REPORT_EXAM_EVENT", **{**event, "duration_seconds": True})["status"], "ERROR")
        self.success(student("REPORT_EXAM_EVENT", **event))
        self.success(student("REPORT_EXAM_EVENT", **event))
        for command in ("GET_EXAM_EVENTS", "GET_MONITORING_STATUS", "ACKNOWLEDGE_EXAM_EVENT"):
            self.assertEqual(other_teacher(command, exam_id=exam_id, id=1)["status"], "ERROR")
        history = self.success(teacher("GET_EXAM_EVENTS", exam_id=exam_id))["events"]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["duration_seconds"], 6.5)
        self.success(teacher("ACKNOWLEDGE_EXAM_EVENT", exam_id=exam_id, id=history[0]["id"]))
        self.assertTrue(self.success(teacher("GET_EXAM_EVENTS", exam_id=exam_id))["events"][0]["reviewed"])

        connection.disconnect()
        with DatabaseConnection() as conn, conn.cursor() as cur:
            cur.execute("UPDATE exam_attempts SET last_heartbeat = NOW(6) - INTERVAL 31 SECOND WHERE id=%s",
                        (attempt_id,))
        limit = time.monotonic() + 6
        while True:
            status = self.success(teacher("GET_MONITORING_STATUS", exam_id=exam_id))[0]
            if status["status"] == "INTERRUPTED" or time.monotonic() >= limit:
                break
            time.sleep(0.15)
        self.assertEqual(status["status"], "INTERRUPTED")
        self.assertEqual(status["latest_event"], "HEARTBEAT_TIMEOUT")
        self.success(student("EXAM_HEARTBEAT", attempt_id=attempt_id))
        self.success(student("EXAM_HEARTBEAT", attempt_id=attempt_id))
        status = self.success(teacher("GET_MONITORING_STATUS", exam_id=exam_id))[0]
        self.assertEqual((status["status"], status["event_count"]), ("IN_PROGRESS", 2))
        payload = dict(exam_id=exam_id, attempt_id=attempt_id, answers={"1": "a"})
        first = self.success(student("SUBMIT_EXAM", **payload))
        second = self.success(student("SUBMIT_EXAM", **payload))
        self.assertEqual(first, second)
        self.assertEqual(first["score"], 10)
        self.assertTrue(self.success(student("EXAM_HEARTBEAT", attempt_id=attempt_id))["finished"])
        with DatabaseConnection() as conn, conn.cursor() as cur:
            cur.execute("SELECT selected_answer, is_correct FROM exam_answers WHERE result_id=%s",
                        (first["result_id"],))
            self.assertEqual(cur.fetchall(), [{"selected_answer": "A", "is_correct": 1}])

    def test_concurrent_attempts_double_submit_and_deadline(self):
        _, teacher = self.client("teacher_a")
        exam_id = self.new_exam(teacher)
        students = [self.client(name)[1] for name in ("student_a", "student_b", "student_c")]
        _, same_student = self.client("student_a")
        with ThreadPoolExecutor(max_workers=4) as pool:
            attempts = list(pool.map(lambda request: self.success(
                request("START_EXAM_ATTEMPT", exam_id=exam_id))["attempt_id"], [*students, same_student]))
            self.assertEqual(attempts[0], attempts[3])
            self.assertEqual(len(set(attempts)), 3)
            with DatabaseConnection() as conn, conn.cursor() as cur:
                cur.execute("UPDATE exam_attempts SET deadline_at = NOW(6) - INTERVAL 121 SECOND WHERE id=%s",
                            (attempts[2],))
            self.success(teacher("END_EXAM", exam_id=exam_id))
            responses = list(pool.map(lambda item: item[0](
                "SUBMIT_EXAM", exam_id=exam_id, attempt_id=item[1], answers={}),
                zip([*students, same_student], attempts)))
        results = [self.success(responses[index]) for index in (0, 1, 3)]
        self.assertEqual(results[0], results[2])
        self.assertEqual(results[1]["score"], 0)
        self.assertEqual(responses[2]["status"], "ERROR")
        self.assertIn("thời hạn", responses[2]["message"])

    @unittest.skipUnless(os.getenv("QUIZ_TEST_DESKTOP") == "1" and sys.platform == "win32",
                         "requires Windows desktop")
    def test_desktop_clients_show_external_focus_event_and_submit(self):
        import customtkinter as ctk
        from client.ui.student.exam_taking import ExamTakingPanel
        from client.ui.teacher.monitoring_panel import MonitoringPanel
        from test_proctoring_client import destroy_test_root

        _, teacher = self.client("teacher_a")
        exam_id = self.new_exam(teacher)

        def login(username):
            connection = ServerConnection("127.0.0.1", self.port)
            self.addCleanup(connection.disconnect)
            token = self.success(connection.send_request(
                "LOGIN", {"username": username, "password": self.password}
            ))["token"]
            return connection, token

        root = ctk.CTk()
        self.addCleanup(destroy_test_root, root)
        root.geometry("1100x700")
        teacher_panel = MonitoringPanel(root, *login("teacher_a"))
        teacher_panel.pack(fill="both", expand=True)
        self.addCleanup(teacher_panel.destroy)
        student_window = ctk.CTkToplevel(root)
        student_window.geometry("1100x700")
        result = Mock()
        student_panel = ExamTakingPanel(student_window, *login("student_a"), {"id": exam_id}, result)
        student_panel.pack(fill="both", expand=True)
        self.addCleanup(student_panel.destroy)

        def pump_until(condition, timeout=6):
            limit = time.monotonic() + timeout
            while not condition() and time.monotonic() < limit:
                root.update()
                time.sleep(0.02)
            self.assertTrue(condition())

        pump_until(lambda: student_window.state() == "zoomed"
                   and exam_id in teacher_panel.exams.values())
        label = next(key for key, value in teacher_panel.exams.items() if value == exam_id)
        teacher_panel.exam_menu.set(label)
        teacher_panel._select_exam(label)
        student_window.focus_force()
        pump_until(lambda: student_window.focus_displayof() is not None)
        student_panel.option_var.set("A")
        student_panel._on_option_selected()

        child_code = (
            "import tkinter as t; r=t.Tk(); r.title('Ứng dụng khác'); "
            "r.geometry('300x160'); r.attributes('-topmost', True); r.update(); "
            "r.focus_force(); r.after(7200, r.destroy); r.mainloop()"
        )
        with subprocess.Popen([sys.executable, "-c", child_code]) as child:
            pump_until(lambda: student_window.focus_displayof() is None)
            pump_until(lambda: bool(teacher_panel.history.get_children()), timeout=10)
            event = teacher_panel.history.get_children()[0]
            self.assertEqual(teacher_panel.history.set(event, "Sự kiện"), "Rời cửa sổ")
            pump_until(lambda: child.poll() is not None)
        student_window.focus_force()
        pump_until(lambda: student_panel.warning_overlay is not None
                   and student_panel.warning_overlay.winfo_ismapped())
        card = student_panel.warning_overlay.winfo_children()[0]
        self.assertTrue(any(widget.cget("text") == "Số lần rời cửa sổ: 1"
                            for widget in card.winfo_children() if isinstance(widget, ctk.CTkLabel)))
        button = next(widget for widget in card.winfo_children() if isinstance(widget, ctk.CTkButton))
        self.assertEqual(button.cget("text"), "Tiếp tục làm bài")
        button.invoke()
        self.assertIsNone(student_panel.warning_overlay)
        self.assertEqual(student_panel.answers, {"1": "A"})
        teacher_panel.history.selection_set(event)
        teacher_panel._acknowledge()
        pump_until(lambda: teacher_panel.history.set(event, "Trạng thái") == "Đã xem")
        with patch("client.ui.student.exam_taking.ask_yes_no", return_value=True), patch(
            "client.ui.student.exam_taking.show_info"
        ):
            student_panel._confirm_manual_submit()
            pump_until(lambda: result.called and student_window.state() == "normal")
        self.assertEqual(result.call_args.args[0]["score"], 10)
