"""
pages/vector.py  –  Vector Export page

UX improvements in this version:
  - 2-column layout (format left, quality right) to reduce scrolling
  - Real determinate progress bar (0 → 100%) instead of bouncing animation
  - Format change immediately enables/disables dependent options (PNG bg, JPG quality)
  - Custom DPI entry clears preset selection; preset click fills custom DPI
  - All interactive widgets properly disabled/enabled during conversion
  - RTL layout when Arabic is active
  - Natural button labels with icons
  - PNG background option only shown when PNG is selected
  - JPG quality slider only shown when JPG is selected
"""

import glob
import os
import queue
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk

from app.core import gs
from app.core.prefs   import prefs
from app.core.strings import t, is_rtl

PRESETS = [
    ("q_screen",  72),
    ("q_web",    150),
    ("q_print",  300),
    ("q_hires",  600),
]
PAD = 16


class VectorPage(ctk.CTkFrame):

    def __init__(self, master, **kw):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kw)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._files: list[str] = []
        self._busy  = False
        self._cancel = False
        self._last_out: str | None = None
        self._q: queue.Queue = queue.Queue()
        self._gs_exe = gs.find()
        self._prog_total = 0

        self._build()
        self._update_gs_badge()
        self.after(120, self._drain)

    # ── Build ──────────────────────────────────────────────────────────────

    def _build(self):
        self._build_header()
        self._build_body()
        self._build_bottom_bar()

    def _build_header(self):
        hdr = ctk.CTkFrame(self, corner_radius=0, height=64)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)

        anchor_side = "e" if is_rtl() else "w"
        text_side   = "right" if is_rtl() else "left"

        ctk.CTkLabel(
            hdr, text=t("vec_title"),
            font=ctk.CTkFont("Segoe UI", 22, "bold"),
            anchor=anchor_side,
        ).grid(row=0, column=0, padx=(PAD, 10), pady=(12, 2), sticky=anchor_side)

        ctk.CTkLabel(
            hdr, text=t("vec_subtitle"),
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=("gray40", "gray60"),
            anchor=anchor_side,
        ).grid(row=1, column=0, padx=(PAD, 10), pady=(0, 10), sticky=anchor_side)

        self._gs_badge = ctk.CTkLabel(
            hdr, text="",
            font=ctk.CTkFont("Segoe UI", 10),
        )
        # Badge on the opposite side from title
        badge_col = 0 if is_rtl() else 2
        badge_sticky = "w" if is_rtl() else "e"
        self._gs_badge.grid(row=0, column=badge_col, rowspan=2,
                            padx=PAD, sticky=badge_sticky)

    def _build_body(self):
        scroll = ctk.CTkScrollableFrame(
            self, corner_radius=0, fg_color="transparent",
        )
        scroll.grid(row=1, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        # ── Row 1: Files card (full width) ───────────────────────────────
        self._build_card_files(scroll)

        # ── Row 2: Format (left) + Quality (right) side-by-side ──────────
        row2 = ctk.CTkFrame(scroll, fg_color="transparent")
        row2.pack(fill="x", padx=PAD, pady=(0, PAD))
        row2.grid_columnconfigure(0, weight=1)
        row2.grid_columnconfigure(1, weight=2)

        self._build_card_format(row2)
        self._build_card_quality(row2)

        # ── Row 3: Save location (full width) ────────────────────────────
        self._build_card_save(scroll)

        # ── Row 4: Log (full width) ───────────────────────────────────────
        self._build_card_log(scroll)

    # Card: Files ────────────────────────────────────────────────────────────
    def _build_card_files(self, parent):
        card = self._card_outer(parent)
        self._card_title(card, t("s1_files"))
        inner = self._card_inner(card)

        # Buttons row — respects RTL
        br = ctk.CTkFrame(inner, fg_color="transparent")
        br.pack(fill="x", pady=(0, 8))

        btns = [
            ("_btn_add",    t("btn_add_files"),  True,  self._add_files),
            ("_btn_folder", t("btn_add_folder"), False, self._add_folder),
            ("_btn_rm",     t("btn_remove"),      False, self._remove_sel),
            ("_btn_clear",  t("btn_clear"),       False, self._clear),
        ]
        pack_side = "right" if is_rtl() else "left"
        for attr, text, primary, cmd in btns:
            btn = ctk.CTkButton(
                br, text=text, width=130, height=34,
                command=cmd,
                fg_color=("gray80","gray25") if not primary else None,
                hover_color=("gray70","gray35") if not primary else None,
                text_color=("gray10","gray90") if not primary else None,
            )
            btn.pack(side=pack_side, padx=(0, 6) if pack_side == "left" else (6, 0))
            setattr(self, attr, btn)

        self._count_lbl = ctk.CTkLabel(
            br, text=t("n_files_0"),
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=("gray40","gray60"),
        )
        count_side = "left" if is_rtl() else "right"
        self._count_lbl.pack(side=count_side, padx=8)

        self._file_box = ctk.CTkTextbox(
            inner, height=140, state="disabled",
            font=ctk.CTkFont("Consolas", 11),
            wrap="none",
        )
        self._file_box.pack(fill="x")

    # Card: Format ────────────────────────────────────────────────────────────
    def _build_card_format(self, parent):
        card = self._card_outer(parent, grid_col=0 if not is_rtl() else 1)
        self._card_title(card, t("s2_format"))
        inner = self._card_inner(card)

        self._fmt = ctk.StringVar(value=prefs["fmt"])
        anchor = "e" if is_rtl() else "w"

        self._fmt_png_rb = ctk.CTkRadioButton(
            inner, text=t("fmt_png"),
            variable=self._fmt, value="png",
            command=self._fmt_changed,
            font=ctk.CTkFont("Segoe UI", 12),
        )
        self._fmt_png_rb.pack(anchor=anchor, pady=(0, 4))

        self._fmt_jpg_rb = ctk.CTkRadioButton(
            inner, text=t("fmt_jpg"),
            variable=self._fmt, value="jpg",
            command=self._fmt_changed,
            font=ctk.CTkFont("Segoe UI", 12),
        )
        self._fmt_jpg_rb.pack(anchor=anchor, pady=(0, 12))

        # PNG-specific: background choice (hidden when JPG)
        self._png_section = ctk.CTkFrame(inner, fg_color="transparent")
        ctk.CTkLabel(
            self._png_section,
            text=t("png_bg_label"),
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            anchor=anchor,
        ).pack(anchor=anchor, pady=(0, 4))

        self._bg = ctk.StringVar(value=prefs["bg"])
        for val, key in (("transparent", "png_bg_trans"), ("white", "png_bg_white")):
            ctk.CTkRadioButton(
                self._png_section, text=t(key),
                variable=self._bg, value=val,
                font=ctk.CTkFont("Segoe UI", 11),
            ).pack(anchor=anchor, pady=2)

        hint_lbl = ctk.CTkLabel(
            self._png_section, text=t("fmt_png_hint"),
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=("gray40","gray60"),
            wraplength=200, justify="left" if not is_rtl() else "right",
            anchor=anchor,
        )
        hint_lbl.pack(anchor=anchor, pady=(6, 0))

        # JPG-specific: quality slider (hidden when PNG)
        self._jpg_section = ctk.CTkFrame(inner, fg_color="transparent")
        ctk.CTkLabel(
            self._jpg_section,
            text=t("jpg_q_label"),
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            anchor=anchor,
        ).pack(anchor=anchor, pady=(0, 4))

        slider_row = ctk.CTkFrame(self._jpg_section, fg_color="transparent")
        slider_row.pack(anchor=anchor)
        self._jpg_q    = ctk.IntVar(value=prefs["jpg_quality"])
        self._jpg_slider = ctk.CTkSlider(
            slider_row, from_=10, to=100, variable=self._jpg_q, width=160,
        )
        self._jpg_slider.pack(side="left" if not is_rtl() else "right", padx=(0, 8))
        self._jpg_lbl = ctk.CTkLabel(
            slider_row, text=str(prefs["jpg_quality"]), width=32,
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
        )
        self._jpg_lbl.pack(side="left" if not is_rtl() else "right")
        self._jpg_q.trace_add("write",
            lambda *_: self._jpg_lbl.configure(text=str(self._jpg_q.get())))

        ctk.CTkLabel(
            self._jpg_section, text=t("jpg_q_hint"),
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=("gray40","gray60"),
            wraplength=200, justify="left" if not is_rtl() else "right",
            anchor=anchor,
        ).pack(anchor=anchor, pady=(6, 0))

        # Show the right section on startup
        self._fmt_changed()

    # Card: Quality ────────────────────────────────────────────────────────────
    def _build_card_quality(self, parent):
        card = self._card_outer(parent, grid_col=1 if not is_rtl() else 0)
        self._card_title(card, t("s3_quality"))
        inner = self._card_inner(card)

        # Preset buttons row
        preset_row = ctk.CTkFrame(inner, fg_color="transparent")
        preset_row.pack(fill="x", pady=(0, 6))

        self._dpi_var = ctk.IntVar(value=prefs["dpi"])
        self._preset_btns: list[tuple[ctk.CTkButton, int]] = []
        pack_side = "right" if is_rtl() else "left"
        for key, dpi in PRESETS:
            b = ctk.CTkButton(
                preset_row, text=t(key),
                width=90, height=52,
                corner_radius=8,
                font=ctk.CTkFont("Segoe UI", 10),
                command=lambda d=dpi: self._set_preset(d),
            )
            b.pack(side=pack_side, padx=(0, 6) if pack_side == "left" else (6, 0))
            self._preset_btns.append((b, dpi))

        self._refresh_preset_colors()

        ctk.CTkLabel(
            inner, text=t("q_hint"),
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=("gray40","gray60"),
            wraplength=300, justify="left" if not is_rtl() else "right",
        ).pack(anchor="e" if is_rtl() else "w", pady=(0, 10))

        # Custom DPI
        dpi_row = ctk.CTkFrame(inner, fg_color="transparent")
        dpi_row.pack(anchor="e" if is_rtl() else "w", pady=(0, 12))
        ctk.CTkLabel(
            dpi_row, text=t("q_custom_label"),
            font=ctk.CTkFont("Segoe UI", 11),
        ).pack(side="right" if is_rtl() else "left", padx=(0, 8))
        self._dpi_entry = ctk.CTkEntry(dpi_row, width=80,
                                        placeholder_text="300")
        self._dpi_entry.insert(0, str(prefs["dpi"]))
        self._dpi_entry.pack(side="right" if is_rtl() else "left")
        # When user types a custom DPI, deselect any preset
        self._dpi_entry.bind("<KeyRelease>", lambda _: self._on_custom_dpi())

        # Separator line
        ctk.CTkFrame(inner, height=1,
                     fg_color=("gray85","gray30"),
                     corner_radius=0).pack(fill="x", pady=(0, 10))

        # Multi-page checkbox
        self._all_pages = ctk.BooleanVar(value=prefs["all_pages"])
        ctk.CTkLabel(
            inner, text=t("pages_label"),
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            anchor="e" if is_rtl() else "w",
        ).pack(anchor="e" if is_rtl() else "w")
        ctk.CTkCheckBox(
            inner, text=t("pages_check"),
            variable=self._all_pages,
            font=ctk.CTkFont("Segoe UI", 11),
        ).pack(anchor="e" if is_rtl() else "w", pady=(4, 2))
        ctk.CTkLabel(
            inner, text=t("pages_hint"),
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=("gray40","gray60"),
            anchor="e" if is_rtl() else "w",
        ).pack(anchor="e" if is_rtl() else "w", pady=(0, 10))

        # Filename suffix
        ctk.CTkLabel(
            inner, text=t("suffix_label"),
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            anchor="e" if is_rtl() else "w",
        ).pack(anchor="e" if is_rtl() else "w")
        suffix_row = ctk.CTkFrame(inner, fg_color="transparent")
        suffix_row.pack(anchor="e" if is_rtl() else "w", pady=(4, 0))
        self._suffix = ctk.StringVar(value=prefs["suffix"])
        ctk.CTkEntry(suffix_row, textvariable=self._suffix, width=130,
                     placeholder_text="_web").pack(
            side="right" if is_rtl() else "left", padx=(0, 8))
        ctk.CTkLabel(
            suffix_row, text=t("suffix_hint"),
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=("gray40","gray60"),
        ).pack(side="right" if is_rtl() else "left")

    # Card: Save ────────────────────────────────────────────────────────────
    def _build_card_save(self, parent):
        card = self._card_outer(parent)
        self._card_title(card, t("s4_save"))
        inner = self._card_inner(card)

        self._out_mode = ctk.StringVar(value=prefs["out_mode"])
        anchor = "e" if is_rtl() else "w"

        ctk.CTkRadioButton(
            inner, text=t("save_beside"),
            variable=self._out_mode, value="beside",
            font=ctk.CTkFont("Segoe UI", 12),
            command=self._save_mode_changed,
        ).pack(anchor=anchor, pady=(0, 8))

        custom_row = ctk.CTkFrame(inner, fg_color="transparent")
        custom_row.pack(fill="x")

        ctk.CTkRadioButton(
            custom_row, text=t("save_custom"),
            variable=self._out_mode, value="custom",
            font=ctk.CTkFont("Segoe UI", 12),
            command=self._save_mode_changed,
        ).pack(side="right" if is_rtl() else "left")

        self._out_entry = ctk.CTkEntry(
            custom_row,
            width=340, placeholder_text="C:\\Output\\folder",
        )
        self._out_entry.insert(0, prefs["last_out_dir"])
        self._out_entry.pack(
            side="right" if is_rtl() else "left",
            padx=(8, 0) if is_rtl() else (8, 8),
        )
        self._browse_btn = ctk.CTkButton(
            custom_row, text=t("btn_browse"), width=100,
            fg_color=("gray80","gray25"),
            hover_color=("gray70","gray35"),
            text_color=("gray10","gray90"),
            command=self._browse_out,
        )
        self._browse_btn.pack(side="right" if is_rtl() else "left")
        self._save_mode_changed()

    # Card: Log ────────────────────────────────────────────────────────────
    def _build_card_log(self, parent):
        card = self._card_outer(parent)
        self._card_title(card, t("log_title"))
        inner = self._card_inner(card)
        self._log_box = ctk.CTkTextbox(
            inner, height=110, state="disabled",
            font=ctk.CTkFont("Consolas", 11),
            wrap="word",
        )
        self._log_box.pack(fill="x")

    # Bottom action bar ────────────────────────────────────────────────────
    def _build_bottom_bar(self):
        bar = ctk.CTkFrame(self, corner_radius=0, height=66)
        bar.grid(row=2, column=0, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(2, weight=1)  # status label stretches

        pack_side = "right" if is_rtl() else "left"
        status_side = "left" if is_rtl() else "left"

        self._convert_btn = ctk.CTkButton(
            bar, text=t("btn_convert"),
            width=150, height=44,
            font=ctk.CTkFont("Segoe UI", 14, "bold"),
            command=self._convert,
        )
        self._cancel_btn = ctk.CTkButton(
            bar, text=t("btn_cancel"),
            width=110, height=44,
            fg_color=("gray80","gray25"),
            hover_color=("gray70","gray35"),
            text_color=("gray10","gray90"),
            state="disabled",
            command=self._do_cancel,
        )
        self._open_btn = ctk.CTkButton(
            bar, text=t("btn_open"),
            width=180, height=44,
            fg_color=("gray80","gray25"),
            hover_color=("gray70","gray35"),
            text_color=("gray10","gray90"),
            state="disabled",
            command=self._open_out,
        )
        self._status_lbl = ctk.CTkLabel(
            bar, text=t("status_ready"),
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=("gray40","gray60"),
            anchor="w",
        )

        # Real determinate progress bar — no more bouncing
        self._prog = ctk.CTkProgressBar(bar, height=6, corner_radius=3)
        self._prog.set(0)

        for w in (self._convert_btn, self._cancel_btn, self._open_btn):
            w.pack(side=pack_side,
                   padx=(PAD, 0) if w is self._convert_btn else (6, 0),
                   pady=11)
        self._status_lbl.pack(side="left", padx=(12, 0), pady=11)
        self._prog.pack(side="right", padx=PAD, pady=11, fill="x", expand=True)

    # ── Card builder helpers ───────────────────────────────────────────────

    def _card_outer(self, parent, grid_col: int | None = None) -> ctk.CTkFrame:
        """Create a rounded card frame. If grid_col is given, use grid layout."""
        card = ctk.CTkFrame(parent, corner_radius=12)
        if grid_col is None:
            card.pack(fill="x", padx=PAD, pady=(0, PAD))
        else:
            padx_l = (0, PAD // 2) if grid_col == 0 else (PAD // 2, 0)
            card.grid(row=0, column=grid_col, sticky="nsew",
                      padx=padx_l, pady=(0, PAD))
        return card

    def _card_title(self, card: ctk.CTkFrame, title: str):
        anchor = "e" if is_rtl() else "w"
        ctk.CTkLabel(
            card, text=title,
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            anchor=anchor,
        ).pack(anchor=anchor, padx=PAD, pady=(12, 0))
        ctk.CTkFrame(
            card, height=1, fg_color=("gray85","gray30"), corner_radius=0,
        ).pack(fill="x", padx=PAD, pady=(6, 0))

    def _card_inner(self, card: ctk.CTkFrame) -> ctk.CTkFrame:
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", padx=PAD, pady=(10, 14))
        return inner

    # ── State helpers ──────────────────────────────────────────────────────

    def _update_gs_badge(self):
        if self._gs_exe:
            ver = gs.get_version(self._gs_exe)
            self._gs_badge.configure(
                text=t("gs_ok", ver=ver),
                text_color=("#16A34A","#4ADE80"),
            )
        else:
            self._gs_badge.configure(
                text=t("gs_missing"),
                text_color=("#DC2626","#F87171"),
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
        self._cancel_btn.configure(state="normal" if busy else "disabled")
        for btn, _ in self._preset_btns:
            btn.configure(state=s)

    def _refresh_preset_colors(self):
        cur = self._dpi_var.get()
        for btn, dpi in self._preset_btns:
            if dpi == cur:
                btn.configure(
                    fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"],
                    text_color=("white","white"),
                )
            else:
                btn.configure(
                    fg_color=("gray80","gray25"),
                    hover_color=("gray70","gray35"),
                    text_color=("gray10","gray90"),
                )

    def _set_preset(self, dpi: int):
        self._dpi_var.set(dpi)
        self._dpi_entry.delete(0, "end")
        self._dpi_entry.insert(0, str(dpi))
        self._refresh_preset_colors()

    def _on_custom_dpi(self):
        """User is typing a custom DPI — deselect all presets."""
        self._dpi_var.set(0)
        self._refresh_preset_colors()

    def _fmt_changed(self):
        """Show/hide PNG-specific and JPG-specific options."""
        is_png = self._fmt.get() == "png"
        if is_png:
            self._jpg_section.pack_forget()
            self._png_section.pack(fill="x", pady=(0, 4))
        else:
            self._png_section.pack_forget()
            self._jpg_section.pack(fill="x", pady=(0, 4))

    def _save_mode_changed(self):
        """Disable the folder entry when 'beside' is selected."""
        if self._out_mode.get() == "beside":
            self._out_entry.configure(state="disabled")
            self._browse_btn.configure(state="disabled")
        else:
            self._out_entry.configure(state="normal")
            self._browse_btn.configure(state="normal")

    # ── File operations ───────────────────────────────────────────────────

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title="Select EPS / AI files",
            filetypes=[("Vector files","*.eps *.ai *.EPS *.AI"),
                       ("All files","*.*")],
        )
        if paths:
            self._ingest(list(paths))

    def _add_folder(self):
        folder = filedialog.askdirectory(title="Choose folder with EPS / AI files")
        if not folder:
            return
        found: list[str] = []
        for ext in ("*.eps","*.ai","*.EPS","*.AI"):
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
            if os.path.splitext(p)[1].lower() not in (".eps",".ai"):
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

        # Read DPI from entry (may differ from preset)
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

        # Persist prefs
        prefs["fmt"]         = fmt
        prefs["dpi"]         = dpi
        prefs["jpg_quality"] = jpg_q
        prefs["bg"]          = self._bg.get()
        prefs["all_pages"]   = all_pages
        prefs["suffix"]      = suffix
        prefs["out_mode"]    = self._out_mode.get()
        if out_dir:
            prefs["last_out_dir"] = out_dir
        prefs.save()

        self._cancel       = False
        self._last_out     = out_dir
        self._prog_total   = len(self._files)
        self._set_busy(True)
        self._prog.set(0)     # real determinate: start at 0
        self._status_lbl.configure(text=t("status_conv", i=0, n=self._prog_total, name="…"))

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
                self._q.put(("done", None))
                return

            name = os.path.basename(src)
            base = os.path.splitext(name)[0] + suffix
            dst_base = (
                os.path.join(out_dir, base) if out_dir
                else os.path.join(os.path.dirname(src), base)
            )
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

            # Real progress: i/total
            self._q.put(("progress", i / total))

        self._last_out = out_dir or first_out
        self._q.put(("status", t("status_done", ok=ok, fail=fail)))
        self._q.put(("done", None))

    def _drain(self):
        try:
            while True:
                kind, data = self._q.get_nowait()
                if kind == "log":
                    self._log(data)
                elif kind == "status":
                    self._status_lbl.configure(text=data)
                elif kind == "progress":
                    # Smooth real progress bar
                    self._prog.set(data)
                elif kind == "done":
                    self._prog.set(1)
                    self._set_busy(False)
                    self._open_btn.configure(
                        state="normal" if self._last_out else "disabled"
                    )
        except queue.Empty:
            pass
        self.after(120, self._drain)
