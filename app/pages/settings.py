"""pages/settings.py – Settings page."""

import customtkinter as ctk

from app.core.prefs   import prefs
from app.core.strings import t

PAD = 16

THEMES = [
    ("blue",   "Ocean Blue", "#2563EB"),
    ("purple", "Purple",     "#7C3AED"),
    ("teal",   "Teal",       "#0D9488"),
]

MODES = [
    ("dark",   "mode_dark"),
    ("light",  "mode_light"),
    ("system", "mode_system"),
]


class SettingsPage(ctk.CTkFrame):
    def __init__(self, master, on_theme_change=None, **kw):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kw)
        self._on_theme = on_theme_change
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build()

    def _build(self):
        hdr = ctk.CTkFrame(self, corner_radius=0, height=70)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text=t("set_title"),
                     font=ctk.CTkFont("Segoe UI", 22, "bold"),
                     anchor="w").pack(side="left", padx=PAD, pady=18)
        ctk.CTkFrame(self, height=1, fg_color=("gray78", "gray28"),
                     corner_radius=0).grid(row=0, column=0, sticky="sew")

        scroll = ctk.CTkScrollableFrame(self, corner_radius=0,
                                         fg_color="transparent")
        scroll.grid(row=1, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)
        scroll.grid_columnconfigure(1, weight=1)

        col0 = ctk.CTkFrame(scroll, fg_color="transparent")
        col0.grid(row=0, column=0, sticky="nsew",
                  padx=(PAD, PAD // 2), pady=PAD)
        col1 = ctk.CTkFrame(scroll, fg_color="transparent")
        col1.grid(row=0, column=1, sticky="nsew",
                  padx=(PAD // 2, PAD), pady=PAD)

        self._build_theme_card(col0)
        self._build_mode_card(col0)
        self._build_about_card(col1)

    # ── Theme ──────────────────────────────────────────────────────────────

    def _build_theme_card(self, parent):
        inner = self._card(parent, t("set_theme"))
        current = prefs.get("theme", "blue")

        for tid, label_text, colour in THEMES:
            active = (tid == current)
            self._theme_row(inner, tid, label_text, colour, active)

    def _theme_row(self, parent, tid: str, label_text: str,
                   colour: str, active: bool):
        """One clickable theme row."""
        card = ctk.CTkFrame(
            parent,
            fg_color=colour if active else ("gray88", "gray20"),
            corner_radius=10,
            cursor="hand2",
        )
        card.pack(fill="x", pady=(0, 8))

        # Colour dot
        dot = ctk.CTkFrame(card, width=20, height=20,
                            corner_radius=10, fg_color=colour)
        dot.pack(side="left", padx=(12, 8), pady=12)

        # Label
        lbl = ctk.CTkLabel(
            card, text=label_text,
            font=ctk.CTkFont("Segoe UI", 13, "bold" if active else "normal"),
            text_color=("white" if active else ("gray10", "gray90")),
            anchor="w",
        )
        lbl.pack(side="left", fill="x", expand=True, pady=12)

        # Check mark
        chk = ctk.CTkLabel(
            card, text="✓" if active else "",
            font=ctk.CTkFont("Segoe UI", 14, "bold"),
            text_color="white",
            width=28,
        )
        chk.pack(side="right", padx=(0, 12))

        # Bind click to every widget in the row
        for w in (card, dot, lbl, chk):
            w.bind("<Button-1>", lambda _, x=tid: self._theme_changed(x))

    def _theme_changed(self, tid: str):
        prefs["theme"] = tid
        prefs.save()
        if self._on_theme:
            self._on_theme(tid)

    # ── Appearance ─────────────────────────────────────────────────────────

    def _build_mode_card(self, parent):
        inner = self._card(parent, t("set_mode"))
        values  = [t(k) for _, k in MODES]
        fwd_map = {t(k): m for m, k in MODES}
        rev_map = {m: t(k) for m, k in MODES}

        seg = ctk.CTkSegmentedButton(
            inner, values=values,
            command=lambda v: self._mode_changed(fwd_map.get(v, "dark")),
            font=ctk.CTkFont("Segoe UI", 12),
            height=40,
        )
        seg.set(rev_map.get(prefs.get("appearance", "dark"), values[0]))
        seg.pack(anchor="w")

    def _mode_changed(self, mode: str):
        prefs["appearance"] = mode
        prefs.save()
        ctk.set_appearance_mode(mode)

    # ── About ───────────────────────────────────────────────────────────────

    def _build_about_card(self, parent):
        inner = self._card(parent, t("set_about"))
        ctk.CTkLabel(inner, text=t("about_body"),
                     font=ctk.CTkFont("Segoe UI", 12),
                     justify="left", anchor="w").pack(anchor="w")

    # ── Card factory ────────────────────────────────────────────────────────

    def _card(self, parent, title: str) -> ctk.CTkFrame:
        outer = ctk.CTkFrame(parent, corner_radius=12)
        outer.pack(fill="x", pady=(0, PAD))
        ctk.CTkLabel(outer, text=title,
                     font=ctk.CTkFont("Segoe UI", 13, "bold"),
                     anchor="w").pack(anchor="w", padx=PAD, pady=(12, 0))
        ctk.CTkFrame(outer, height=1, fg_color=("gray82", "gray30"),
                     corner_radius=0).pack(fill="x", padx=PAD, pady=(6, 0))
        inner = ctk.CTkFrame(outer, fg_color="transparent")
        inner.pack(fill="both", padx=PAD, pady=(10, 14))
        return inner
