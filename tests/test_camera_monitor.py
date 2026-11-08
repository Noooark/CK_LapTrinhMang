import os
from threading import Event
from time import monotonic, sleep
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from client.anti_cheat.camera_monitor import CameraEpisodes, CameraMonitor, CameraSample, DISCONNECTED


class EpisodeTests(unittest.TestCase):
    def test_phone_allows_a_brief_missed_frame(self):
        track = CameraEpisodes({})
        for visible, timestamp in [(True, 1), (False, 1.5), (True, 2), (False, 2.5)]:
            self.assertIsNone(track.sample_phone(visible, timestamp))
        self.assertEqual(track.sample_phone(True, 3), ("CAMERA_PHONE_DETECTED", 2, None))

    def test_phone_requires_distinct_frames_and_rearms_after_clear(self):
        track = CameraEpisodes({})
        self.assertIsNone(track.sample_phone(True, 1))
        self.assertIsNone(track.sample_phone(True, 1))
        self.assertIsNone(track.sample_phone(True, 2))
        self.assertEqual(track.sample_phone(True, 3), ("CAMERA_PHONE_DETECTED", 2, None))
        self.assertIsNone(track.sample_phone(True, 4))
        self.assertIsNone(track.sample_phone(False, 5))
        self.assertIsNone(track.sample_phone(True, 5.5))
        self.assertIsNone(track.sample_phone(True, 6.5))
        self.assertIsNone(track.sample_phone(False, 7))
        self.assertIsNone(track.sample_phone(False, 8))
        self.assertIsNone(track.sample_phone(True, 9))
        self.assertIsNone(track.sample_phone(None, 10))
        self.assertIsNone(track.sample_phone(True, 11))
        self.assertIsNone(track.sample_phone(True, 12))
        self.assertEqual(track.sample_phone(True, 13), ("CAMERA_PHONE_DETECTED", 2, None))

    def test_model_scores_only_phone_class(self):
        import numpy as np
        from client.anti_cheat.phone_detector import PhoneDetector

        cv = Mock()
        cv.resize.side_effect = lambda frame, size, **kwargs: np.zeros((size[1], size[0], 3), dtype=np.uint8)
        cv.flip.side_effect = lambda frame, axis: frame[:, ::-1]
        cv.rotate.side_effect = lambda frame, rotation: np.rot90(frame)
        cv.HoughLinesP.return_value = None
        network = cv.dnn.readNetFromONNX.return_value
        output = np.zeros((1, 2, 85), dtype=np.float32)
        network.forward.return_value = output
        output[0, 0, [4, 5, 72]] = [0.9, 0.95, 0.8]
        self.assertFalse(PhoneDetector(cv).sees_phone(np.zeros((480, 640, 3), dtype=np.uint8)))
        output[0, 1, [4, 72]] = [0.9, 0.8]
        self.assertTrue(PhoneDetector(cv).sees_phone(np.zeros((480, 640, 3), dtype=np.uint8)))
        output[0, 1, [4, 72]] = [0.8, 0.5]
        self.assertTrue(PhoneDetector(cv).sees_phone(np.zeros((480, 640, 3), dtype=np.uint8)))

        standard = output.copy()
        standard[0, 1, 72] = 0
        close_view = standard.copy()
        close_view[0, 1, [4, 72]] = [0.8, 0.41]
        network.forward.side_effect = [standard, close_view]
        self.assertTrue(PhoneDetector(cv).sees_phone(np.zeros((480, 640, 3), dtype=np.uint8)))
        self.assertEqual(max(cv.resize.call_args.args[1]), 320)
        network.forward.side_effect = [standard, standard, close_view]
        cv.flip.reset_mock()
        self.assertTrue(PhoneDetector(cv).sees_phone(np.zeros((480, 640, 3), dtype=np.uint8)))
        cv.flip.assert_called_once()

    def test_deskew_uses_two_agreeing_edges(self):
        import numpy as np
        from client.anti_cheat.phone_detector import PhoneDetector

        cv = Mock()
        cv.HoughLinesP.return_value = np.array([[[10, 100, 90, 20]], [[20, 80, 60, 40]]])
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        detector = PhoneDetector(cv)
        self.assertIs(detector._deskew(frame), cv.warpAffine.return_value)
        self.assertAlmostEqual(cv.getRotationMatrix2D.call_args.args[1], -45)

        cv.HoughLinesP.return_value = np.array([[[10, 100, 90, 20]], [[20, 80, 90, 80]]])
        self.assertIs(detector._deskew(frame), frame)

    def test_no_face_threshold_dedup_and_next_episode(self):
        track = CameraEpisodes({})
        self.assertIsNone(track.sample(None, 1, 0))
        self.assertIsNone(track.sample("CAMERA_NO_FACE", 0, 1))
        self.assertIsNone(track.sample("CAMERA_NO_FACE", 0, 10.99))
        self.assertEqual(track.sample("CAMERA_NO_FACE", 0, 11), ("CAMERA_NO_FACE", 10, None))
        self.assertIsNone(track.sample("CAMERA_NO_FACE", 0, 14))
        self.assertIsNone(track.sample(None, 1, 15))
        self.assertEqual(track.sample(None, 1, 16), ("CAMERA_RECOVERED", None, None))
        self.assertIsNone(track.sample("CAMERA_NO_FACE", 0, 17))
        self.assertEqual(track.sample("CAMERA_NO_FACE", 0, 27), ("CAMERA_NO_FACE", 10, None))

    def test_multiple_faces_signal_loss_and_obstruction(self):
        for kind, seconds, faces in [
            ("CAMERA_MULTIPLE_FACES", 3, 2), (DISCONNECTED, 5, None),
            ("CAMERA_OBSTRUCTED", 10, None),
        ]:
            with self.subTest(kind=kind):
                track = CameraEpisodes({})
                self.assertIsNone(track.sample(kind, faces, 0))
                self.assertIsNone(track.sample(kind, faces, seconds - .01))
                self.assertEqual(track.sample(kind, faces, seconds), (kind, seconds, faces))
                self.assertIsNone(track.sample(kind, faces, seconds + 1))
                self.assertIsNone(track.sample(None, 1, seconds + 2))
                self.assertEqual(track.sample(None, 1, seconds + 3), ("CAMERA_RECOVERED", None, None))

    def test_configured_threshold_is_used(self):
        track = CameraEpisodes({"no_face_threshold_seconds": 3})
        self.assertIsNone(track.sample("CAMERA_NO_FACE", 0, 0))
        self.assertEqual(track.sample("CAMERA_NO_FACE", 0, 3), ("CAMERA_NO_FACE", 3, None))


class WorkerTests(unittest.TestCase):
    def wait_for(self, predicate):
        limit = monotonic() + 3
        while not predicate() and monotonic() < limit:
            sleep(.01)
        self.assertTrue(predicate())

    def start(self, cv):
        detector = Mock()
        detector.observe.return_value = (None, 1)
        camera = CameraMonitor(cv=cv, detector_factory=lambda _: detector, phone_model=None)
        self.addCleanup(camera.finished.wait, 3)
        self.addCleanup(camera.stop)
        return camera

    def test_open_failure_retry_preview_transfer_and_release(self):
        unavailable = Mock()
        unavailable.isOpened.return_value = False
        working = Mock()
        working.isOpened.return_value = True
        working.read.return_value = True, SimpleNamespace(shape=(240, 320, 3))
        cv = Mock()
        cv.VideoCapture.side_effect = [unavailable, working]
        camera = self.start(cv)
        self.wait_for(lambda: unavailable.release.called)
        self.assertEqual(camera.snapshot().condition, DISCONNECTED)
        camera.retry(1)
        self.wait_for(lambda: camera.snapshot().faces == 1)
        self.assertIsNotNone(camera.snapshot().preview)
        camera.begin_exam()
        self.wait_for(lambda: camera.snapshot().preview is None)
        camera.stop()
        self.assertTrue(camera.finished.wait(3))
        working.release.assert_called_once()
        self.assertEqual(cv.VideoCapture.call_count, 2)

    def test_read_failure_and_stale_driver_are_disconnected(self):
        capture = Mock()
        capture.isOpened.return_value = True
        capture.read.return_value = False, None
        cv = Mock()
        cv.VideoCapture.return_value = capture
        camera = self.start(cv)
        self.wait_for(lambda: capture.release.called)
        self.assertEqual(camera.snapshot().condition, DISCONNECTED)
        camera.latest = CameraSample(monotonic() - 3, None, 1)
        self.assertEqual(camera.snapshot().condition, DISCONNECTED)

    def test_slow_native_read_does_not_delay_stop_request(self):
        started, resume = Event(), Event()
        self.addCleanup(resume.set)
        capture = Mock()
        capture.isOpened.return_value = True

        def read():
            started.set()
            resume.wait(3)
            return False, None

        capture.read.side_effect = read
        cv = Mock()
        cv.VideoCapture.return_value = capture
        camera = self.start(cv)
        self.assertTrue(started.wait(3))
        camera.stop()
        self.assertFalse(camera.finished.is_set())
        resume.set()
        self.assertTrue(camera.finished.wait(3))
        capture.release.assert_called_once()


@unittest.skipUnless(os.getenv("QUIZ_TEST_DESKTOP") == "1", "requires an interactive Tk desktop")
class CameraConsentTests(unittest.TestCase):
    def test_decline_never_opens_device_and_preview_can_be_transferred(self):
        import customtkinter as ctk
        from client.ui.student.camera_check_dialog import CameraCheckDialog
        from test_proctoring_client import destroy_test_root

        root = ctk.CTk()
        self.addCleanup(destroy_test_root, root)
        root.update()
        on_ready = Mock()
        with patch("client.ui.student.camera_check_dialog.CameraMonitor") as factory:
            dialog = CameraCheckDialog(root, on_ready, retention_days=7)
            self.assertEqual(dialog.start.cget("state"), "disabled")
            self.assertFalse(any(isinstance(widget, ctk.CTkCheckBox) for widget in dialog.winfo_children()))
            dialog.destroy()
            factory.assert_not_called()
            on_ready.assert_not_called()

            factory.return_value.snapshot.return_value = CameraSample(monotonic(), None, 1)
            dialog = CameraCheckDialog(root, on_ready, retention_days=7)
            dialog._enable()
            self.assertEqual(dialog.start.cget("state"), "normal")
            dialog._start()
            on_ready.assert_called_once_with(factory.return_value)
            factory.return_value.begin_exam.assert_called_once()
            self.assertIs(factory.return_value.snapshot_consent, True)
            factory.return_value.stop.assert_not_called()

    def test_exam_warns_and_releases_camera_after_submission(self):
        import customtkinter as ctk
        import numpy as np
        from client.ui.student.exam_taking import ExamTakingPanel
        from test_proctoring_client import destroy_test_root

        root = ctk.CTk()
        self.addCleanup(destroy_test_root, root)
        root.geometry("1100x700")
        camera = Mock()
        camera.snapshot_consent = True
        camera.snapshot.return_value = CameraSample(monotonic(), None, 1)
        calls = []

        def send(command, data, token):
            calls.append((command, data))
            if command == "START_EXAM_ATTEMPT":
                return {"status": "SUCCESS", "data": {
                    "attempt_id": 20, "remaining_seconds": 45, "submit_grace_seconds": 120,
                    "camera_required": True, "snapshot_consent": True,
                    "camera_thresholds": {"no_face_threshold_seconds": 1},
                    "questions": [{"id": 12, "option_a": "Một"}],
                }}
            return {"status": "SUCCESS", "data": {"score": 10, "correct_count": 1, "total_questions": 1}}

        result = Mock()
        panel = ExamTakingPanel(root, SimpleNamespace(send_request=send), "session", {"id": 2},
                                result, camera=camera)
        panel.pack(fill="both", expand=True)
        self.addCleanup(panel.destroy)

        def pump_until(predicate):
            limit = monotonic() + 4
            while not predicate() and monotonic() < limit:
                root.update()
                sleep(.02)
            self.assertTrue(predicate())

        pump_until(lambda: panel.deadline is not None)
        original_deadline = panel.deadline
        panel.opt_buttons["A"].invoke()
        camera.snapshot.return_value = CameraSample(monotonic(), "CAMERA_NO_FACE", 0,
                                                    evidence=np.zeros((40, 60, 3), dtype=np.uint8))
        pump_until(lambda: any(command == "REPORT_EXAM_EVENT" for command, _ in calls))
        pump_until(lambda: any(command == "UPLOAD_EXAM_SNAPSHOT" for command, _ in calls))
        alert = next(data for command, data in calls if command == "REPORT_EXAM_EVENT")
        upload = next(data for command, data in calls if command == "UPLOAD_EXAM_SNAPSHOT")
        self.assertEqual(upload["event_id"], alert["event_id"])
        self.assertIn("Không thấy khuôn mặt", panel.camera_label.cget("text"))
        card = panel.warning_overlay.winfo_children()[0]
        self.assertEqual(card.winfo_children()[0].cget("text"), "Không thấy khuôn mặt")
        panel._show_focus_warning("Đã rời cửa sổ.")
        self.assertEqual(len(panel.warning_queue), 1)
        panel._continue_after_warning()
        card = panel.warning_overlay.winfo_children()[0]
        self.assertEqual(card.winfo_children()[0].cget("text"), "Bạn đã rời cửa sổ thi")
        panel._continue_after_warning()
        self.assertIsNone(panel.warning_overlay)
        self.assertEqual(panel.answers, {"12": "A"})
        self.assertEqual(panel.deadline, original_deadline)
        camera.snapshot.return_value = CameraSample(monotonic(), None, 1)
        pump_until(lambda: any(data.get("event_type") == "CAMERA_RECOVERED" for _, data in calls))
        frame = np.zeros((40, 60, 3), dtype=np.uint8)
        now = monotonic()
        for offset in (2.2, 1.1, 0):
            camera.snapshot.return_value = CameraSample(now - offset, None, 1, evidence=frame,
                                                        phone_detected=True)
            panel._sample_camera(now)
        card = panel.warning_overlay.winfo_children()[0]
        self.assertEqual(card.winfo_children()[0].cget("text"), "Phát hiện điện thoại trong khung hình")
        phone_event = panel.events[-1]["event_id"]
        pump_until(lambda: any(command == "UPLOAD_EXAM_SNAPSHOT" and data["event_id"] == phone_event
                               for command, data in calls))
        panel._continue_after_warning()
        with patch("client.ui.student.exam_taking.show_info"):
            panel._request_submit()
            pump_until(lambda: result.called)
        camera.stop.assert_called_once()
        self.assertEqual(sum(command == "UPLOAD_EXAM_SNAPSHOT" for command, _ in calls), 2)
        self.assertEqual(calls[-1][1]["answers"], {"12": "A"})
