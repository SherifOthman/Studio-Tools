"""
pages/settings.py  –  Settings page.
All changes (language, theme, appearance) apply INSTANTLY.
Theme picker: coloured swatch buttons only — no duplicate radio buttons.
"""

import customtkinter as ctk

from app.core.prefs   import prefs
from app.core.strings import t, is_rtl

PAD = 16

THEMES = [
    ("blue",      "Ocean Blue",  "#3B82F6"),
    ("green",     "Green",       "#22C55E"),
    ("dark-blue", "Dark Blue",   "#1D4ED8"),
]

MODES = [
    ("dark",   "mode_dark"),
    ("light",  "mode_light"),
    ("system", "mode_system"),
]


class SettingsPage(ctk.CTkFrame):
    def __init__(self, master, on_lang_change=None, on_theme_change=None, **kw):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kw)
        self._on_lang  = on_lang_change
        self._on_theme = on_theme_change
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build()

    def _build(self):
        anchor = "e" if is_rtl() else "w"

        # Header
        hdr = ctk.CTkFrame(self, corner_radius=0, height=64)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        ctk.CTkLabel(
            hdr, text=t("set_title"),
            font=ctk.CTkFont("Segoe UI", 22, "bold"),
            anchor=anchor,
        ).pack(side="right" if is_rtl() else "left", padx=PAD, pady=18)

        # Body — two columns on wide screens
        scroll = ctk.CTkScrollableFrame(
            self, corner_radius=0, fg_color="transparent",
        )
        scroll.grid(row=1, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)
        scroll.grid_columnconfigure(1, weight=1)

        # Left column: Language + Theme
        col0 = ctk.CTkFrame(scroll, fg_color="transparent")
        col0.grid(row=0, column=0 if not is_rtl() else 1,
                  sticky="nsew", padx=(PAD, PAD // 2), pady=0)

        # Right column: Appearance + About
        col1 = ctk.CTkFrame(scroll, fg_color="transparent")
        col1.grid(row=0, column=1 if not is_rtl() else 0,
                  sticky="nsew", padx=(PAD // 2, PAD), pady=0)

        self._build_lang_card(col0)
        self._build_theme_card(col0)
        self._build_mode_card(col1)
        self._build_about_card(col1)

    # ── Language ──────────────────────────────────────────────────────────

    def _build_lang_card(self, parent):
        card = self._card(parent, t("set_lang"))
        seg = ctk.CTkSegmentedButton(
            card,
            values=["English", "العربية"],
            command=self._lang_changed,
            font=ctk.CTkFont("Segoe UI", 13),
            height=40,
        )
        seg.set("English" if prefs["lang"] == "en" else "العربية")
        seg.pack(anchor="e" if is_rtl() else "w")

    def _lang_changed(self, value: str):
        code = "en" if value == "English" else "ar"
        prefs["lang"] = code
        prefs.save()
        if self._on_lang:
            self._on_lang(code)

    # ── Colour theme ──────────────────────────────────────────────────────

    def _build_theme_card(self, parent):
        """Clean swatch-button picker — NO radio buttons, no duplicates."""
        card = self._card(parent, t("set_theme"))

        self._theme_btns: dict[str, ctk.CTkFrame] = {}
        current = prefs["theme"]

        for tid, label, colour in THEMES:
            is_active = (tid == current)
            row = ctk.CTkFrame(
                card,
                fg_color=colour if is_active else ("gray85","gray20"),
                corner_radius=10,
                cursor="hand2",
            )
            row.pack(fill="x", pady=(0, 8))

            # Swatch dot
            dot = ctk.CTkFrame(
                row, width=18, height=18,
                corner_radius=9,
                fg_color=colour,
            )
            dot.pack(side="right" if is_rtl() else "left",
                     padx=(10, 6), pady=10)

            lbl = ctk.CTkLabel(
                row, text=label,
                font=ctk.CTkFont("Segoe UI", 12,
                                  "bold" if is_active else "normal"),
                text_color=("white" if is_active
                             else ("gray20","gray85")),
            )
            lbl.pack(side="right" if is_rtl() else "left",
                     padx=(0, 10), pady=10)

            # ✓ check on active
            check = ctk.CTkLabel(
                row, text="✓" if is_active else "",
                font=ctk.CTkFont("Segoe UI", 14, "bold"),
                text_color="white",
                width=24,
            )
            check.pack(side="left" if is_rtl() else "right",
                       padx=(0, 10))

            self._theme_btns[tid] = (row, dot, lbl, check, colour)

            # Bind click to all children
            for w in (row, dot, lbl, check):
                w.bind("<Button-1>", lambda _, t=tid: self._theme_changed(t))
            row.bind("<Enter>", lambda e, r=row, t=tid, c=colour, a=(tid==current):
                     r.configure(fg_color=c) if not a else None)
            row.bind("<Leave>", lambda e, r=row, t=tid, c=colour, a=(tid==current):
                     r.configure(fg_color=("gray85","gray20")) if not a else None)

    def _theme_changed(self, tid: str):
        prefs["theme"] = tid
        prefs.save()
        if self._on_theme:
            self._on_theme(tid)

    # ── Appearance mode ───────────────────────────────────────────────────

    def _build_mode_card(self, parent):
        card = self._card(parent, t("set_mode"))

        values    = [t(key) for _, key in MODES]
        mode_map  = {t(key): mode for mode, key in MODES}
        mode_rmap = {mode: t(key) for mode, key in MODES}

        seg = ctk.CTkSegmentedButton(
            card, values=values,
            command=lambda v: self._mode_changed(mode_map.get(v, "dark")),
            font=ctk.CTkFont("Segoe UI", 12),
            height=40,
        )
        saved = prefs.get("appearance", "dark")
        seg.set(mode_rmap.get(saved, values[0]))
        seg.pack(anchor="e" if is_rtl() else "w")

    def _mode_changed(self, mode: str):
        prefs["appearance"] = mode
        prefs.save()
        ctk.set_appearance_mode(mode)

    # ── About ─────────────────────────────────────────────────────────────

    def _build_about_card(self, parent):
        card = self._card(parent, t("set_about"))
        anchor = "e" if is_rtl() else "w"
        ctk.CTkLabel(
            card, text=t("about_body"),
            font=ctk.CTkFont("Segoe UI", 12),
            justify="right" if is_rtl() else "left",
            anchor=anchor,
        ).pack(anchor=anchor)

    # ── Card helper ───────────────────────────────────────────────────────

    def _card(self, parent, title: str) -> ctk.CTkFrame:
        anchor = "e" if is_rtl() else "w"
        outer = ctk.CTkFrame(parent, corner_radius=12)
        outer.pack(fill="x", pady=(0, PAD))
        ctk.CTkLabel(
            outer, text=title,
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            anchor=anchor,
        ).pack(anchor=anchor, padx=PAD, pady=(12, 0))
        ctk.CTkFrame(
            outer, height=1, fg_color=("gray85","gray30"), corner_radius=0,
        ).pack(fill="x", padx=PAD, pady=(6, 0))
        inner = ctk.CTkFrame(outer, fg_color="transparent")
        inner.pack(fill="both", padx=PAD, pady=(10, 14))
        return inner
