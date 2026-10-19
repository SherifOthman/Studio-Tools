"""
pages/settings.py  –  Settings page.
Language and theme changes apply INSTANTLY without any restart.
"""

import customtkinter as ctk

from app.core.prefs   import prefs
from app.core.strings import t

PAD = 20

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
        self._on_lang   = on_lang_change
        self._on_theme  = on_theme_change
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build()

    def _build(self):
        # Header
        hdr = ctk.CTkFrame(self, corner_radius=0, height=68)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        ctk.CTkLabel(
            hdr, text=t("set_title"),
            font=ctk.CTkFont("Segoe UI", 22, "bold"), anchor="w",
        ).pack(side="left", padx=PAD, pady=18)

        # Scrollable body
        scroll = ctk.CTkScrollableFrame(
            self, corner_radius=0, fg_color="transparent",
        )
        scroll.grid(row=1, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        self._build_lang_card(scroll)
        self._build_theme_card(scroll)
        self._build_mode_card(scroll)
        self._build_about_card(scroll)

    # ── Language ─────────────────────────────────────────────────────────

    def _build_lang_card(self, parent):
        card = self._card(parent, t("set_lang"))

        self._lang_var = ctk.StringVar(value=prefs["lang"])

        seg = ctk.CTkSegmentedButton(
            card,
            values=["English", "العربية"],
            command=self._lang_changed,
            font=ctk.CTkFont("Segoe UI", 12),
            height=38,
        )
        seg.set("English" if prefs["lang"] == "en" else "العربية")
        seg.pack(anchor="w")
        self._lang_seg = seg

    def _lang_changed(self, value: str):
        code = "en" if value == "English" else "ar"
        prefs["lang"] = code
        prefs.save()
        if self._on_lang:
            self._on_lang(code)

    # ── Colour theme ─────────────────────────────────────────────────────

    def _build_theme_card(self, parent):
        card = self._card(parent, t("set_theme"))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(anchor="w")

        self._theme_var = ctk.StringVar(value=prefs["theme"])

        for tid, label, colour in THEMES:
            btn_frame = ctk.CTkFrame(row, fg_color="transparent")
            btn_frame.pack(side="left", padx=(0, 16))

            # Colour swatch circle
            swatch = ctk.CTkFrame(
                btn_frame, width=22, height=22,
                corner_radius=11, fg_color=colour,
            )
            swatch.pack(side="left", padx=(0, 6))
            swatch.bind("<Button-1>", lambda _, tid=tid: self._theme_changed(tid))

            rb = ctk.CTkRadioButton(
                btn_frame, text=label,
                variable=self._theme_var, value=tid,
                command=lambda tid=tid: self._theme_changed(tid),
                font=ctk.CTkFont("Segoe UI", 12),
            )
            rb.pack(side="left")

    def _theme_changed(self, tid: str):
        self._theme_var.set(tid)
        prefs["theme"] = tid
        prefs.save()
        if self._on_theme:
            self._on_theme(tid)

    # ── Appearance mode ───────────────────────────────────────────────────

    def _build_mode_card(self, parent):
        card = self._card(parent, t("set_mode"))

        values = [t(key) for _, key in MODES]
        self._mode_map = {t(key): mode for mode, key in MODES}
        self._mode_rmap = {mode: t(key) for mode, key in MODES}

        seg = ctk.CTkSegmentedButton(
            card, values=values,
            command=self._mode_changed,
            font=ctk.CTkFont("Segoe UI", 12),
            height=38,
        )
        saved = prefs.get("appearance", "dark")
        seg.set(self._mode_rmap.get(saved, values[0]))
        seg.pack(anchor="w")

    def _mode_changed(self, value: str):
        mode = self._mode_map.get(value, "dark")
        prefs["appearance"] = mode
        prefs.save()
        ctk.set_appearance_mode(mode)

    # ── About ─────────────────────────────────────────────────────────────

    def _build_about_card(self, parent):
        card = self._card(parent, t("set_about"))
        ctk.CTkLabel(
            card, text=t("about_body"),
            font=ctk.CTkFont("Segoe UI", 12),
            justify="left",
            anchor="w",
        ).pack(anchor="w")

    # ── Helper ────────────────────────────────────────────────────────────

    def _card(self, parent, title: str) -> ctk.CTkFrame:
        outer = ctk.CTkFrame(parent, corner_radius=12)
        outer.pack(fill="x", padx=PAD, pady=(0, PAD))
        ctk.CTkLabel(
            outer, text=title,
            font=ctk.CTkFont("Segoe UI", 13, "bold"), anchor="w",
        ).pack(anchor="w", padx=PAD, pady=(14, 0))
        ctk.CTkFrame(outer, height=1,
                     fg_color=("gray85","gray30"),
                     corner_radius=0).pack(fill="x", padx=PAD, pady=(6, 0))
        inner = ctk.CTkFrame(outer, fg_color="transparent")
        inner.pack(fill="both", padx=PAD, pady=(10, 14))
        return inner
