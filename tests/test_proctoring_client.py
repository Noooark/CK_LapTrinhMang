import os
import socket
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from client.anti_cheat.focus_monitor import FOCUS_WARNING, FocusMonitor
from client.request_worker import RequestWorker
from client.network import ServerConnection
from common.protocol import receive_message, send_message


def destroy_test_root(root):
    # CTk installs interpreter-wide timers in addition to panel-owned timers.
    for job in root.tk.splitlist(root.tk.call("after", "info")):
        root.after_cancel(job)
    root.destroy()


class FocusTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.root = Mock()
        self.root.focus_displayof.return_value = self.root
        self.root.attributes.return_value = True
        self.report = Mock()
        self.warn = Mock()
        self.monitor = FocusMonitor(self.root, self.report, self.warn, clock=lambda: self.now)

    def sample(self, now, focused):
        self.now = now
        self.root.focus_displayof.return_value = self.root if focused else None
        self.monitor.sample()

    def test_short_loss_and_initialization_do_not_report(self):
        self.sample(0.2, False)
        self.sample(1, True)
        self.sample(2, False)
        self.sample(4.49, True)
        self.report.assert_not_called()
        self.warn.assert_not_called()

    def test_threshold_reports_while_away_once_and_warns_on_return(self):
        self.sample(1, False)
        self.sample(3.5, False)
        self.sample(4, False)
        self.report.assert_called_once_with("FOCUS_LOST", 2.5)
        self.warn.assert_not_called()
        self.sample(5, True)
        self.warn.assert_called_once_with(FOCUS_WARNING)

    def test_dialog_and_internal_focus_are_ignored(self):
        with self.monitor.internal_dialog():
            self.sample(1, False)
            self.sample(10, False)
        self.sample(10.1, False)
        self.root.focus_displayof.return_value = object()
        self.now = 11
        self.monitor.sample()
        self.report.assert_not_called()


class WorkerTests(unittest.TestCase):
    def test_retry_keeps_payload_and_callback_runs_only_on_dispatch_thread(self):
        connection = Mock()
        completed = threading.Event()
        transport_threads = []
        payload = {"event_id": "fixed"}

        def send(*args, **kwargs):
            transport_threads.append(threading.get_ident())
            self.assertIs(kwargs["data"], payload)
            if len(transport_threads) == 1:
                return {"transport_error": True}
            completed.set()
            return {"status": "SUCCESS"}

        connection.send_request.side_effect = send
        worker = RequestWorker(connection, "session")
        self.addCleanup(worker.stop)
        callback = Mock(side_effect=lambda _: self.assertEqual(threading.get_ident(), main_thread))
        main_thread = threading.get_ident()
        worker.request("REPORT_EXAM_EVENT", payload, callback, attempts=2)
        self.assertTrue(completed.wait(3))
        callback.assert_not_called()
        deadline = time.monotonic() + 2
        while not callback.called and time.monotonic() < deadline:
            worker.dispatch()
            time.sleep(0.01)
        callback.assert_called_once_with({"status": "SUCCESS"})
        self.assertEqual(len(set(transport_threads)), 1)
        self.assertNotEqual(transport_threads[0], main_thread)

    def test_partial_response_timeout_closes_connection_and_next_request_reconnects(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(2)
            listener.settimeout(3)
            requests = []

            def serve():
                with listener.accept()[0] as first:
                    first.settimeout(2)
                    requests.append(receive_message(first))
                    first.sendall(b"\x00\x00")
                    with listener.accept()[0] as second:
                        second.settimeout(2)
                        requests.append(receive_message(second))
                        send_message(second, {"status": "SUCCESS"})

            server = threading.Thread(target=serve, daemon=True)
            server.start()
            connection = ServerConnection(*listener.getsockname(), tls_ca="")
            self.addCleanup(connection.disconnect)
            create_connection = socket.create_connection
            with patch("client.network.socket.create_connection",
                       side_effect=lambda address, timeout: create_connection(address, timeout=0.2)):
                response = connection.send_request("EXAM_HEARTBEAT", {"attempt_id": 1}, "session")
                self.assertTrue(response["transport_error"])
                self.assertIsNone(connection.sock)
                response = connection.send_request("EXAM_HEARTBEAT", {"attempt_id": 1}, "session")
            self.assertEqual(response["status"], "SUCCESS")
            server.join(3)
            self.assertEqual(len(requests), 2)
            self.assertEqual(requests[0], requests[1])


@unittest.skipUnless(os.getenv("QUIZ_TEST_DESKTOP") == "1", "requires an interactive Tk desktop")
class DesktopTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows window controls")
    def test_maximized_window_submits_on_confirmed_close(self):
        from client.main import QuizApp
        from client.ui.student.student_dashboard import StudentDashboard

        root = QuizApp()
        self.addCleanup(destroy_test_root, root)
        root.geometry("1050x650+80+50")
        root.update()
        geometry_before = root.winfo_geometry()
        gate = threading.Event()
        self.addCleanup(gate.set)
        calls = []
        fail_submit = True

        def send(command, data, token):
            calls.append((command, data))
            if command == "START_EXAM_ATTEMPT":
                gate.wait(3)
                return {"status": "SUCCESS", "data": {
                    "attempt_id": 19, "remaining_seconds": 40, "submit_grace_seconds": 120,
                    "questions": [
                        {"id": 12, "content": "Câu hỏi ngắn?", "option_a": "Một"},
                        {"id": 13, "content": "Câu hỏi dài. " * 65,
                         "option_a": "Phương án dài. " * 80},
                    ],
                }}
            if command == "SUBMIT_EXAM" and fail_submit:
                return {"status": "ERROR", "message": "Thử lại"}
            return {"status": "SUCCESS", "data": {"score": 10, "correct_count": 1, "total_questions": 1}}

        connection = SimpleNamespace(send_request=send, disconnect=lambda: None)
        root.connection = connection
        with patch.object(StudentDashboard, "_show_panel"):
            dashboard = StudentDashboard(root.container, connection, {}, "session", lambda: None)
        root.current_view = dashboard
        dashboard.grid(row=0, column=0, sticky="nsew")
        dashboard._start_exam_taking({"id": 2})
        panel = dashboard.current_panel
        self.addCleanup(panel.destroy)

        def click_close():
            root.tk.call(root.protocol("WM_DELETE_WINDOW"))

        def pump_until(condition):
            deadline = time.monotonic() + 4
            while not condition() and time.monotonic() < deadline:
                root.update()
                time.sleep(0.015)
            self.assertTrue(condition())

        tick = threading.Event()
        root.after(40, tick.set)
        pump_until(tick.is_set)
        self.assertFalse(gate.is_set())
        self.assertFalse(root.attributes("-fullscreen"))
        gate.set()
        pump_until(lambda: root.state() == "zoomed")
        self.assertFalse(root.attributes("-fullscreen"))
        gap = (panel.option_labels["A"].winfo_rooty()
               - panel.question_text.winfo_rooty() - panel.question_text.winfo_height())
        self.assertLess(gap, 40)
        panel._jump_to_question(1)
        root.update()
        wide_height = panel.option_labels["A"].winfo_height()
        root.state("normal")
        root.update()
        self.assertGreater(panel.option_labels["A"].winfo_height(), wide_height)
        self.assertLess(panel.question_card._parent_canvas.yview()[1], 1)
        root.state("zoomed")
        panel._jump_to_question(0)
        root.update()
        self.assertEqual(panel.question_card._parent_canvas.yview()[0], 0)
        panel.option_var.set("A")
        panel._on_option_selected()
        with patch("client.ui.student.exam_taking.ask_yes_no", return_value=False) as confirm:
            click_close()
            confirm.assert_called_once()
        self.assertEqual(panel.answers, {"12": "A"})
        self.assertEqual([command for command, _ in calls], ["START_EXAM_ATTEMPT"])
        with patch("client.ui.student.exam_taking.ask_yes_no", return_value=True), patch(
            "client.ui.student.exam_taking.show_info"
        ), patch.object(root, "destroy") as close:
            panel._confirm_manual_submit()
            pump_until(lambda: panel.submit_failed)
            self.assertEqual(root.state(), "zoomed")
            self.assertEqual(panel.answers, {"12": "A"})
            fail_submit = False
            click_close()
            pump_until(lambda: close.called and root.winfo_geometry() == geometry_before)
        self.assertEqual(root.state(), "normal")
        self.assertTrue(panel.worker.stopped.is_set())
        self.assertEqual([data["event_type"] for command, data in calls
                          if command == "REPORT_EXAM_EVENT"], ["EXAM_EXIT_REQUESTED"])
        self.assertEqual(calls[-1], ("SUBMIT_EXAM", {
            "exam_id": 2, "attempt_id": 19, "answers": {"12": "A"},
        }))

    @unittest.skipUnless(os.name == "nt", "Windows maximized state")
    def test_exam_preserves_preexisting_maximized_state(self):
        import customtkinter as ctk
        from client.ui.student.exam_window import ExamWindow

        root = ctk.CTk()
        self.addCleanup(destroy_test_root, root)
        root.geometry("800x550+80+50")
        root.update()
        before = root.winfo_geometry()
        root.state("zoomed")
        root.update()
        window = ExamWindow(root)
        window.enter()
        window.restore()
        root.update()
        self.assertFalse(root.attributes("-fullscreen"))
        self.assertEqual(root.state(), "zoomed")
        root.state("normal")
        root.update()
        self.assertEqual(root.winfo_geometry(), before)
