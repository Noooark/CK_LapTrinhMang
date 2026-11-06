import threading
from typing import Dict, Any, Optional, List, Callable
import customtkinter as ctk

from client.network import ServerConnection
from client.ui.utils import (
    PRIMARY_COLOR, PRIMARY_HOVER, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR,
    show_error, show_info, show_warning, ask_yes_no
)


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
        **kwargs
    ):
        super().__init__(master, **kwargs)
        self.connection = connection
        self.token = token
        self.exam_data = exam_data
        self.on_submitted = on_submitted

        # Exam state
        self.questions: List[Dict[str, Any]] = []
        self.current_idx: int = 0
        self.answers: Dict[str, str] = {}  # str(qid) -> "A"|"B"|"C"|"D"
        self.nav_buttons: List[ctk.CTkButton] = []
        self.is_submitting: bool = False
        self.timer_job: Optional[str] = None

        # Calculate duration in seconds
        duration_mins = int(self.exam_data.get("duration_minutes", 30))
        self.time_left_seconds = duration_mins * 60

        self._build_ui()
        self._load_questions()

    def _build_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=3)  # Main question area
        self.grid_columnconfigure(1, weight=1)  # Right sidebar

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
        q_box = ctk.CTkFrame(self.question_container, corner_radius=12, fg_color=("gray90", "#242830"))
        q_box.grid(row=1, column=0, sticky="nsew")
        q_box.grid_rowconfigure(0, weight=1)
        q_box.grid_rowconfigure(1, weight=2)
        q_box.grid_columnconfigure(0, weight=1)

        # Question text display
        self.content_textbox = ctk.CTkTextbox(
            q_box,
            font=("Helvetica", 14),
            wrap="word",
            fg_color="transparent",
            height=130
        )
        self.content_textbox.grid(row=0, column=0, padx=25, pady=(20, 10), sticky="nsew")
        self.content_textbox.insert("1.0", "Đang tải dữ liệu câu hỏi...")
        self.content_textbox.configure(state="disabled")

        # Separator line
        ctk.CTkFrame(q_box, height=1, fg_color=("gray80", "#333842")).grid(row=0, column=0, sticky="sew", padx=25)

        # Options Container (A, B, C, D)
        options_frame = ctk.CTkFrame(q_box, fg_color="transparent")
        options_frame.grid(row=1, column=0, padx=25, pady=15, sticky="nsew")
        options_frame.grid_columnconfigure(0, weight=1)

        self.option_var = ctk.StringVar(value="")

        self.opt_buttons = {}
        for idx, key in enumerate(["A", "B", "C", "D"]):
            rb = ctk.CTkRadioButton(
                options_frame,
                text=f"{key}. ",
                value=key,
                variable=self.option_var,
                command=self._on_option_selected,
                font=("Helvetica", 13),
                radiobutton_width=20,
                radiobutton_height=20
            )
            rb.grid(row=idx, column=0, padx=10, pady=8, sticky="w")
            self.opt_buttons[key] = rb

        # Clear answer button
        self.clear_ans_btn = ctk.CTkButton(
            options_frame,
            text="❌ Bỏ chọn câu trả lời",
            width=160,
            height=28,
            fg_color="transparent",
            text_color="gray60",
            hover_color=("gray85", "#2a2d36"),
            font=("Helvetica", 11),
            command=self._clear_current_answer
        )
        self.clear_ans_btn.grid(row=4, column=0, padx=10, pady=(10, 0), sticky="w")

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
        self.grid_scroll = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        self.grid_scroll.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")
        for col in range(5):
            self.grid_scroll.grid_columnconfigure(col, weight=1)

        # Legend at bottom of sidebar
        legend_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        legend_frame.grid(row=3, column=0, padx=15, pady=(10, 15), sticky="ew")

        legend_text = "🔵 Đã làm   ⚪ Chưa làm   🟡 Đang xem"
        ctk.CTkLabel(legend_frame, text=legend_text, font=("Helvetica", 11), text_color="gray60").pack()

    # ==================== HELPERS & TIMER ====================

    def _format_time(self, seconds: int) -> str:
        mins = max(0, seconds) // 60
        secs = max(0, seconds) % 60
        return f"⏱️ {mins:02d}:{secs:02d}"

    def _start_timer(self):
        self._tick_timer()

    def _tick_timer(self):
        if self.is_submitting:
            return

        self.timer_label.configure(text=self._format_time(self.time_left_seconds))

        # Alert color when less than 2 minutes remain
        if self.time_left_seconds <= 120:
            self.timer_label.configure(text_color=DANGER_COLOR)
        else:
            self.timer_label.configure(text_color=PRIMARY_COLOR)

        if self.time_left_seconds <= 0:
            self._auto_submit_on_timeout()
            return

        self.time_left_seconds -= 1
        self.timer_job = self.after(1000, self._tick_timer)

    def _stop_timer(self):
        if self.timer_job:
            try:
                self.after_cancel(self.timer_job)
            except Exception:
                pass
            self.timer_job = None

    # ==================== DATA LOADING ====================

    def _load_questions(self):
        exam_id = self.exam_data.get("id")

        def worker():
            try:
                resp = self.connection.send_request("GET_EXAM_QUESTIONS", data={"exam_id": exam_id}, token=self.token)
                self.after(0, lambda: self._on_questions_loaded(resp))
            except Exception as e:
                self.after(0, lambda: self._on_load_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_questions_loaded(self, resp):
        if resp and resp.get("status") == "SUCCESS":
            self.questions = resp.get("data") or []
        else:
            self.questions = []

        if not self.questions:
            show_error("Lỗi đề thi", "Không thể tải danh sách câu hỏi của đề thi này!", parent=self)
            self._abort_exam()
            return

        # Build numbered buttons in grid
        self._build_nav_buttons()

        # Display first question
        self.current_idx = 0
        self._display_current_question()

        # Start timer
        self._start_timer()

    def _on_load_error(self, err_msg):
        show_error("Lỗi kết nối", err_msg, parent=self)
        self._abort_exam()

    def _abort_exam(self):
        self._stop_timer()
        if self.on_submitted:
            self.on_submitted({"status": "ABORTED"})

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
        self.content_textbox.configure(state="normal")
        self.content_textbox.delete("1.0", "end")
        self.content_textbox.insert("1.0", q.get("content", ""))
        self.content_textbox.configure(state="disabled")

        # Update Options
        self.opt_buttons["A"].configure(text=f"A. {q.get('option_a', '')}")
        self.opt_buttons["B"].configure(text=f"B. {q.get('option_b', '')}")
        self.opt_buttons["C"].configure(text=f"C. {q.get('option_c', '')}")
        self.opt_buttons["D"].configure(text=f"D. {q.get('option_d', '')}")

        # Set selected radio option
        saved_answer = self.answers.get(qid, "")
        self.option_var.set(saved_answer)

        # Update Next/Prev buttons
        self.prev_btn.configure(state="normal" if self.current_idx > 0 else "disabled")
        self.next_btn.configure(state="normal" if self.current_idx < total - 1 else "disabled")

        # Update navigation grid colors
        self._refresh_nav_button_colors()

    def _on_option_selected(self):
        if not self.questions:
            return
        qid = str(self.questions[self.current_idx]["id"])
        selected = self.option_var.get()
        self.answers[qid] = selected

        self._update_progress_summary()
        self._refresh_nav_button_colors()

    def _clear_current_answer(self):
        if not self.questions:
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

    def _confirm_manual_submit(self):
        total = len(self.questions)
        answered = len(self.answers)
        unanswered = total - answered

        msg = f"Bạn đã trả lời {answered}/{total} câu hỏi."
        if unanswered > 0:
            msg += f"\n(Còn {unanswered} câu chưa trả lời!)"
        msg += "\n\nBạn có chắc chắn muốn nộp bài ngay bây giờ?"

        confirm = ask_yes_no("Xác nhận nộp bài", msg, parent=self)
        if confirm:
            self._execute_submit(is_timeout=False)

    def _auto_submit_on_timeout(self):
        self._stop_timer()
        show_warning(
            "Hết giờ làm bài!",
            "Thời gian làm bài thi đã hết!\nHệ thống sẽ tự động nộp bài thi của bạn.",
            parent=self
        )
        self._execute_submit(is_timeout=True)

    def _execute_submit(self, is_timeout: bool = False):
        if self.is_submitting:
            return

        self.is_submitting = True
        self._stop_timer()

        # UI state
        self.submit_btn.configure(state="disabled", text="Đang nộp bài...")
        self.prev_btn.configure(state="disabled")
        self.next_btn.configure(state="disabled")
        self.clear_ans_btn.configure(state="disabled")

        exam_id = self.exam_data.get("id")

        def worker():
            try:
                payload = {
                    "exam_id": exam_id,
                    "answers": self.answers
                }
                resp = self.connection.send_request("SUBMIT_EXAM", data=payload, token=self.token)
                self.after(0, lambda: self._on_submit_finished(resp))
            except Exception as e:
                self.after(0, lambda: self._on_submit_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_submit_finished(self, resp):
        if resp and resp.get("status") == "SUCCESS":
            result_data = resp.get("data") or {}
            score = float(result_data.get("score", 0.0))
            correct = result_data.get("correct_count", 0)
            total = result_data.get("total_questions", len(self.questions))
            is_pass = score >= 5.0

            msg = (
                "🎉 NỘP BÀI THÀNH CÔNG!\n\n"
                f"• Điểm số đạt được: {score:.1f} / 10\n"
                f"• Số câu đúng: {correct} / {total}\n"
                f"• Kết quả: {'ĐẠT CHUẨN ✅' if is_pass else 'CHƯA ĐẠT ❌'}\n\n"
                "Kết quả đã được lưu vào hệ thống."
            )
            show_info("Kết quả thi", msg, parent=self)

            if self.on_submitted:
                self.on_submitted(result_data)
        else:
            msg = resp.get("message", "Nộp bài thất bại!") if resp else "Lỗi máy chủ"
            show_error("Lỗi nộp bài", msg, parent=self)
            self.submit_btn.configure(state="normal", text="📤 Nộp bài lại")
            self.is_submitting = False

    def _on_submit_error(self, err_msg):
        show_error("Lỗi kết nối khi nộp bài", err_msg, parent=self)
        self.submit_btn.configure(state="normal", text="📤 Nộp bài lại")
        self.is_submitting = False

    def destroy(self):
        self._stop_timer()
        super().destroy()
