import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk

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
    _notice(title, message, parent, PRIMARY_COLOR)


def show_error(title: str, message: str, parent=None):
    _notice(title, message, parent, DANGER_COLOR, native=messagebox.showerror)


def show_warning(title: str, message: str, parent=None):
    _notice(title, message, parent, WARNING_COLOR, native=messagebox.showwarning)


def ask_yes_no(title: str, message: str, parent=None) -> bool:
    return _notice(title, message, parent, PRIMARY_COLOR, confirm=True)


def _notice(title, message, parent, color, confirm=False, native=messagebox.showinfo):
    parent = parent if parent is not None else tk._default_root
    if parent is None:
        fallback = messagebox.askyesno if confirm else native
        return fallback(title, message)

    owner = parent.winfo_toplevel()
    previous_grab = owner.grab_current()
    accepted = False
    dialog = ctk.CTkToplevel(owner)
    dialog.withdraw()
    dialog.title(title)
    dialog.transient(owner)
    dialog.resizable(False, False)

    def close(result=False):
        nonlocal accepted
        accepted = result
        dialog.destroy()

    dialog.protocol("WM_DELETE_WINDOW", close)
    dialog.bind("<Escape>", lambda _: close())
    card = ctk.CTkFrame(dialog, border_width=1, border_color=color)
    card.pack(padx=14, pady=14, fill="both", expand=True)
    ctk.CTkLabel(card, text=title, font=("Helvetica", 22, "bold"),
                 text_color=color, wraplength=470).pack(padx=24, pady=(20, 8))
    ctk.CTkLabel(card, text=message, font=("Helvetica", 16), wraplength=470,
                 justify="center").pack(padx=24, pady=(2, 16))
    actions = ctk.CTkFrame(card, fg_color="transparent")
    actions.pack(padx=24, pady=(0, 20))
    if confirm:
        ctk.CTkButton(actions, text="Quay lại", height=36, font=("Helvetica", 14),
                      fg_color="gray40", command=close).pack(side="left", padx=6)
    ctk.CTkButton(actions, text="Đồng ý" if confirm else "Đóng", height=36,
                  font=("Helvetica", 14, "bold"), command=lambda: close(True)).pack(side="left", padx=6)

    dialog.update_idletasks()
    x = owner.winfo_rootx() + (owner.winfo_width() - dialog.winfo_reqwidth()) // 2
    y = owner.winfo_rooty() + (owner.winfo_height() - dialog.winfo_reqheight()) // 2
    dialog.geometry(f"{x:+d}{y:+d}")
    dialog.deiconify()
    dialog.wait_visibility()
    dialog.grab_set()
    dialog.focus_set()
    owner.wait_window(dialog)
    if previous_grab is not None and previous_grab.winfo_exists():
        previous_grab.grab_set()
    return accepted
