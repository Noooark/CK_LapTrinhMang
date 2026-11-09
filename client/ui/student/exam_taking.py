from collections import deque
from contextlib import nullcontext
import json
from math import ceil
from pathlib import Path
from tkinter import filedialog
from time import monotonic
from uuid import uuid4
from typing import Dict, Any, Optional, List, Callable
import customtkinter as ctk

from common.camera import CAMERA_PHONE_DETECTED
from common.snapshots import SNAPSHOT_EVENTS
from client.anti_cheat.camera_snapshot import encode_snapshot
from client.anti_cheat.camera_monitor import CameraEpisodes, CameraMonitor, DISCONNECTED
from client.anti_cheat.focus_monitor import FocusMonitor
from client.ui.student.exam_window import ExamWindow
from client.ui.student.exam_notice import exam_notice
from client.network import ServerConnection
from client.request_worker import RequestWorker
from client.ui.utils import (
    PRIMARY_COLOR, PRIMARY_HOVER, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR,
    show_error, show_info, ask_yes_no
)


CAMERA_WARNINGS = {
    CAMERA_PHONE_DETECTED: ("Phát hiện điện thoại trong khung hình",
                            "Vui lòng cất điện thoại. Giáo viên có thể xem lại cảnh báo này."),
    "CAMERA_NO_FACE": ("Không thấy khuôn mặt", "Vui lòng quay lại vị trí làm bài và nhìn về phía camera."),
    "CAMERA_MULTIPLE_FACES": ("Phát hiện nhiều khuôn mặt", "Vui lòng kiểm tra để chỉ có bạn trong khung hình."),
    DISCONNECTED: ("Camera mất tín hiệu", "Vui lòng kiểm tra webcam hoặc bấm Kết nối lại sau khi đóng cảnh báo."),
    "CAMERA_OBSTRUCTED": ("Hình ảnh khó quan sát", "Vui lòng kiểm tra ánh sáng và bảo đảm camera không bị che."),
}
MAX_PENDING_SNAPSHOTS = 4


class ExamTakingPanel(ctk.CTkFrame):
    """
    Core exam taking interface for students:
    - Real-time countdown timer with auto-submit on timeout
    - Question navigation grid with answered/unanswered/current status
    - Local answer storage and batch submission to server
    - Thread-safe network operations
    """

    def __init__(
        self,
        master,
        connection: ServerConnection,
        token: str,
        exam_data: Dict[str, Any],
        on_submitted: Callable[[Dict[str, Any]], None],
        camera=None,
        **kwargs
    ):
        super().__init__(master, **kwargs)
        self.connection = connection
        self.token = token
        self.exam_data = exam_data
        self.on_submitted = on_submitted
        self.camera = camera
        self.camera_episodes = None
        self.snapshot_consent = False
        self.pending_snapshots = {}
        self.snapshot_uploads = 0

        # Exam state
        self.questions: List[Dict[str, Any]] = []
        self.current_idx: int = 0
        self.answers: Dict[str, str] = {}  # str(qid) -> "A"|"B"|"C"|"D"
        self.nav_buttons: List[ctk.CTkButton] = []
        self.is_submitting: bool = False
        self.poll_job = None
        self.deadline = None
        self.submit_grace = 0
        self.monitor = None
        self.focus_loss_count = 0
        self.warning_overlay = None
        self.warning_queue = deque()
        self.exam_window = None
        self.dialog_open = False
        self.close_after_submit = False
        self.submit_failed = False
        self.submit_requested = False
        self.timed_out = False
        self.next_heartbeat = 0
        self.heartbeat_pending = False
        self.events = deque()
        self.event_pending = False
        self.next_event_retry = 0

        # Calculate duration in seconds
        duration_mins = int(self.exam_data.get("duration_minutes", 30))
        self.time_left_seconds = duration_mins * 60

        self._build_ui()
        self.submit_btn.configure(state="disabled")
        self.worker = RequestWorker(connection, token)
        payload = {"exam_id": exam_data["id"]}
        if camera is not None:
            payload["camera_ready"] = True
            payload["snapshot_consent"] = getattr(camera, "snapshot_consent", False) is True
        self.worker.request("START_EXAM_ATTEMPT", payload, self._on_attempt_started, attempts=2)
        self.poll_job = self.after(100, self._poll)

    def _build_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ==================== 1. TOP HEADER BAR ====================
        top_bar = ctk.CTkFrame(self, height=65, corner_radius=0, fg_color=("gray85", "#1c1e24"))
        top_bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        top_bar.grid_columnconfigure(1, weight=1)

        # Left: Exam info
        info_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        info_frame.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        title_text = self.exam_data.get("title", "Bài thi trắc nghiệm")
        subj_text = self.exam_data.get("subject_name", "")
        header_text = f"📝 {title_text}" + (f" - {subj_text}" if subj_text else "")

        ctk.CTkLabel(
            info_frame,
            text=header_text,
            font=("Helvetica", 16, "bold"),
            text_color=("gray10", "#ffffff")
        ).pack(anchor="w")

        self.progress_counter_lbl = ctk.CTkLabel(
            info_frame,
            text="Đang tải câu hỏi...",
            font=("Helvetica", 12),
            text_color="gray60"
        )
        self.progress_counter_lbl.pack(anchor="w")

        self.monitor_label = ctk.CTkLabel(info_frame, text="Đang mở lượt thi…", text_color=WARNING_COLOR)
        self.monitor_label.pack(anchor="w")
        if self.camera is not None:
            camera_bar = ctk.CTkFrame(info_frame, fg_color="transparent")
            camera_bar.pack(anchor="w")
            self.camera_label = ctk.CTkLabel(camera_bar, text="● Đang chờ mở lượt thi")
            self.camera_label.pack(side="left", padx=(0, 8))
            self.camera_retry = ctk.CTkButton(camera_bar, text="Kết nối lại", width=84,
                                              command=self._retry_camera)
        self.warning_label = ctk.CTkLabel(self, text="", text_color=WARNING_COLOR, wraplength=760)
        self.warning_label.grid(row=2, column=0, columnspan=2, padx=20, sticky="w")

        # Right: Timer and Submit
        action_bar = ctk.CTkFrame(top_bar, fg_color="transparent")
        action_bar.grid(row=0, column=2, padx=20, pady=10, sticky="e")

        self.timer_label = ctk.CTkLabel(
            action_bar,
            text=self._format_time(self.time_left_seconds),
            font=("Helvetica", 20, "bold"),
            text_color=PRIMARY_COLOR
        )
        self.timer_label.pack(side="left", padx=(0, 20))

        self.submit_btn = ctk.CTkButton(
            action_bar,
            text="📤 Nộp bài",
            font=("Helvetica", 14, "bold"),
            fg_color=SUCCESS_COLOR,
            hover_color="#218838",
            width=120,
            height=38,
            command=self._confirm_manual_submit
        )
        self.submit_btn.pack(side="right")

        # ==================== 2. MAIN QUESTION AREA (LEFT) ====================
        self.question_container = ctk.CTkFrame(self, fg_color="transparent")
        self.question_container.grid(row=1, column=0, padx=(20, 10), pady=15, sticky="nsew")
        self.question_container.grid_rowconfigure(1, weight=1)
        self.question_container.grid_columnconfigure(0, weight=1)

        # Question header card
        q_meta_frame = ctk.CTkFrame(self.question_container, fg_color="transparent")
        q_meta_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        q_meta_frame.grid_columnconfigure(0, weight=1)

        self.q_index_label = ctk.CTkLabel(
            q_meta_frame,
            text="Câu 1",
            font=("Helvetica", 18, "bold"),
            text_color=PRIMARY_COLOR
        )
        self.q_index_label.grid(row=0, column=0, sticky="w")

        self.diff_badge = ctk.CTkLabel(
            q_meta_frame,
            text="Độ khó: -",
            font=("Helvetica", 11),
            text_color="gray60"
        )
        self.diff_badge.grid(row=0, column=1, sticky="e")

        # Question Card Box
        self.question_card = ctk.CTkScrollableFrame(
            self.question_container, width=1, height=1, corner_radius=12,
            fg_color=("gray90", "#242830"),
        )
        self.question_card.grid(row=1, column=0, sticky="nsew")
        self.question_card.grid_columnconfigure(1, weight=1)

        # Question text display
        self.question_text = ctk.CTkLabel(
            self.question_card, text="Đang tải dữ liệu câu hỏi...",
            font=("Helvetica", 14), justify="left", anchor="w", wraplength=1,
        )
        self.question_text.grid(row=0, column=0, columnspan=2, padx=16, pady=(14, 8), sticky="ew")

        # Separator line
        ctk.CTkFrame(self.question_card, height=1, fg_color=("gray80", "#333842")).grid(
            row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 4),
        )

        self.option_var = ctk.StringVar(value="")

        self.opt_buttons = {}
        self.option_labels = {}
        for row, key in enumerate("ABCD", start=2):
            rb = ctk.CTkRadioButton(
                self.question_card,
                text="",
                width=24,
                value=key,
                variable=self.option_var,
                command=self._on_option_selected,
                radiobutton_width=20,
                radiobutton_height=20
            )
            rb.grid(row=row, column=0, padx=(16, 4), pady=4, sticky="nw")
            self.opt_buttons[key] = rb
            label = ctk.CTkLabel(
                self.question_card, text=f"{key}.", font=("Helvetica", 13),
                justify="left", anchor="w", wraplength=1,
            )
            label.grid(row=row, column=1, padx=(0, 16), pady=4, sticky="ew")
            label.bind("<Button-1>", rb.invoke)
            self.option_labels[key] = label

        self.question_card.bind("<Configure>", self._wrap_question_text, add="+")

        # Clear answer button
        self.clear_ans_btn = ctk.CTkButton(
            self.question_card,
            text="❌ Bỏ chọn câu trả lời",
            width=160,
            height=28,
            fg_color="transparent",
            text_color="gray60",
            hover_color=("gray85", "#2a2d36"),
            font=("Helvetica", 11),
            command=self._clear_current_answer
        )
        self.clear_ans_btn.grid(row=6, column=0, columnspan=2, padx=16, pady=(4, 12), sticky="w")

        # Bottom Question Navigation buttons
        nav_frame = ctk.CTkFrame(self.question_container, fg_color="transparent")
        nav_frame.grid(row=2, column=0, sticky="ew", pady=(15, 0))
        nav_frame.grid_columnconfigure(1, weight=1)

        self.prev_btn = ctk.CTkButton(
            nav_frame,
            text="⬅️ Câu trước",
            width=120,
            height=38,
            fg_color="gray40",
            hover_color="gray30",
            command=self._prev_question
        )
        self.prev_btn.grid(row=0, column=0, sticky="w")

        self.next_btn = ctk.CTkButton(
            nav_frame,
            text="Câu tiếp ➡️",
            width=120,
            height=38,
            fg_color=PRIMARY_COLOR,
            hover_color=PRIMARY_HOVER,
            command=self._next_question
        )
        self.next_btn.grid(row=0, column=2, sticky="e")

        # ==================== 3. SIDEBAR NAVIGATION (RIGHT) ====================
        sidebar = ctk.CTkFrame(self, width=280, corner_radius=12, fg_color=("gray90", "#1c1e24"))
        sidebar.grid(row=1, column=1, padx=(10, 20), pady=15, sticky="nsew")
        sidebar.grid_rowconfigure(2, weight=1)
        sidebar.grid_columnconfigure(0, weight=1)

        # Title
        ctk.CTkLabel(
            sidebar,
            text="📋 Danh sách câu hỏi",
            font=("Helvetica", 15, "bold")
        ).grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")

        # Summary counter
        self.answered_summary_label = ctk.CTkLabel(
            sidebar,
            text="Đã làm: 0 / 0 câu",
            font=("Helvetica", 12),
            text_color=SUCCESS_COLOR
        )
        self.answered_summary_label.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="w")

        # Grid of Question Number Buttons
        self.grid_scroll = ctk.CTkScrollableFrame(sidebar, width=240, height=1, fg_color="transparent")
        self.grid_scroll.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")
        for col in range(5):
            self.grid_scroll.grid_columnconfigure(col, weight=1)

        # Legend at bottom of sidebar
        legend_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        legend_frame.grid(row=3, column=0, padx=15, pady=(10, 15), sticky="ew")

        legend_text = "🔵 Đã làm   ⚪ Chưa làm   🟡 Đang xem"
        ctk.CTkLabel(legend_frame, text=legend_text, font=("Helvetica", 11), text_color="gray60").pack()

    # ==================== HELPERS & TIMER ====================

    def _wrap_question_text(self, event):
        width = self._reverse_widget_scaling(event.width)
        self.question_text.configure(wraplength=max(1, width - 32))
        for label in self.option_labels.values():
            label.configure(wraplength=max(1, width - 60))

    def _format_time(self, seconds: int) -> str:
        mins = max(0, seconds) // 60
        secs = max(0, seconds) % 60
        return f"⏱️ {mins:02d}:{secs:02d}"

    def _poll(self):
        self.poll_job = None
        self.worker.dispatch()
        if self.worker.stopped.is_set():
            return
        if self.deadline is not None:
            now = monotonic()
            self.time_left_seconds = max(0, ceil(self.deadline - now))
            self.timer_label.configure(
                text=self._format_time(self.time_left_seconds),
                text_color=DANGER_COLOR if self.time_left_seconds <= 120 else PRIMARY_COLOR,
            )
            if self.monitor and now < self.deadline and not self.submit_requested and not self.is_submitting:
                self.monitor.sample()
            if self.camera is not None and now >= self.deadline:
                self._stop_camera()
                self.camera_label.configure(text="● Đã dừng camera")
                self.camera_retry.pack_forget()
            if self.camera is not None and not self.is_submitting and not self.submit_requested:
                self._sample_camera(now)
            if now < self.deadline and not self.is_submitting and not self.submit_requested:
                self._show_next_warning()
            for event_id, (queued_at, _) in list(self.pending_snapshots.items()):
                if now - queued_at > 30:
                    del self.pending_snapshots[event_id]
            if now >= self.deadline and not self.timed_out and not self.dialog_open:
                self.timed_out = True
                self.monitor = None
                self._clear_warnings()
                self.monitor_label.configure(text="Hết giờ làm bài")
                if not self.is_submitting and not self.submit_requested:
                    self._request_submit()
            self._schedule_requests(now)
        self.poll_job = self.after(100, self._poll)

    def _on_attempt_started(self, response):
        if response["status"] != "SUCCESS":
            self._stop_camera()
            show_error("Không thể mở lượt thi", response["message"], parent=self)
            self.on_submitted({"status": "ABORTED"})
            return

        data = response["data"]
        if self.camera is not None:
            if data.get("camera_required"):
                self.camera_episodes = CameraEpisodes(data.get("camera_thresholds", {}))
                self.snapshot_consent = (data.get("snapshot_consent") is True
                                         and getattr(self.camera, "snapshot_consent", False) is True)
                self.camera.evidence_enabled = self.snapshot_consent
                if self.snapshot_consent:
                    self.camera_label.master.pack_configure(pady=(0, 2))
                    self.snapshot_notice = ctk.CTkLabel(
                        self.camera_label.master.master, text="Có thể lưu ảnh khi phát sinh cảnh báo",
                    )
                    self.snapshot_notice.pack(anchor="w")
            else:
                self._stop_camera()
                self.camera_label.master.pack_forget()
        self.attempt_id = data["attempt_id"]
        self.questions = data["questions"]
        self.deadline = monotonic() + data["remaining_seconds"]
        self.submit_grace = data["submit_grace_seconds"]
        self.next_heartbeat = monotonic() + 10
        self._build_nav_buttons()
        self._display_current_question()
        self.submit_btn.configure(state="normal")
        root = self.winfo_toplevel()
        self.exam_window = ExamWindow(root)
        self.exam_window.enter()
        self.monitor = FocusMonitor(root, self._record_event, self._show_focus_warning)
        self.monitor_label.configure(text="Đang được giám sát")

    def _sample_camera(self, now):
        sample = self.camera.snapshot()
        events = (self.camera_episodes.sample(sample.condition, sample.faces, now),
                  self.camera_episodes.sample_phone(sample.phone_detected, sample.timestamp))
        for event in events:
            if event is None:
                continue
            event_id = self._record_event(*event)
            if event[0] in CAMERA_WARNINGS:
                title, message = CAMERA_WARNINGS[event[0]]
                self._queue_warning(title, message)
            if (self.snapshot_consent
                    and len(self.pending_snapshots) + self.snapshot_uploads < MAX_PENDING_SNAPSHOTS
                    and event[0] in SNAPSHOT_EVENTS and sample.evidence is not None
                    and 0 <= monotonic() - sample.timestamp <= 2):
                self.pending_snapshots[event_id] = (now, sample.evidence)
        observed = DISCONNECTED if sample.condition == DISCONNECTED else self.camera_episodes.alert
        status = CAMERA_WARNINGS[observed][0] if observed else "Đang giám sát"
        text = f"● Camera: {status}"
        if sample.phone_detected:
            text += " · Đang thấy điện thoại"
        if self.camera_label.cget("text") != text:
            self.camera_label.configure(text=text)
        if sample.condition == DISCONNECTED:
            if not self.camera_retry.winfo_manager():
                self.camera_retry.pack(side="left", padx=6)
        elif self.camera_retry.winfo_manager():
            self.camera_retry.pack_forget()

    def _retry_camera(self):
        if self.camera is None:
            return
        if self.camera.finished.is_set():
            self.camera = CameraMonitor(self.camera.index)
            self.camera.begin_exam()
            self.camera.evidence_enabled = self.snapshot_consent
        else:
            self.camera.retry(self.camera.index)

    def _stop_camera(self):
        if self.camera is not None:
            self.camera.stop()
            self.camera = None

    def _record_event(self, event_type, duration=None, face_count=None):
        if event_type == "FOCUS_LOST":
            self.focus_loss_count += 1
        payload = {"attempt_id": self.attempt_id, "event_type": event_type, "event_id": str(uuid4())}
        if duration is not None:
            payload["duration_seconds"] = round(duration, 3)
        if face_count is not None:
            payload["face_count"] = face_count
        self.events.append(payload)
        return payload["event_id"]

    def _show_banner(self, message):
        self.warning_label.configure(text=message)

    def _show_focus_warning(self, message):
        self._queue_warning("Bạn đã rời cửa sổ thi", message,
                            f"Số lần rời cửa sổ: {self.focus_loss_count}")

    def _queue_warning(self, title, message, detail=None):
        self.warning_queue.append((title, message, detail))
        self._show_next_warning()

    def _show_next_warning(self):
        if self.warning_overlay is not None or not self.warning_queue or self.dialog_open:
            return
        title, message, detail = self.warning_queue.popleft()
        self.warning_overlay, card = exam_notice(self, title, message, WARNING_COLOR)
        if detail:
            ctk.CTkLabel(card, text=detail, font=("Helvetica", 16, "bold")).pack(padx=24)
        ctk.CTkButton(card, text="Tiếp tục làm bài", command=self._continue_after_warning).pack(
            padx=24, pady=(8, 20),
        )

    def _continue_after_warning(self):
        self.warning_overlay.destroy()
        self.warning_overlay = None
        self._show_next_warning()

    def _clear_warnings(self):
        self.warning_queue.clear()
        if self.warning_overlay is not None:
            self.warning_overlay.destroy()
            self.warning_overlay = None

    def _schedule_requests(self, now):
        within_grace = now < self.deadline + self.submit_grace
        if within_grace and not self.is_submitting and not self.heartbeat_pending and now >= self.next_heartbeat:
            self.heartbeat_pending = True
            self.next_heartbeat = now + 10
            self.worker.request("EXAM_HEARTBEAT", {"attempt_id": self.attempt_id}, self._on_heartbeat)

        if self.events and not self.event_pending and not self.is_submitting and now >= self.next_event_retry:
            self.event_pending = True
            self.worker.request("REPORT_EXAM_EVENT", self.events[0], self._on_event)

        if not self.submit_requested or self.dialog_open:
            return
        if not self.events and not self.event_pending:
            self._execute_submit()
        elif not within_grace and self.next_event_retry == float("inf"):
            self.submit_requested = False
            self._on_submit_finished({"status": "ERROR", "message": "Chưa xác nhận được bài đã nộp."})

    def _on_heartbeat(self, response):
        self.heartbeat_pending = False
        if response["status"] == "SUCCESS":
            data = response["data"]
            self.deadline = min(self.deadline, monotonic() + data["remaining_seconds"])
            if self.next_event_retry == float("inf"):
                self.next_event_retry = 0
            if data["finished"]:
                self.next_heartbeat = float("inf")
            elif not self.timed_out:
                self.monitor_label.configure(text="Đang được giám sát")
        elif not self.timed_out:
            self.monitor_label.configure(text="Mất liên lạc với máy chủ · Đang thử kết nối lại")

    def _on_event(self, response):
        self.event_pending = False
        delay = (response.get("data") or {}).get("retry_after_seconds")
        if delay:
            self.next_event_retry = monotonic() + delay
            return
        if response.get("transport_error") or response.get("retryable"):
            self.next_event_retry = float("inf")
            if self.submit_requested:
                self.submit_failed = True
                self.submit_btn.configure(text="Chờ kết nối…")
            return
        reported = self.events.popleft()
        event_id = reported["event_id"]
        snapshot = self.pending_snapshots.pop(event_id, None)
        if snapshot:
            queued_at, frame = snapshot
            if response["status"] == "SUCCESS" and monotonic() - queued_at <= 30:
                self._upload_snapshot(event_id, queued_at, frame)
        if response["status"] != "SUCCESS":
            self._show_banner(response["message"])

    def _upload_snapshot(self, event_id, queued_at, frame):
        attempt_id = self.attempt_id
        self.snapshot_uploads += 1

        def prepare():
            if not self.snapshot_consent or monotonic() - queued_at > 30:
                return None
            image = encode_snapshot(frame)
            if image:
                return {"attempt_id": attempt_id, "event_id": event_id,
                        "image_format": "jpeg", "image_base64": image}
            return None

        self.worker.request("UPLOAD_EXAM_SNAPSHOT", prepare, self._on_snapshot_uploaded, attempts=2)

    def _on_snapshot_uploaded(self, _response):
        self.snapshot_uploads -= 1

    def _build_nav_buttons(self):
        for btn in self.nav_buttons:
            btn.destroy()
        self.nav_buttons.clear()

        cols = 5
        for idx, q in enumerate(self.questions):
            row = idx // cols
            col = idx % cols

            btn = ctk.CTkButton(
                self.grid_scroll,
                text=str(idx + 1),
                width=40,
                height=36,
                corner_radius=6,
                font=("Helvetica", 12, "bold"),
                fg_color="gray45",
                hover_color="gray35",
                command=lambda i=idx: self._jump_to_question(i)
            )
            btn.grid(row=row, column=col, padx=3, pady=3)
            self.nav_buttons.append(btn)

        self._update_progress_summary()

    # ==================== NAVIGATION & SELECTION ====================

    def _display_current_question(self):
        if not self.questions or self.current_idx < 0 or self.current_idx >= len(self.questions):
            return

        q = self.questions[self.current_idx]
        qid = str(q.get("id"))
        total = len(self.questions)

        # Update index label
        self.q_index_label.configure(text=f"Câu {self.current_idx + 1} / {total}")
        self.diff_badge.configure(text=f"Độ khó: {q.get('difficulty', 'MEDIUM')}")

        # Update text
        self.question_text.configure(text=q.get("content", ""))

        # Update Options
        for key, label in self.option_labels.items():
            label.configure(text=f"{key}. {q.get(f'option_{key.lower()}', '')}")
        self.question_card._parent_canvas.yview_moveto(0)

        # Set selected radio option
        saved_answer = self.answers.get(qid, "")
        self.option_var.set(saved_answer)

        # Update Next/Prev buttons
        self.prev_btn.configure(state="normal" if self.current_idx > 0 else "disabled")
        self.next_btn.configure(state="normal" if self.current_idx < total - 1 else "disabled")

        # Update navigation grid colors
        self._refresh_nav_button_colors()

    def _on_option_selected(self):
        if not self.questions or self._answers_locked():
            return
        qid = str(self.questions[self.current_idx]["id"])
        selected = self.option_var.get()
        self.answers[qid] = selected

        self._update_progress_summary()
        self._refresh_nav_button_colors()

    def _clear_current_answer(self):
        if not self.questions or self._answers_locked():
            return
        qid = str(self.questions[self.current_idx]["id"])
        if qid in self.answers:
            del self.answers[qid]
        self.option_var.set("")

        self._update_progress_summary()
        self._refresh_nav_button_colors()

    def _prev_question(self):
        if self.current_idx > 0:
            self.current_idx -= 1
            self._display_current_question()

    def _next_question(self):
        if self.current_idx < len(self.questions) - 1:
            self.current_idx += 1
            self._display_current_question()

    def _jump_to_question(self, index: int):
        if 0 <= index < len(self.questions):
            self.current_idx = index
            self._display_current_question()

    def _refresh_nav_button_colors(self):
        for idx, btn in enumerate(self.nav_buttons):
            q = self.questions[idx]
            qid = str(q.get("id"))
            is_answered = qid in self.answers

            if idx == self.current_idx:
                # Active question: amber/gold color
                btn.configure(fg_color="#e0a800", text_color="#000000")
            elif is_answered:
                # Answered: primary blue
                btn.configure(fg_color=PRIMARY_COLOR, text_color="#ffffff")
            else:
                # Unanswered: muted gray
                btn.configure(fg_color="gray45", text_color="#ffffff")

    def _update_progress_summary(self):
        total = len(self.questions)
        answered = len(self.answers)
        self.answered_summary_label.configure(text=f"Đã làm: {answered} / {total} câu")
        self.progress_counter_lbl.configure(text=f"Tiến độ hoàn thành: {answered}/{total} câu hỏi")

    # ==================== SUBMISSION LOGIC ====================

    def _answers_locked(self):
        return self.deadline is None or self.is_submitting or self.submit_requested or monotonic() >= self.deadline

    def _confirm_manual_submit(self):
        if self.dialog_open or self.deadline is None or self.is_submitting or self.submit_requested:
            return
        if self.timed_out or self._confirm(
            "Xác nhận nộp bài",
            f"Bạn đã trả lời {len(self.answers)}/{len(self.questions)} câu hỏi. Bạn có muốn nộp bài?",
        ):
            self._request_submit()

    def _confirm(self, title, message):
        self.dialog_open = True
        guard = self.monitor.internal_dialog() if self.monitor else nullcontext()
        try:
            with guard:
                return ask_yes_no(title, message, parent=self)
        finally:
            self.dialog_open = False

    def request_close(self):
        if self.dialog_open or self.deadline is None or self.is_submitting:
            return
        if self.submit_failed and self.close_after_submit:
            if self._confirm("Lưu bản sao đáp án",
                             "Chưa xác nhận được bài đã nộp. Bạn có muốn lưu bản sao đáp án rồi đóng ứng dụng?"):
                self._save_backup_and_close()
            return
        if self.submit_requested:
            return
        if self._confirm("Thoát bài thi", "Nếu đồng ý, các đáp án đã chọn sẽ được nộp, "
                         "bài thi sẽ kết thúc và ứng dụng sẽ đóng. Bạn có muốn thoát?"):
            self.close_after_submit = True
            self._record_event("EXAM_EXIT_REQUESTED")
            self._request_submit()

    def _save_backup_and_close(self):
        self.dialog_open = True
        guard = self.monitor.internal_dialog() if self.monitor else nullcontext()
        try:
            with guard:
                destination = filedialog.asksaveasfilename(
                    parent=self, title="Lưu bản sao đáp án", defaultextension=".json",
                    filetypes=[("JSON", "*.json")],
                )
                if not destination:
                    return
                try:
                    Path(destination).write_text(json.dumps({
                        "exam_id": self.exam_data["id"],
                        "attempt_id": self.attempt_id,
                        "answers": self.answers,
                    }, ensure_ascii=False, indent=2), encoding="utf-8")
                except OSError:
                    show_error("Lỗi lưu tệp", "Không thể ghi bản sao đáp án.", parent=self)
                    return
        finally:
            self.dialog_open = False
        self._stop_monitoring()
        self.on_submitted({"status": "ABORTED", "close_window": True})

    def _set_editing(self, enabled):
        for button in (*self.opt_buttons.values(), self.clear_ans_btn):
            button.configure(state="normal" if enabled else "disabled")

    def _request_submit(self):
        self._clear_warnings()
        self.submit_failed = False
        self.next_event_retry = 0
        self.submit_requested = True
        self._set_editing(False)
        self.submit_btn.configure(state="disabled", text="Đang nộp bài…")

    def _execute_submit(self):
        self.submit_requested = False
        self.is_submitting = True
        self.submit_btn.configure(text="Đang nộp bài…")
        self.worker.request("SUBMIT_EXAM", {
            "exam_id": self.exam_data["id"],
            "attempt_id": self.attempt_id,
            "answers": self.answers.copy(),
        }, self._on_submit_finished, attempts=2)

    def _on_submit_finished(self, response):
        if response["status"] != "SUCCESS":
            self.is_submitting = False
            self.submit_failed = True
            self._set_editing(not self._answers_locked())
            self.submit_btn.configure(state="normal", text="📤 Nộp bài lại")
            self._show_banner(response["message"] + " Các đáp án đã chọn vẫn được giữ trong cửa sổ này.")
            return

        self._stop_monitoring()
        result = response["data"]
        score = float(result["score"])
        show_info(
            "Kết quả thi",
            f"Nộp bài thành công. Điểm: {score:.2f}/10. "
            f"Số câu đúng: {result['correct_count']}/{result['total_questions']}.",
            parent=self,
        )
        self.on_submitted({**result, "close_window": self.close_after_submit})

    def _stop_monitoring(self):
        self.worker.stop()
        self.pending_snapshots.clear()
        self._stop_camera()
        self.monitor = None
        self._clear_warnings()
        if self.poll_job is not None:
            self.after_cancel(self.poll_job)
            self.poll_job = None
        if self.exam_window is not None:
            self.exam_window.restore()
            self.exam_window = None

    def destroy(self):
        self._stop_monitoring()
        super().destroy()
