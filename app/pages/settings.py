"""
pages/settings.py  –  Settings page (RTL-correct).

RTL rules applied:
  • All content starts from the reading-start edge (right in Arabic).
  • Theme picker: clean swatch cards, no radio buttons.
  • Segmented buttons (CTkSegmentedButton) handle their own mirroring fine.
  • Two-column layout: Language+Theme on one side, Appearance+About on the other.
    In RTL the column order is reversed so reading starts from the right.
"""

import customtkinter as ctk

from app.core        import rtl as R
from app.core.prefs  import prefs
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
        # ── Header ───────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, corner_radius=0, height=70)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)

        ctk.CTkLabel(
            hdr, text=t("set_title"),
            font=ctk.CTkFont("Segoe UI", 22, "bold"),
            anchor=R.anchor_start(),
        ).pack(side=R.start(), padx=PAD, pady=18)

        # Separator under header
        ctk.CTkFrame(
            self, height=1, fg_color=("gray82", "gray28"), corner_radius=0,
        ).grid(row=0, column=0, sticky="sew")

        # ── Scrollable body ───────────────────────────────────────────────
        scroll = ctk.CTkScrollableFrame(
            self, corner_radius=0, fg_color="transparent",
        )
        scroll.grid(row=1, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)
        scroll.grid_columnconfigure(1, weight=1)

        # Two columns — in RTL column 0 is the right column (reading-start)
        col_a = ctk.CTkFrame(scroll, fg_color="transparent")
        col_b = ctk.CTkFrame(scroll, fg_color="transparent")

        if is_rtl():
            col_a.grid(row=0, column=0, sticky="nsew",
                       padx=(PAD, PAD // 2), pady=PAD)
            col_b.grid(row=0, column=1, sticky="nsew",
                       padx=(PAD // 2, PAD), pady=PAD)
        else:
            col_a.grid(row=0, column=0, sticky="nsew",
                       padx=(PAD, PAD // 2), pady=PAD)
            col_b.grid(row=0, column=1, sticky="nsew",
                       padx=(PAD // 2, PAD), pady=PAD)

        self._build_lang_card(col_a)
        self._build_theme_card(col_a)
        self._build_mode_card(col_b)
        self._build_about_card(col_b)

    # ── Language ──────────────────────────────────────────────────────────

    def _build_lang_card(self, parent):
        inner = self._card(parent, t("set_lang"))
        seg = ctk.CTkSegmentedButton(
            inner,
            values=["English", "العربية"],
            command=self._lang_changed,
            font=ctk.CTkFont("Segoe UI", 13),
            height=40,
        )
        seg.set("English" if prefs["lang"] == "en" else "العربية")
        seg.pack(anchor=R.anchor_start())

    def _lang_changed(self, value: str):
        code = "en" if value == "English" else "ar"
        prefs["lang"] = code
        prefs.save()
        if self._on_lang:
            self._on_lang(code)

    # ── Theme ─────────────────────────────────────────────────────────────

    def _build_theme_card(self, parent):
        """Clean swatch cards — no radio buttons, no duplicates."""
        inner = self._card(parent, t("set_theme"))
        current = prefs["theme"]

        for tid, label_text, colour in THEMES:
            active = (tid == current)

            card = ctk.CTkFrame(
                inner,
                fg_color=colour if active else ("gray85", "gray20"),
                corner_radius=10,
                cursor="hand2",
            )
            card.pack(fill="x", pady=(0, 8))

            # Layout inside the swatch card (always LTR visually — it's a colour card)
            dot = ctk.CTkFrame(
                card, width=18, height=18,
                corner_radius=9, fg_color=colour,
            )
            dot.pack(side="left", padx=(12, 6), pady=10)

            lbl = ctk.CTkLabel(
                card, text=label_text,
                font=ctk.CTkFont("Segoe UI", 12,
                                  "bold" if active else "normal"),
                text_color="white" if active else ("gray20", "gray85"),
                anchor="w",
            )
            lbl.pack(side="left", pady=10)

            check = ctk.CTkLabel(
                card, text="✓" if active else "",
                font=ctk.CTkFont("Segoe UI", 14, "bold"),
                text_color="white", width=28,
            )
            check.pack(side="right", padx=(0, 10))

            for w in (card, dot, lbl, check):
                w.bind("<Button-1>",
                       lambda _, t=tid: self._theme_changed(t))

    def _theme_changed(self, tid: str):
        prefs["theme"] = tid
        prefs.save()
        if self._on_theme:
            self._on_theme(tid)

    # ── Appearance ────────────────────────────────────────────────────────

    def _build_mode_card(self, parent):
        inner = self._card(parent, t("set_mode"))

        values   = [t(key) for _, key in MODES]
        mode_map = {t(key): mode for mode, key in MODES}
        rev_map  = {mode: t(key) for mode, key in MODES}

        seg = ctk.CTkSegmentedButton(
            inner, values=values,
            command=lambda v: self._mode_changed(mode_map.get(v, "dark")),
            font=ctk.CTkFont("Segoe UI", 12),
            height=40,
        )
        saved = prefs.get("appearance", "dark")
        seg.set(rev_map.get(saved, values[0]))
        seg.pack(anchor=R.anchor_start())

    def _mode_changed(self, mode: str):
        prefs["appearance"] = mode
        prefs.save()
        ctk.set_appearance_mode(mode)

    # ── About ─────────────────────────────────────────────────────────────

    def _build_about_card(self, parent):
        inner = self._card(parent, t("set_about"))
        ctk.CTkLabel(
            inner, text=t("about_body"),
            font=ctk.CTkFont("Segoe UI", 12),
            justify=R.justify(),
            anchor=R.anchor_start(),
        ).pack(anchor=R.anchor_start())

    # ── Card helper ───────────────────────────────────────────────────────

    def _card(self, parent, title: str) -> ctk.CTkFrame:
        outer = ctk.CTkFrame(parent, corner_radius=12)
        outer.pack(fill="x", pady=(0, PAD))

        ctk.CTkLabel(
            outer, text=title,
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            anchor=R.anchor_start(),
        ).pack(anchor=R.anchor_start(), padx=PAD, pady=(12, 0))

        ctk.CTkFrame(
            outer, height=1, fg_color=("gray85", "gray30"), corner_radius=0,
        ).pack(fill="x", padx=PAD, pady=(6, 0))

        inner = ctk.CTkFrame(outer, fg_color="transparent")
        inner.pack(fill="both", padx=PAD, pady=(10, 14))
        return inner
