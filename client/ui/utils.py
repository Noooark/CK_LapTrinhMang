import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

# Application Theme Colors
PRIMARY_COLOR = "#1f6aa5"
PRIMARY_HOVER = "#144870"
SUCCESS_COLOR = "#28a745"
DANGER_COLOR = "#dc3545"
WARNING_COLOR = "#fd7e14"
TEXT_MUTED = "#888888"


def style_treeview(style: ttk.Style):
    """
    Applies modern styling to ttk.Treeview for clean dark/light mode appearance.
    """
    style.theme_use("clam")

    # Treeview rows
    style.configure(
        "Treeview",
        background="#2b2b2b",
        foreground="#ffffff",
        fieldbackground="#2b2b2b",
        rowheight=32,
        font=("Helvetica", 10),
        borderwidth=0
    )
    style.map(
        "Treeview",
        background=[("selected", PRIMARY_COLOR)],
        foreground=[("selected", "#ffffff")]
    )

    # Treeview headings
    style.configure(
        "Treeview.Heading",
        background="#1f232a",
        foreground="#ffffff",
        font=("Helvetica", 10, "bold"),
        borderwidth=1,
        relief="flat",
        padding=(8, 6)
    )
    style.map(
        "Treeview.Heading",
        background=[("active", "#2d333b")]
    )


def show_info(title: str, message: str, parent=None):
    messagebox.showinfo(title, message, parent=parent)


def show_error(title: str, message: str, parent=None):
    messagebox.showerror(title, message, parent=parent)


def show_warning(title: str, message: str, parent=None):
    messagebox.showwarning(title, message, parent=parent)


def ask_yes_no(title: str, message: str, parent=None) -> bool:
    return messagebox.askyesno(title, message, parent=parent)
