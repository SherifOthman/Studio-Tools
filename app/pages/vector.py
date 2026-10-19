"""
pages/vector.py  –  Vector Export page
Converts EPS / AI files to PNG or JPG with Illustrator-grade quality.
The conversion runs in a background thread so the UI stays responsive.
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

# DPI presets  (string-key for translation, int dpi value)
PRESETS = [
    ("q_screen",  72),
    ("q_web",    150),
    ("q_print",  300),
    ("q_hires",  600),
]

PAD = 20   # standard outer padding


class VectorPage(ctk.CTkFrame):
    """Full EPS/AI → image conversion page."""

    def __init__(self, master, **kw):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kw)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._files: list[str] = []
        self._busy = False
        self._cancel = False
        self._last_out: str | None = None
        self._q: queue.Queue = queue.Queue()
        self._gs_exe = gs.find()

        self._build()
        self._update_gs_badge()
        self.after(120, self._drain)

    # ── Build ─────────────────────────────────────────────────────────────

    def _build(self):
        self._build_header()
        self._build_body()
        self._build_bottom_bar()

    # Header strip
    def _build_header(self):
        hdr = ctk.CTkFrame(self, corner_radius=0, height=68)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            hdr, text=t("vec_title"),
            font=ctk.CTkFont("Segoe UI", 22, "bold"),
            anchor="w",
        ).grid(row=0, column=0, padx=(PAD, 12), pady=(14, 4), sticky="w")

        ctk.CTkLabel(
            hdr, text=t("vec_subtitle"),
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=("gray40", "gray60"),
            anchor="w",
        ).grid(row=1, column=0, padx=(PAD, 12), pady=(0, 10), sticky="w")

        self._gs_badge = ctk.CTkLabel(
            hdr, text="",
            font=ctk.CTkFont("Segoe UI", 10),
            anchor="e",
        )
        self._gs_badge.grid(row=0, column=2, rowspan=2, padx=(0, PAD), sticky="e")

    # Scrollable card body
    def _build_body(self):
        scroll = ctk.CTkScrollableFrame(
            self, corner_radius=0, fg_color="transparent",
        )
        scroll.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        scroll.grid_columnconfigure(0, weight=1)

        self._build_card_files(scroll)
        self._build_card_format(scroll)
        self._build_card_quality(scroll)
        self._build_card_save(scroll)
        self._build_card_log(scroll)

    # Card: Files
    def _build_card_files(self, parent):
        card = self._card(parent, t("s1_files"))

        # Button row
        br = ctk.CTkFrame(card, fg_color="transparent")
        br.pack(fill="x", pady=(0, 10))

        self._btn_add   = ctk.CTkButton(br, text=t("btn_add_files"),   width=130,
                                         command=self._add_files)
        self._btn_folder= ctk.CTkButton(br, text=t("btn_add_folder"),  width=140,
                                         fg_color=("gray80","gray25"),
                                         hover_color=("gray70","gray35"),
                                         text_color=("gray10","gray90"),
                                         command=self._add_folder)
        self._btn_rm    = ctk.CTkButton(br, text=t("btn_remove"),      width=130,
                                         fg_color=("gray80","gray25"),
                                         hover_color=("gray70","gray35"),
                                         text_color=("gray10","gray90"),
                                         command=self._remove_sel)
        self._btn_clear = ctk.CTkButton(br, text=t("btn_clear"),       width=100,
                                         fg_color=("gray80","gray25"),
                                         hover_color=("gray70","gray35"),
                                         text_color=("gray10","gray90"),
                                         command=self._clear)

        for w in (self._btn_add, self._btn_folder, self._btn_rm, self._btn_clear):
            w.pack(side="left", padx=(0, 8))

        self._count_lbl = ctk.CTkLabel(
            br, text=t("n_files_0"),
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=("gray40","gray60"),
        )
        self._count_lbl.pack(side="right")

        # File textbox (read-only list)
        self._file_box = ctk.CTkTextbox(
            card, height=160, state="disabled",
            font=ctk.CTkFont("Consolas", 11),
            wrap="none",
        )
        self._file_box.pack(fill="x")

    # Card: Format
    def _build_card_format(self, parent):
        card = self._card(parent, t("s2_format"))

        self._fmt = ctk.StringVar(value=prefs["fmt"])
        for val, key in (("png", "fmt_png"), ("jpg", "fmt_jpg")):
            ctk.CTkRadioButton(
                card, text=t(key),
                variable=self._fmt, value=val,
                command=self._fmt_changed,
                font=ctk.CTkFont("Segoe UI", 12),
            ).pack(anchor="w", pady=4)

    # Card: Quality
    def _build_card_quality(self, parent):
        card = self._card(parent, t("s3_quality"))

        # Segmented-style preset row
        seg_row = ctk.CTkFrame(card, fg_color="transparent")
        seg_row.pack(fill="x", pady=(0, 8))

        self._dpi_var = ctk.IntVar(value=prefs["dpi"])
        self._preset_btns: list[tuple[ctk.CTkButton, int]] = []

        for key, dpi in PRESETS:
            b = ctk.CTkButton(
                seg_row, text=t(key),
                width=110, height=56,
                corner_radius=8,
                font=ctk.CTkFont("Segoe UI", 11),
                command=lambda d=dpi: self._set_preset(d),
            )
            b.pack(side="left", padx=(0, 8))
            self._preset_btns.append((b, dpi))

        self._refresh_preset_colors()

        ctk.CTkLabel(
            card, text=t("q_hint"),
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=("gray40","gray60"),
            wraplength=680, justify="left",
        ).pack(anchor="w", pady=(0, 8))

        # Collapsible advanced
        self._adv_open = False
        self._adv_btn = ctk.CTkButton(
            card, text=t("adv_label"),
            anchor="w", width=200, height=28,
            fg_color="transparent",
            hover_color=("gray85","gray25"),
            text_color=("gray30","gray70"),
            font=ctk.CTkFont("Segoe UI", 11),
            command=self._toggle_adv,
        )
        self._adv_btn.pack(anchor="w", pady=(4, 0))

        self._adv_frame = ctk.CTkFrame(card, fg_color="transparent")
        self._build_advanced(self._adv_frame)

    def _build_advanced(self, parent):
        def row():
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.pack(fill="x", pady=5)
            return f

        # Custom DPI
        r = row()
        ctk.CTkLabel(r, text=t("adv_dpi"), width=140, anchor="w",
                     font=ctk.CTkFont("Segoe UI", 11, "bold")).pack(side="left")
        self._dpi_entry = ctk.CTkEntry(r, width=72,
                                       textvariable=ctk.StringVar(value=str(prefs["dpi"])))
        self._dpi_entry.pack(side="left", padx=(0, 10))
        ctk.CTkLabel(r, text=t("adv_dpi_hint"),
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=("gray40","gray60")).pack(side="left")

        # Background
        r = row()
        ctk.CTkLabel(r, text=t("adv_bg"), width=140, anchor="w",
                     font=ctk.CTkFont("Segoe UI", 11, "bold")).pack(side="left")
        self._bg = ctk.StringVar(value=prefs["bg"])
        ctk.CTkRadioButton(r, text=t("adv_transparent"),
                            variable=self._bg, value="transparent").pack(side="left", padx=(0,16))
        ctk.CTkRadioButton(r, text=t("adv_white"),
                            variable=self._bg, value="white").pack(side="left")

        # JPG quality slider
        r = row()
        ctk.CTkLabel(r, text=t("adv_jpg_q"), width=140, anchor="w",
                     font=ctk.CTkFont("Segoe UI", 11, "bold")).pack(side="left")
        self._jpg_q = ctk.IntVar(value=prefs["jpg_quality"])
        self._jpg_slider = ctk.CTkSlider(r, from_=10, to=100,
                                          variable=self._jpg_q, width=180)
        self._jpg_slider.pack(side="left", padx=(0, 8))
        self._jpg_lbl = ctk.CTkLabel(r, text=str(prefs["jpg_quality"]), width=28,
                                      font=ctk.CTkFont("Segoe UI", 11))
        self._jpg_lbl.pack(side="left")
        self._jpg_q.trace_add("write",
            lambda *_: self._jpg_lbl.configure(text=str(self._jpg_q.get())))

        # All pages
        r = row()
        self._all_pages = ctk.BooleanVar(value=prefs["all_pages"])
        ctk.CTkCheckBox(r, text=t("adv_pages"), variable=self._all_pages,
                         font=ctk.CTkFont("Segoe UI", 11)).pack(anchor="w")

        # Suffix
        r = row()
        ctk.CTkLabel(r, text=t("adv_suffix"), width=140, anchor="w",
                     font=ctk.CTkFont("Segoe UI", 11, "bold")).pack(side="left")
        self._suffix = ctk.StringVar(value=prefs["suffix"])
        ctk.CTkEntry(r, textvariable=self._suffix, width=140).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(r, text=t("adv_suffix_hint"),
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=("gray40","gray60")).pack(side="left")

    # Card: Save location
    def _build_card_save(self, parent):
        card = self._card(parent, t("s4_save"))

        self._out_mode = ctk.StringVar(value=prefs["out_mode"])
        ctk.CTkRadioButton(
            card, text=t("save_beside"),
            variable=self._out_mode, value="beside",
            font=ctk.CTkFont("Segoe UI", 12),
        ).pack(anchor="w", pady=(0, 8))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkRadioButton(
            row, text=t("save_custom"),
            variable=self._out_mode, value="custom",
            font=ctk.CTkFont("Segoe UI", 12),
        ).pack(side="left")
        self._out_entry = ctk.CTkEntry(
            row, textvariable=ctk.StringVar(value=prefs["last_out_dir"]),
            width=340, placeholder_text="C:\\Output\\folder",
        )
        self._out_entry.pack(side="left", padx=10)
        ctk.CTkButton(
            row, text=t("btn_browse"), width=100,
            fg_color=("gray80","gray25"),
            hover_color=("gray70","gray35"),
            text_color=("gray10","gray90"),
            command=self._browse_out,
        ).pack(side="left")

    # Card: Log
    def _build_card_log(self, parent):
        card = self._card(parent, t("log_title"))
        self._log_box = ctk.CTkTextbox(
            card, height=130, state="disabled",
            font=ctk.CTkFont("Consolas", 11),
            wrap="word",
        )
        self._log_box.pack(fill="x")

    # Bottom action bar
    def _build_bottom_bar(self):
        bar = ctk.CTkFrame(self, corner_radius=0, height=68)
        bar.grid(row=2, column=0, sticky="ew")
        bar.grid_propagate(False)

        self._convert_btn = ctk.CTkButton(
            bar, text=t("btn_convert"),
            width=150, height=44,
            font=ctk.CTkFont("Segoe UI", 14, "bold"),
            command=self._convert,
        )
        self._cancel_btn = ctk.CTkButton(
            bar, text=t("btn_cancel"),
            width=100, height=44,
            fg_color=("gray80","gray25"),
            hover_color=("gray70","gray35"),
            text_color=("gray10","gray90"),
            state="disabled",
            command=self._do_cancel,
        )
        self._open_btn = ctk.CTkButton(
            bar, text=t("btn_open"),
            width=170, height=44,
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
        self._prog = ctk.CTkProgressBar(bar, height=6, corner_radius=3)
        self._prog.set(0)

        self._convert_btn.pack(side="left", padx=(PAD, 8), pady=12)
        self._cancel_btn.pack (side="left", padx=(0, 8),   pady=12)
        self._open_btn.pack   (side="left", padx=(0, 8),   pady=12)
        self._status_lbl.pack (side="left", padx=8,         pady=12)
        self._prog.pack       (side="right",padx=PAD,       pady=12, fill="x", expand=True)

    # ── Helpers ───────────────────────────────────────────────────────────

    def _card(self, parent, title: str) -> ctk.CTkFrame:
        """Return the inner frame of a titled card."""
        outer = ctk.CTkFrame(parent, corner_radius=12)
        outer.pack(fill="x", padx=PAD, pady=(0, PAD))
        outer.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            outer, text=title,
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            anchor="w",
        ).pack(anchor="w", padx=PAD, pady=(14, 0))

        sep = ctk.CTkFrame(outer, height=1,
                           fg_color=("gray85","gray30"),
                           corner_radius=0)
        sep.pack(fill="x", padx=PAD, pady=(6, 0))

        inner = ctk.CTkFrame(outer, fg_color="transparent")
        inner.pack(fill="both", padx=PAD, pady=(10, 14))
        return inner

    def _update_gs_badge(self):
        if self._gs_exe:
            ver = gs.get_version(self._gs_exe)
            self._gs_badge.configure(
                text=t("gs_ok", ver=ver),
                text_color=("#16A34A", "#4ADE80"),   # green
            )
        else:
            self._gs_badge.configure(
                text=t("gs_missing"),
                text_color=("#DC2626", "#F87171"),   # red
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
                  self._convert_btn, self._out_entry):
            w.configure(state=s)
        self._cancel_btn.configure(state="normal" if busy else "disabled")
        if not busy:
            self._prog.stop()

    def _refresh_preset_colors(self):
        cur = self._dpi_var.get()
        for btn, dpi in self._preset_btns:
            if dpi == cur:
                btn.configure(
                    fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"],
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

    def _fmt_changed(self):
        is_jpg = self._fmt.get() == "jpg"
        self._jpg_slider.configure(state="normal" if is_jpg else "disabled")

    def _toggle_adv(self):
        if self._adv_open:
            self._adv_frame.pack_forget()
            self._adv_btn.configure(text=t("adv_label"))
        else:
            self._adv_frame.pack(fill="x", pady=(4, 0))
            self._adv_btn.configure(text=t("adv_label_open"))
        self._adv_open = not self._adv_open

    # ── File operations ───────────────────────────────────────────────────

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title="Select EPS / AI files",
            filetypes=[
                ("Vector files", "*.eps *.ai *.EPS *.AI"),
                ("All files", "*.*"),
            ],
        )
        if paths:
            self._ingest(list(paths))

    def _add_folder(self):
        folder = filedialog.askdirectory(title="Choose folder containing EPS / AI files")
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
        """Remove the last file (CTkTextbox has no row selection)."""
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
            self._out_entry.delete(0, "end")
            self._out_entry.insert(0, d)
            self._out_mode.set("custom")

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

        # Persist preferences
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

        self._cancel = False
        self._last_out = out_dir
        self._set_busy(True)
        self._prog.configure(mode="indeterminate")
        self._prog.start()

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
                self._q.put(("log", "✓  " + name + "  →  " +
                             ", ".join(os.path.basename(o) for o in outs)))
            except Exception as e:
                fail += 1
                self._q.put(("log", f"✗  {name}  —  {e}"))

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
                elif kind == "done":
                    self._prog.configure(mode="determinate")
                    self._prog.set(1)
                    self._set_busy(False)
                    self._open_btn.configure(
                        state="normal" if self._last_out else "disabled"
                    )
        except queue.Empty:
            pass
        self.after(120, self._drain)
