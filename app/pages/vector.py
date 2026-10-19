"""
pages/vector.py  –  Vector Export page

RTL rules (Material Design 3 / Apple HIG):
  • Every row starts from the reading-start edge (right in Arabic, left in English).
  • Radio buttons and checkboxes: the circle/box is on the READING-START side,
    text follows toward the reading-end side. In Arabic: ○ on the right, text to left.
  • Icons come before their label in reading order (so on the right in Arabic).
  • File paths, DPI numbers, folder paths stay LTR always.
  • Progress bar fills from reading-start to reading-end.
  • The header title is aligned to the reading-start edge.
  • Content area has proper top padding so it never overlaps the header.
"""

import glob
import os
import queue
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk

from app.core        import gs, notify, rtl as R
from app.core.prefs  import prefs
from app.core.strings import t, is_rtl

PRESETS = [
    ("q_screen",  72),
    ("q_web",    150),
    ("q_print",  300),
    ("q_hires",  600),
]
PAD = 16


class VectorPage(ctk.CTkFrame):

    def __init__(self, master, shell=None, **kw):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kw)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)   # row 1 = body; row 0 = header; row 2 = bar

        self._shell       = shell
        self._files: list[str] = []
        self._busy        = False
        self._cancel      = False
        self._last_out: str | None = None
        self._q: queue.Queue = queue.Queue()
        self._gs_exe      = gs.find()
        self._prog_total  = 0

        self._build()
        self._update_gs_badge()
        self.after(120, self._drain)

    # ── Build ──────────────────────────────────────────────────────────────

    def _build(self):
        self._build_header()
        self._build_body()
        self._build_action_bar()

    # ── Header ─────────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = ctk.CTkFrame(self, corner_radius=0, height=70)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)

        # Title on reading-start side
        title_col  = 2 if is_rtl() else 0
        badge_col  = 0 if is_rtl() else 2
        title_anch = "e" if is_rtl() else "w"
        badge_anch = "w" if is_rtl() else "e"

        ctk.CTkLabel(
            hdr, text=t("vec_title"),
            font=ctk.CTkFont("Segoe UI", 22, "bold"),
            anchor=title_anch,
        ).grid(row=0, column=title_col, padx=(PAD, 10),
               pady=(14, 2), sticky=title_anch)

        ctk.CTkLabel(
            hdr, text=t("vec_subtitle"),
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=("gray40", "gray60"),
            anchor=title_anch,
        ).grid(row=1, column=title_col, padx=(PAD, 10),
               pady=(0, 10), sticky=title_anch)

        # GS badge on reading-end side
        self._gs_badge = ctk.CTkLabel(
            hdr, text="",
            font=ctk.CTkFont("Segoe UI", 10),
            anchor=badge_anch,
        )
        self._gs_badge.grid(row=0, column=badge_col, rowspan=2,
                            padx=PAD, sticky=badge_anch)

        # Thin separator under header
        ctk.CTkFrame(
            self, height=1, fg_color=("gray82", "gray28"), corner_radius=0,
        ).grid(row=0, column=0, sticky="sew")   # sticks to bottom of row 0

    # ── Scrollable body ─────────────────────────────────────────────────────

    def _build_body(self):
        scroll = ctk.CTkScrollableFrame(
            self, corner_radius=0, fg_color="transparent",
        )
        scroll.grid(row=1, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        # ── Files card (full width) ──────────────────────────────────────
        self._build_files_card(scroll)

        # ── Format + Quality side-by-side row ────────────────────────────
        two_col = ctk.CTkFrame(scroll, fg_color="transparent")
        two_col.pack(fill="x", padx=PAD, pady=(0, PAD))
        two_col.grid_columnconfigure(0, weight=1)
        two_col.grid_columnconfigure(1, weight=2)
        self._build_format_card(two_col)
        self._build_quality_card(two_col)
        # ── Save card (full width) ───────────────────────────────────────
        self._build_save_card(scroll)

        # ── Log card (full width) ────────────────────────────────────────
        self._build_log_card(scroll)
    # ── Card: Files ────────────────────────────────────────────────────────

    def _build_files_card(self, parent):
        # TOP_PAD gives breathing room between the header and first card
        inner = self._card(parent, t("s1_files"), pack=True, top_pad=PAD)

        # Button row — buttons flow from reading-start edge
        br = ctk.CTkFrame(inner, fg_color="transparent")
        br.pack(fill="x", pady=(0, 8))

        self._btn_add    = ctk.CTkButton(br, text=t("btn_add_files"),  width=130,
                                          command=self._add_files)
        self._btn_folder = ctk.CTkButton(br, text=t("btn_add_folder"), width=130,
                                          **self._secondary_btn(),
                                          command=self._add_folder)
        self._btn_rm     = ctk.CTkButton(br, text=t("btn_remove"),     width=120,
                                          **self._ghost_btn(),
                                          command=self._remove_sel)
        self._btn_clear  = ctk.CTkButton(br, text=t("btn_clear"),      width=110,
                                          **self._ghost_btn(),
                                          command=self._clear)

        # Pack buttons from reading-start
        for b in (self._btn_add, self._btn_folder, self._btn_rm, self._btn_clear):
            b.pack(side=R.start(), padx=(0, 6))

        self._count_lbl = ctk.CTkLabel(
            br, text=t("n_files_0"),
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=("gray40", "gray60"),
        )
        self._count_lbl.pack(side=R.end(), padx=4)

        self._file_box = ctk.CTkTextbox(
            inner, height=130, state="disabled",
            font=ctk.CTkFont("Consolas", 11),
            wrap="none",
        )
        self._file_box.pack(fill="x")

    # ── Card: Format ──────────────────────────────────────────────────────

    def _build_format_card(self, parent):
        inner = self._card(parent, t("s2_format"), grid_col=0 if not is_rtl() else 1)
        self._fmt = ctk.StringVar(value=prefs["fmt"])

        # Radio buttons: in RTL the circle is on the right, text on left.
        # CTkRadioButton naturally places the circle on the left in LTR.
        # For RTL we use a custom row that puts circle right and text left.
        for val, key in (("png", "fmt_png"), ("jpg", "fmt_jpg")):
            self._radio_row(inner, t(key), self._fmt, val,
                            command=self._fmt_changed)

        # ── PNG section (background choice) ─────────────────────────────
        self._png_section = ctk.CTkFrame(inner, fg_color="transparent")
        R.section_label(self._png_section, t("png_bg_label")).pack(
            anchor=R.anchor_start(), pady=(8, 4))
        self._bg = ctk.StringVar(value=prefs["bg"])
        # Clean radio rows — no emoji squares
        self._radio_row(self._png_section, t("adv_bg_trans"), self._bg, "transparent")
        self._radio_row(self._png_section, t("adv_bg_white"), self._bg, "white")
        R.hint_label(self._png_section, t("fmt_png_hint"),
                     wraplength=200).pack(anchor=R.anchor_start(), pady=(6, 0))

        # ── JPG section (quality slider) ─────────────────────────────────
        self._jpg_section = ctk.CTkFrame(inner, fg_color="transparent")

        # Label row: "JPG Quality:" above the slider
        R.section_label(self._jpg_section, t("jpg_q_label")).pack(
            anchor=R.anchor_start(), pady=(8, 6))

        # Slider row: value number on the reading-start side, slider extends away
        sl_row = ctk.CTkFrame(self._jpg_section, fg_color="transparent")
        sl_row.pack(fill="x", anchor=R.anchor_start())

        self._jpg_q      = ctk.IntVar(value=prefs["jpg_quality"])
        self._jpg_lbl    = ctk.CTkLabel(
            sl_row, text=str(prefs["jpg_quality"]),
            width=36, font=ctk.CTkFont("Segoe UI", 13, "bold"),
        )
        self._jpg_slider = ctk.CTkSlider(
            sl_row, from_=0 if not is_rtl() else 100,
            to=100 if not is_rtl() else 0,
            variable=self._jpg_q, width=180,
        )
        if is_rtl():
            # RTL: number on right (reading-start), slider extends left
            self._jpg_lbl.pack(side="right", padx=(0, 8))
            self._jpg_slider.pack(side="right")
        else:
            self._jpg_slider.pack(side="left")
            self._jpg_lbl.pack(side="left", padx=(8, 0))

        self._jpg_q.trace_add("write",
            lambda *_: self._jpg_lbl.configure(text=str(self._jpg_q.get())))

        R.hint_label(self._jpg_section, t("jpg_q_hint"),
                     wraplength=210).pack(anchor=R.anchor_start(), pady=(6, 0))

        self._fmt_changed()   # show the right section immediately

    # ── Card: Quality ─────────────────────────────────────────────────────

    def _build_quality_card(self, parent):
        inner = self._card(parent, t("s3_quality"), grid_col=1 if not is_rtl() else 0)

        # Preset buttons — flow from reading-start
        pr = ctk.CTkFrame(inner, fg_color="transparent")
        pr.pack(anchor=R.anchor_start(), pady=(0, 8))
        self._dpi_var = ctk.IntVar(value=prefs["dpi"])
        self._preset_btns: list[tuple[ctk.CTkButton, int]] = []

        for key, dpi in PRESETS:
            b = ctk.CTkButton(
                pr, text=t(key), width=88, height=50,
                corner_radius=8, font=ctk.CTkFont("Segoe UI", 10),
                command=lambda d=dpi: self._set_preset(d),
            )
            b.pack(side=R.start(), padx=(0, 6))
            self._preset_btns.append((b, dpi))

        self._refresh_preset_colors()

        R.hint_label(inner, t("q_hint"),
                     wraplength=320).pack(anchor=R.anchor_start(), pady=(0, 8))

        # Custom DPI row
        # RTL: [entry field] [label text]  (entry is reading-start = right)
        # LTR: [label text] [entry field]
        dpi_row = ctk.CTkFrame(inner, fg_color="transparent")
        dpi_row.pack(anchor=R.anchor_start(), pady=(0, 10))

        lbl = ctk.CTkLabel(dpi_row, text=t("q_custom_label"),
                           font=ctk.CTkFont("Segoe UI", 11))
        self._dpi_entry = ctk.CTkEntry(dpi_row, width=78,
                                        placeholder_text="300",
                                        justify="left")   # numbers always LTR
        self._dpi_entry.insert(0, str(prefs["dpi"]))
        self._dpi_entry.bind("<KeyRelease>", lambda _: self._on_custom_dpi())

        if is_rtl():
            # Reading order RTL: ← label ← [300] (entry on right = reading-start)
            self._dpi_entry.pack(side="right", padx=(0, 8))
            lbl.pack(side="right")
        else:
            lbl.pack(side="left", padx=(0, 8))
            self._dpi_entry.pack(side="left")

        # Separator
        ctk.CTkFrame(inner, height=1, fg_color=("gray85", "gray30"),
                     corner_radius=0).pack(fill="x", pady=(0, 10))

        # Multi-page checkbox
        R.section_label(inner, t("pages_label")).pack(
            anchor=R.anchor_start())
        self._all_pages = ctk.BooleanVar(value=prefs["all_pages"])
        self._check_row(inner, t("pages_check"), self._all_pages)
        R.hint_label(inner, t("pages_hint")).pack(
            anchor=R.anchor_start(), pady=(2, 10))

        # Filename suffix
        R.section_label(inner, t("suffix_label")).pack(
            anchor=R.anchor_start())
        # Suffix row: entry field + hint
        # RTL: [entry] [مثال:] [_web → logo_web.png]  (entry on reading-start right)
        # LTR: [entry] [e.g.] [_web → logo_web.png]
        suf_row = ctk.CTkFrame(inner, fg_color="transparent")
        suf_row.pack(anchor=R.anchor_start(), pady=(4, 0))
        self._suffix = ctk.StringVar(value=prefs["suffix"])
        suf_entry = ctk.CTkEntry(suf_row, textvariable=self._suffix,
                                  width=110, placeholder_text="_web",
                                  justify="left")
        # "مثال:" / "e.g." label
        suf_lbl = ctk.CTkLabel(suf_row, text=t("suffix_hint"),
                                font=ctk.CTkFont("Segoe UI", 10),
                                text_color=("gray40", "gray60"))
        # The example itself is always LTR (file names)
        suf_ex = ctk.CTkLabel(suf_row, text=t("suffix_hint_ex"),
                               font=ctk.CTkFont("Consolas", 10),
                               text_color=("gray40", "gray60"))
        if is_rtl():
            # Right → left: [entry] [مثال:] [_web → logo_web.png]
            suf_entry.pack(side="right", padx=(0, 10))
            suf_lbl.pack(side="right", padx=(0, 4))
            suf_ex.pack(side="right")
        else:
            suf_entry.pack(side="left", padx=(0, 10))
            suf_lbl.pack(side="left", padx=(0, 4))
            suf_ex.pack(side="left")

    # ── Card: Save ────────────────────────────────────────────────────────

    def _build_save_card(self, parent):
        inner = self._card(parent, t("s4_save"), pack=True)
        self._out_mode = ctk.StringVar(value=prefs["out_mode"])

        self._radio_row(inner, t("save_beside"), self._out_mode, "beside",
                        command=self._save_mode_changed, pady=(0, 10))

        # Custom folder row
        # RTL: [Browse] [entry] [في مجلد محدد:] [○]
        # LTR: [○] [Save to folder:] [entry] [Browse]
        cf_row = ctk.CTkFrame(inner, fg_color="transparent")
        cf_row.pack(fill="x")

        self._rb_custom = ctk.CTkRadioButton(
            cf_row, text="",
            variable=self._out_mode, value="custom",
            command=self._save_mode_changed,
            width=20,
        )
        custom_lbl = ctk.CTkLabel(
            cf_row, text=t("save_custom"),
            font=ctk.CTkFont("Segoe UI", 12),
            anchor=R.text_anchor(),
            cursor="hand2",
        )
        custom_lbl.bind("<Button-1>",
                        lambda _: (self._out_mode.set("custom"), self._save_mode_changed()))

        self._out_entry = ctk.CTkEntry(
            cf_row, width=260,
            placeholder_text="C:\\Output\\folder",
            justify="left",
        )
        self._out_entry.insert(0, prefs["last_out_dir"])

        self._browse_btn = ctk.CTkButton(
            cf_row, text=t("btn_browse"), width=100,
            **self._secondary_btn(),
            command=self._browse_out,
        )

        if is_rtl():
            self._rb_custom.pack(side="right", padx=(4, 0))
            custom_lbl.pack(side="right", padx=(0, 6))
            self._browse_btn.pack(side="left", padx=(0, 6))
            self._out_entry.pack(side="left", fill="x", expand=True)
        else:
            self._rb_custom.pack(side="left", padx=(0, 4))
            custom_lbl.pack(side="left", padx=(0, 6))
            self._out_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
            self._browse_btn.pack(side="left")

        self._save_mode_changed()

    # ── Card: Log ─────────────────────────────────────────────────────────

    def _build_log_card(self, parent):
        inner = self._card(parent, t("log_title"), pack=True)
        self._log_box = ctk.CTkTextbox(
            inner, height=100, state="disabled",
            font=ctk.CTkFont("Consolas", 11),
            wrap="word",
        )
        self._log_box.pack(fill="x")

    # ── Action bar (pinned to bottom) ──────────────────────────────────────

    def _build_action_bar(self):
        bar = ctk.CTkFrame(self, corner_radius=0, height=64)
        bar.grid(row=2, column=0, sticky="ew")
        bar.grid_propagate(False)

        # Separator above action bar
        ctk.CTkFrame(
            bar, height=1, fg_color=("gray82", "gray28"), corner_radius=0,
        ).pack(fill="x", side="top")

        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="both", expand=True)

        self._convert_btn = ctk.CTkButton(
            inner, text=t("btn_convert"),
            width=150, height=42,
            font=ctk.CTkFont("Segoe UI", 14, "bold"),
            command=self._convert,
        )
        self._cancel_btn = ctk.CTkButton(
            inner, text=t("btn_cancel"),
            width=110, height=42,
            state="disabled",
            **self._secondary_btn(),
            command=self._do_cancel,
        )
        self._open_btn = ctk.CTkButton(
            inner, text=t("btn_open"),
            width=180, height=42,
            state="disabled",
            **self._secondary_btn(),
            command=self._open_out,
        )
        self._status_lbl = ctk.CTkLabel(
            inner, text=t("status_ready"),
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=("gray40", "gray60"),
            anchor=R.text_anchor(),
        )
        self._prog = ctk.CTkProgressBar(inner, height=6, corner_radius=3)
        self._prog.set(0)

        # Pack from reading-start
        for w in (self._convert_btn, self._cancel_btn, self._open_btn):
            w.pack(side=R.start(),
                   padx=(PAD, 0) if w is self._convert_btn else (6, 0),
                   pady=10)
        self._status_lbl.pack(side=R.start(), padx=(10, 0), pady=10)
        self._prog.pack(side=R.end(), padx=PAD, pady=10,
                        fill="x", expand=True)

    # ── Widget factories ───────────────────────────────────────────────────

    def _card(self, parent, title: str,
              pack=False, grid_col: int | None = None,
              top_pad: int = 0) -> ctk.CTkFrame:
        outer = ctk.CTkFrame(parent, corner_radius=12)

        if pack:
            outer.pack(fill="x", padx=PAD, pady=(top_pad, PAD))
        else:
            padx = (0, PAD // 2) if grid_col == 0 else (PAD // 2, 0)
            outer.grid(row=0, column=grid_col, sticky="nsew", padx=padx, pady=(top_pad, PAD))

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

    def _radio_row(self, parent, text: str, variable, value,
                   command=None, pady=(0, 4)):
        """
        Build a proper RTL-aware radio button row.
        In LTR: ○  Text
        In RTL: Text  ○   (circle on the right = reading-start in RTL)
        CTkRadioButton always places the circle on the left. For RTL we put the
        circle in a separate row and anchor text to the right.
        """
        if not is_rtl():
            ctk.CTkRadioButton(
                parent, text=text,
                variable=variable, value=value,
                command=command,
                font=ctk.CTkFont("Segoe UI", 12),
            ).pack(anchor="w", pady=pady)
        else:
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(anchor="e", pady=pady, fill="x")
            # Text on the left (reading-end), radio circle on the right (reading-start)
            ctk.CTkLabel(
                row, text=text,
                font=ctk.CTkFont("Segoe UI", 12),
                anchor="e",
            ).pack(side="left", fill="x", expand=True, padx=(0, 8))
            ctk.CTkRadioButton(
                row, text="",
                variable=variable, value=value,
                command=command,
                width=24,
            ).pack(side="right")

    def _check_row(self, parent, text: str, variable, pady=(0, 4)):
        """
        Build a proper RTL-aware checkbox row.
        In LTR: ☐  Text
        In RTL: Text  ☐   (box on the right = reading-start in RTL)
        """
        if not is_rtl():
            ctk.CTkCheckBox(
                parent, text=text,
                variable=variable,
                font=ctk.CTkFont("Segoe UI", 11),
            ).pack(anchor="w", pady=pady)
        else:
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(anchor="e", pady=pady, fill="x")
            ctk.CTkLabel(
                row, text=text,
                font=ctk.CTkFont("Segoe UI", 11),
                anchor="e",
            ).pack(side="left", fill="x", expand=True, padx=(0, 8))
            ctk.CTkCheckBox(
                row, text="",
                variable=variable,
                width=24,
            ).pack(side="right")

    def _secondary_btn(self) -> dict:
        return dict(fg_color=("gray80", "gray25"),
                    hover_color=("gray70", "gray35"),
                    text_color=("gray10", "gray90"))

    def _ghost_btn(self) -> dict:
        return dict(fg_color=("gray85", "gray20"),
                    hover_color=("gray75", "gray30"),
                    text_color=("gray10", "gray90"))

    # ── State helpers ──────────────────────────────────────────────────────

    def _update_gs_badge(self):
        if self._gs_exe:
            ver = gs.get_version(self._gs_exe)
            self._gs_badge.configure(
                text=t("gs_ok", ver=ver),
                text_color=("#16A34A", "#4ADE80"),
            )
        else:
            self._gs_badge.configure(
                text=t("gs_missing"),
                text_color=("#DC2626", "#F87171"),
            )

    def _refresh_list(self):
        self._file_box.configure(state="normal")
        self._file_box.delete("1.0", "end")
        for p in self._files:
            self._file_box.insert("end", p + "\n")
        self._file_box.configure(state="disabled")
        n = len(self._files)
        self._count_lbl.configure(
            text=t("n_files_0") if n == 0 else t("n_files_n", n=n)
        )

    def _log(self, msg: str):
        self._log_box.configure(state="normal")
        self._log_box.insert("end", msg + "\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _set_busy(self, busy: bool):
        self._busy = busy
        s = "disabled" if busy else "normal"
        for w in (self._btn_add, self._btn_folder, self._btn_rm, self._btn_clear,
                  self._convert_btn, self._out_entry, self._browse_btn,
                  self._dpi_entry):
            w.configure(state=s)
        for btn, _ in self._preset_btns:
            btn.configure(state=s)
        self._cancel_btn.configure(state="normal" if busy else "disabled")

    def _refresh_preset_colors(self):
        cur = self._dpi_var.get()
        for btn, dpi in self._preset_btns:
            if dpi == cur:
                btn.configure(
                    fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"],
                    text_color=("white", "white"),
                )
            else:
                btn.configure(**self._ghost_btn())

    def _set_preset(self, dpi: int):
        self._dpi_var.set(dpi)
        self._dpi_entry.delete(0, "end")
        self._dpi_entry.insert(0, str(dpi))
        self._refresh_preset_colors()

    def _on_custom_dpi(self):
        self._dpi_var.set(0)
        self._refresh_preset_colors()

    def _fmt_changed(self):
        if self._fmt.get() == "png":
            self._jpg_section.pack_forget()
            self._png_section.pack(fill="x", pady=(4, 0))
        else:
            self._png_section.pack_forget()
            self._jpg_section.pack(fill="x", pady=(4, 0))

    def _save_mode_changed(self):
        if self._out_mode.get() == "beside":
            self._out_entry.configure(state="disabled")
            self._browse_btn.configure(state="disabled")
        else:
            self._out_entry.configure(state="normal")
            self._browse_btn.configure(state="normal")

    def _is_window_focused(self) -> bool:
        try:
            return bool(self._shell and self._shell.focus_displayof() is not None)
        except Exception:
            return True

    # ── File operations ───────────────────────────────────────────────────

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title="Select EPS / AI files",
            filetypes=[("Vector files", "*.eps *.ai *.EPS *.AI"),
                       ("All files", "*.*")],
        )
        if paths:
            self._ingest(list(paths))

    def _add_folder(self):
        folder = filedialog.askdirectory(title="Choose folder with EPS / AI files")
        if not folder:
            return
        found: list[str] = []
        for ext in ("*.eps", "*.ai", "*.EPS", "*.AI"):
            found.extend(glob.glob(os.path.join(folder, ext)))
        if not found:
            self._log(t("log_no_eps"))
        else:
            self._ingest(sorted(found))

    def _ingest(self, paths: list[str]):
        existing = set(self._files)
        added = 0
        for p in paths:
            p = os.path.abspath(p)
            if p in existing:
                continue
            if os.path.splitext(p)[1].lower() not in (".eps", ".ai"):
                continue
            self._files.append(p)
            existing.add(p)
            added += 1
        self._refresh_list()
        if added:
            self._log(t("log_added", n=added))

    def _remove_sel(self):
        if self._files:
            name = os.path.basename(self._files.pop())
            self._refresh_list()
            self._log(f"Removed: {name}")

    def _clear(self):
        self._files.clear()
        self._refresh_list()

    def _browse_out(self):
        d = filedialog.askdirectory(title="Choose output folder")
        if d:
            self._out_entry.configure(state="normal")
            self._out_entry.delete(0, "end")
            self._out_entry.insert(0, d)
            self._out_mode.set("custom")
            self._save_mode_changed()

    def _open_out(self):
        if self._last_out and os.path.isdir(self._last_out):
            try:
                os.startfile(self._last_out)
            except Exception:
                pass

    def _do_cancel(self):
        self._cancel = True

    # ── Conversion ────────────────────────────────────────────────────────

    def _convert(self):
        if self._busy:
            return
        if not self._files:
            messagebox.showinfo("Studio Tools", t("err_no_files"))
            return

        exe = self._gs_exe or gs.find()
        if not exe:
            messagebox.showerror("Studio Tools", t("err_gs"))
            return

        try:
            dpi = int(float(self._dpi_entry.get()))
            assert 1 <= dpi <= 6000
        except Exception:
            messagebox.showerror("Studio Tools", t("err_dpi"))
            return

        out_dir: str | None = None
        if self._out_mode.get() == "custom":
            out_dir = self._out_entry.get().strip()
            if not out_dir:
                messagebox.showerror("Studio Tools", t("err_no_outdir"))
                return
            os.makedirs(out_dir, exist_ok=True)

        fmt       = self._fmt.get()
        jpg_q     = int(self._jpg_q.get())
        all_pages = bool(self._all_pages.get())
        bg_white  = (self._bg.get() == "white") if fmt == "png" else True
        suffix    = self._suffix.get().strip()

        prefs["fmt"]          = fmt
        prefs["dpi"]          = dpi
        prefs["jpg_quality"]  = jpg_q
        prefs["bg"]           = self._bg.get()
        prefs["all_pages"]    = all_pages
        prefs["suffix"]       = suffix
        prefs["out_mode"]     = self._out_mode.get()
        if out_dir:
            prefs["last_out_dir"] = out_dir
        prefs.save()

        self._cancel      = False
        self._last_out    = out_dir
        self._prog_total  = len(self._files)
        self._set_busy(True)
        self._prog.set(0)
        self._status_lbl.configure(
            text=t("status_conv", i=0, n=self._prog_total, name="…"))

        threading.Thread(
            target=self._worker,
            args=(exe, list(self._files), fmt, dpi, jpg_q,
                  all_pages, bg_white, suffix, out_dir),
            daemon=True,
        ).start()

    def _worker(self, exe, files, fmt, dpi, jpg_q, all_pages, bg_white, suffix, out_dir):
        total = len(files)
        ok = fail = 0
        first_out = None

        for i, src in enumerate(files, start=1):
            if self._cancel:
                self._q.put(("status", t("status_cancel", ok=ok, fail=fail)))
                self._q.put(("done", (ok, fail)))
                return

            name     = os.path.basename(src)
            base     = os.path.splitext(name)[0] + suffix
            dst_base = (os.path.join(out_dir, base) if out_dir
                        else os.path.join(os.path.dirname(src), base))
            if first_out is None:
                first_out = os.path.dirname(dst_base) or "."

            self._q.put(("status", t("status_conv", i=i, n=total, name=name)))
            try:
                outs = gs.convert(exe, src, dst_base, fmt, dpi,
                                  jpg_q, all_pages, bg_white)
                ok += 1
                self._q.put(("log",
                             "✓  " + name + "  →  " +
                             ", ".join(os.path.basename(o) for o in outs)))
            except Exception as e:
                fail += 1
                self._q.put(("log", f"✗  {name}  —  {e}"))

            self._q.put(("progress", i / total))

        self._last_out = out_dir or first_out
        self._q.put(("status", t("status_done", ok=ok, fail=fail)))
        self._q.put(("done", (ok, fail)))

    def _drain(self):
        try:
            while True:
                kind, data = self._q.get_nowait()
                if kind == "log":
                    self._log(data)
                elif kind == "status":
                    self._status_lbl.configure(text=data)
                elif kind == "progress":
                    self._prog.set(data)
                elif kind == "done":
                    ok, fail = data or (0, 0)
                    self._prog.set(1)
                    self._set_busy(False)
                    self._open_btn.configure(
                        state="normal" if self._last_out else "disabled")

                    if not self._is_window_focused():
                        if is_rtl():
                            title = "Studio Tools — اكتمل التصدير ✓"
                            msg   = (f"تم تصدير {ok} ملف" +
                                     (f"،  {fail} فشل" if fail else "") +
                                     "\nانقر للعودة إلى التطبيق")
                        else:
                            title = "Studio Tools — Done ✓"
                            msg   = (f"{ok} file(s) exported" +
                                     (f",  {fail} failed" if fail else "") +
                                     "\nClick to return to Studio Tools")
                        threading.Thread(
                            target=notify.send, args=(title, msg), daemon=True,
                        ).start()

        except queue.Empty:
            pass
        self.after(120, self._drain)
