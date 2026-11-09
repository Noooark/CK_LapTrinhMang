"""Shared centered cards for exam consent and monitoring notices."""
import customtkinter as ctk


def exam_notice(parent, title, message, color):
    overlay = ctk.CTkFrame(parent, corner_radius=0, fg_color=("gray85", "#1c1e24"))
    overlay.place(relwidth=1, relheight=1)
    card = ctk.CTkFrame(overlay, border_width=1, border_color=color)
    card.place(relx=0.5, rely=0.5, anchor="center")
    ctk.CTkLabel(card, text=title, text_color=color, font=("Helvetica", 22, "bold"),
                 wraplength=410).pack(padx=26, pady=(22, 8))
    ctk.CTkLabel(card, text=message, font=("Helvetica", 15), wraplength=410,
                 justify="center").pack(padx=26, pady=(4, 12))
    overlay.focus_set()
    return overlay, card
