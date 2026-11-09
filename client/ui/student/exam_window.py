"""Maximize the exam in the desktop work area and restore it afterwards."""
from tkinter import TclError


class ExamWindow:
    def __init__(self, root):
        self.root = root
        self.original_fullscreen = root.attributes("-fullscreen")
        self.zoomed_attribute = root.tk.call("tk", "windowingsystem") == "x11"
        self.original_zoomed = (root.attributes("-zoomed") if self.zoomed_attribute
                                else root.state() == "zoomed")

    def _maximize(self, enabled):
        if self.zoomed_attribute:
            self.root.attributes("-zoomed", enabled)
        else:
            self.root.state("zoomed" if enabled else "normal")

    def enter(self):
        if self.original_fullscreen:
            self.root.attributes("-fullscreen", False)
        try:
            self._maximize(True)
        except TclError:
            # A window manager without maximize support keeps the standard window.
            return

    def restore(self):
        try:
            self._maximize(self.original_zoomed)
        except TclError:
            pass
        if self.original_fullscreen:
            self.root.attributes("-fullscreen", True)
