"""Track app focus from the Tk thread."""
from contextlib import contextmanager
from time import monotonic
from tkinter import TclError


FOCUS_THRESHOLD = 2.5
FOCUS_WARNING = (
    "Bạn đã rời khỏi cửa sổ làm bài. Hành vi này đã được hệ thống ghi nhận "
    "và thông báo cho giáo viên."
)


class FocusMonitor:
    def __init__(self, root, report, warn, threshold=FOCUS_THRESHOLD, clock=monotonic):
        self.root = root
        self.report = report
        self.warn = warn
        self.threshold = threshold
        self.clock = clock
        self.away_since = None
        self.reported = False
        self.dialog_depth = 0
        self.ready_at = clock() + 0.75

    @contextmanager
    def internal_dialog(self):
        self.dialog_depth += 1
        try:
            yield
        finally:
            self.dialog_depth -= 1
            self.away_since = None
            self.reported = False
            self.ready_at = self.clock() + 0.4

    def sample(self):
        now = self.clock()
        if self.dialog_depth or now < self.ready_at:
            return
        try:
            # Tk returns the focused widget for this application, including its toplevels.
            in_app = self.root.focus_displayof() is not None
        except (TclError, KeyError):
            # Some native dialogs use a Tcl widget that has no Python wrapper.
            in_app = bool(self.root.tk.call("focus", "-displayof", self.root._w))
        if not in_app and self.away_since is None:
            self.away_since = now
        if self.away_since is None:
            return
        elapsed = now - self.away_since
        if elapsed >= self.threshold and not self.reported:
            self.report("FOCUS_LOST", elapsed)
            self.reported = True
        if in_app:
            if self.reported:
                self.warn(FOCUS_WARNING)
            self.away_since = None
            self.reported = False
