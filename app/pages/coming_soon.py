"""pages/coming_soon.py  –  Placeholder page for unbuilt tools."""

import customtkinter as ctk
from app.core.strings import t

ICONS = {"images": "🖼", "rename": "✏️"}


class ComingSoonPage(ctk.CTkFrame):
    def __init__(self, master, page_id: str = "images", **kw):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kw)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        centre = ctk.CTkFrame(self, fg_color="transparent")
        centre.grid(row=0, column=0)

        ctk.CTkLabel(
            centre, text=ICONS.get(page_id, "🚧"),
            font=ctk.CTkFont(size=72),
        ).pack(pady=(0, 16))

        ctk.CTkLabel(
            centre, text=t("coming_soon"),
            font=ctk.CTkFont("Segoe UI", 26, "bold"),
        ).pack()

        ctk.CTkLabel(
            centre, text=t("coming_body"),
            font=ctk.CTkFont("Segoe UI", 13),
            text_color=("gray40", "gray60"),
            justify="center",
        ).pack(pady=(8, 0))
