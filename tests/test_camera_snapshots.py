import base64
from io import BytesIO
import os
import socket
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from PIL import Image

from common.snapshots import MAX_BASE64_CHARS
from server.client_handler import ClientHandler
from server.service.snapshot_service import SnapshotService


def jpeg():
    with BytesIO() as output:
        Image.new("RGB", (48, 32), "#336699").save(output, "JPEG")
        return base64.b64encode(output.getvalue()).decode("ascii")


class SnapshotValidationTests(unittest.TestCase):
    def test_invalid_jpeg_limits_and_storage_key(self):
        self.assertIsNotNone(SnapshotService._decode(jpeg()))
        self.assertIsNone(SnapshotService._decode("A" * (MAX_BASE64_CHARS + 1)))
        self.assertIsNone(SnapshotService._decode(base64.b64encode(b"fake\xff\xd9").decode("ascii")))
        for key in ("../../outside", "C:/somewhere", "a.jpg"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                SnapshotService._path(None, key)

    def test_server_blocks_snapshot_commands_on_plain_socket(self):
        auth = Mock()
        auth.validate_token.return_value = {"id": 1, "role": "ADMIN"}
        snapshots = Mock()
        with socket.socket() as server:
            handler = ClientHandler(server, ("127.0.0.1", 5000), auth, snapshots=snapshots)
            for command in ("GET_EXAM_SNAPSHOT", "UPLOAD_EXAM_SNAPSHOT"):
                response = handler._handle_request({"command": command, "token": "session", "data": {}})
                self.assertEqual(response["status"], "ERROR")
                self.assertIn("TLS", response["message"])
            self.assertEqual(snapshots.mock_calls, [])


@unittest.skipUnless(os.getenv("QUIZ_TEST_DESKTOP") == "1", "requires an interactive Tk desktop")
class SnapshotViewerTests(unittest.TestCase):
    def test_eye_fetches_only_available_snapshot_and_displays_it(self):
        import customtkinter as ctk
        from client.ui.teacher.monitoring_panel import MonitoringPanel
        from test_proctoring_client import destroy_test_root

        root = ctk.CTk()
        self.addCleanup(destroy_test_root, root)
        root.geometry("1100x700")
        connection = SimpleNamespace(send_request=lambda *a, **k: {"status": "SUCCESS", "data": []})
        panel = MonitoringPanel(root, connection, "session")
        panel.worker.stop()
        panel.pack(fill="both", expand=True)
        self.addCleanup(panel.destroy)
        root.update()
        row = {"id": 1, "created_at": "2026-11-07", "username": "student_a",
               "event_type": "CAMERA_MULTIPLE_FACES", "face_count": 2,
               "duration_seconds": 3, "reviewed": False}
        panel._on_history(panel.generation, {"status": "SUCCESS", "data": {
            "next_before_id": None, "events": [row, {**row, "id": 2, "has_snapshot": True}],
        }})
        root.update()
        column = panel.history["columns"][-1]
        self.assertEqual(panel.history.set("1", column), "Không có ảnh")
        self.assertEqual(panel.history.set("2", column), "👁")

        def click(row_id):
            x, y, width, height = panel.history.bbox(row_id, column)
            panel._open_history_status(SimpleNamespace(x=x + width // 2, y=y + height // 2))

        with patch.object(panel.worker, "request") as request:
            click("1")
            request.assert_not_called()
            click("2")
            command, data, callback = request.call_args.args
            self.assertEqual((command, data), ("GET_EXAM_SNAPSHOT", {"event_id": 2}))
            callback({"status": "SUCCESS", "data": {
                **row, "image_base64": jpeg(), "title": "Demo", "captured_at": row["created_at"],
            }})
        labels = [widget for widget in panel.snapshot_window.winfo_children() if isinstance(widget, ctk.CTkLabel)]
        image = labels[-1].cget("image")
        self.assertEqual(image.cget("size"), (48, 32))
        panel._close_snapshot()
        self.assertIsNone(panel.snapshot_window)
