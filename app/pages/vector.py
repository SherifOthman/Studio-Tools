"""pages/vector.py – Vector Export page. English / LTR only."""

import glob
import os
import queue
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk

from app.core        import gs, notify
from app.core.prefs  import prefs
from app.core.strings import t
from app.core.palette import (CHIP, CHIP_HOVER, CHIP_TEXT, DIVIDER, EDGE,
                              GHOST, GHOST_HOVER, GHOST_TEXT,
                              SEC, SEC_BORDER, SEC_HOVER, SEC_TEXT,
                              TEXT, TEXT_DISABLED, TEXT_SUB)

PRESETS = [("q_screen", 72), ("q_web", 150), ("q_print", 300), ("q_hires", 600)]
PAD = 16


class VectorPage(ctk.CTkFrame):

    def __init__(self, master, shell=None, **kw):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kw)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._shell     = shell
        self._files: list[str] = []
        self._busy      = False
        self._cancel    = False
        self._last_out: str | None = None
        self._q: queue.Queue = queue.Queue()
        self._gs_exe    = gs.find()

        self._build()
        self._update_gs_badge()
        self.after(120, self._drain)

    # ── Header ────────────────────────────────────────────────────────────

    def _build(self):
        # Header
        hdr = ctk.CTkFrame(self, corner_radius=0, height=70)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(hdr, text=t("vec_title"),
                     font=ctk.CTkFont("Segoe UI", 22, "bold"),
                     anchor="w").grid(row=0, column=0, padx=(PAD, 10),
                                      pady=(14, 2), sticky="w")
        ctk.CTkLabel(hdr, text=t("vec_subtitle"),
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=(TEXT_SUB[0], TEXT_SUB[1]),
                     anchor="w").grid(row=1, column=0, padx=(PAD, 10),
                                      pady=(0, 10), sticky="w")

        self._gs_badge = ctk.CTkLabel(hdr, text="",
                                       font=ctk.CTkFont("Segoe UI", 10),
                                       anchor="e")
        self._gs_badge.grid(row=0, column=2, rowspan=2, padx=PAD, sticky="e")

        # Separator under header
        ctk.CTkFrame(self, height=1, fg_color=EDGE,
                     corner_radius=0).grid(row=0, column=0, sticky="sew")

        # Scrollable body
        scroll = ctk.CTkScrollableFrame(self, corner_radius=0,
                                         fg_color="transparent")
        scroll.grid(row=1, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        self._build_files(scroll)

        two = ctk.CTkFrame(scroll, fg_color="transparent")
        two.pack(fill="x", padx=PAD, pady=(0, PAD))
        two.grid_columnconfigure(0, weight=1)
        two.grid_columnconfigure(1, weight=2)
        self._build_format(two)
        self._build_quality(two)

        self._build_save(scroll)
        self._build_log(scroll)

        # Action bar
        bar = ctk.CTkFrame(self, corner_radius=0, height=64)
        bar.grid(row=2, column=0, sticky="ew")
        bar.grid_propagate(False)
        ctk.CTkFrame(bar, height=1, fg_color=EDGE,
                     corner_radius=0).pack(fill="x", side="top")
        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="both", expand=True)

        self._convert_btn = ctk.CTkButton(inner, text=t("btn_convert"),
                                           width=150, height=42,
                                           font=ctk.CTkFont("Segoe UI", 14, "bold"),
                                           command=self._convert)
        self._cancel_btn = ctk.CTkButton(inner, text=t("btn_cancel"),
                                          width=110, height=42, state="disabled",
                                          **self._sec(), command=self._do_cancel)
        self._open_btn = ctk.CTkButton(inner, text=t("btn_open"),
                                        width=180, height=42, state="disabled",
                                        **self._sec(), command=self._open_out)
        self._status_lbl = ctk.CTkLabel(inner, text=t("status_ready"),
                                         font=ctk.CTkFont("Segoe UI", 11),
                                         text_color=(TEXT_SUB[0], TEXT_SUB[1]),
                                         anchor="w")
        self._prog = ctk.CTkProgressBar(inner, height=6, corner_radius=3)
        self._prog.set(0)

        self._convert_btn.pack(side="left", padx=(PAD, 0), pady=10)
        self._cancel_btn.pack(side="left",  padx=(6, 0),   pady=10)
        self._open_btn.pack(side="left",    padx=(6, 0),   pady=10)
        self._status_lbl.pack(side="left",  padx=(10, 0),  pady=10)
        self._prog.pack(side="right", padx=PAD, pady=10, fill="x", expand=True)

    # ── Cards ─────────────────────────────────────────────────────────────

    def _build_files(self, parent):
        inner = self._card(parent, t("s1_files"), pack=True, top_pad=PAD)

        br = ctk.CTkFrame(inner, fg_color="transparent")
        br.pack(fill="x", pady=(0, 8))

        self._btn_add    = ctk.CTkButton(br, text=t("btn_add_files"),  width=130,
                                          command=self._add_files)
        self._btn_folder = ctk.CTkButton(br, text=t("btn_add_folder"), width=130,
                                          **self._sec(), command=self._add_folder)
        self._btn_rm     = ctk.CTkButton(br, text=t("btn_remove"),     width=120,
                                          **self._ghost(), command=self._remove_sel)
        self._btn_clear  = ctk.CTkButton(br, text=t("btn_clear"),      width=110,
                                          **self._ghost(), command=self._clear)
        for b in (self._btn_add, self._btn_folder, self._btn_rm, self._btn_clear):
            b.pack(side="left", padx=(0, 6))

        self._count_lbl = ctk.CTkLabel(br, text=t("n_files_0"),
                                        font=ctk.CTkFont("Segoe UI", 11),
                                        text_color=(TEXT_SUB[0], TEXT_SUB[1]))
        self._count_lbl.pack(side="right", padx=4)

        self._file_box = ctk.CTkTextbox(inner, height=130, state="disabled",
                                         font=ctk.CTkFont("Consolas", 11),
                                         wrap="none")
        self._file_box.pack(fill="x")

    def _build_format(self, parent):
        inner = self._card(parent, t("s2_format"), grid_col=0)
        self._fmt = ctk.StringVar(value=prefs["fmt"])

        ctk.CTkRadioButton(inner, text=t("fmt_png"), variable=self._fmt,
                            value="png", command=self._fmt_changed,
                            font=ctk.CTkFont("Segoe UI", 12),
                            ).pack(anchor="w", pady=(0, 4))
        ctk.CTkRadioButton(inner, text=t("fmt_jpg"), variable=self._fmt,
                            value="jpg", command=self._fmt_changed,
                            font=ctk.CTkFont("Segoe UI", 12),
                            ).pack(anchor="w", pady=(0, 10))

        # PNG background section
        self._png_sec = ctk.CTkFrame(inner, fg_color="transparent")
        ctk.CTkLabel(self._png_sec, text=t("png_bg_label"),
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     anchor="w").pack(anchor="w", pady=(0, 4))
        self._bg = ctk.StringVar(value=prefs["bg"])
        ctk.CTkRadioButton(self._png_sec, text=t("adv_bg_trans"),
                            variable=self._bg, value="transparent",
                            font=ctk.CTkFont("Segoe UI", 11),
                            ).pack(anchor="w", pady=(0, 4))
        ctk.CTkRadioButton(self._png_sec, text=t("adv_bg_white"),
                            variable=self._bg, value="white",
                            font=ctk.CTkFont("Segoe UI", 11),
                            ).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(self._png_sec, text=t("fmt_png_hint"),
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=(TEXT_SUB[0], TEXT_SUB[1]),
                     anchor="w", wraplength=220,
                     ).pack(anchor="w", pady=(2, 0))

        # JPG quality section
        self._jpg_sec = ctk.CTkFrame(inner, fg_color="transparent")
        ctk.CTkLabel(self._jpg_sec, text=t("jpg_q_label"),
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     anchor="w").pack(anchor="w", pady=(0, 6))

        sl_row = ctk.CTkFrame(self._jpg_sec, fg_color="transparent")
        sl_row.pack(fill="x")
        self._jpg_q   = ctk.IntVar(value=prefs["jpg_quality"])
        self._jpg_sld = ctk.CTkSlider(sl_row, from_=10, to=100,
                                       variable=self._jpg_q, width=170)
        self._jpg_lbl = ctk.CTkLabel(sl_row, text=str(prefs["jpg_quality"]),
                                      width=36,
                                      font=ctk.CTkFont("Segoe UI", 13, "bold"))
        self._jpg_sld.pack(side="left")
        self._jpg_lbl.pack(side="left", padx=(8, 0))
        self._jpg_q.trace_add("write",
            lambda *_: self._jpg_lbl.configure(text=str(self._jpg_q.get())))

        ctk.CTkLabel(self._jpg_sec, text=t("jpg_q_hint"),
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=(TEXT_SUB[0], TEXT_SUB[1]),
                     anchor="w", wraplength=220,
                     ).pack(anchor="w", pady=(4, 0))

        self._fmt_changed()

    def _build_quality(self, parent):
        inner = self._card(parent, t("s3_quality"), grid_col=1)

        # Preset buttons
        pr = ctk.CTkFrame(inner, fg_color="transparent")
        pr.pack(anchor="w", pady=(0, 8))
        self._dpi_var = ctk.IntVar(value=prefs["dpi"])
        self._preset_btns: list[tuple[ctk.CTkButton, int]] = []
        for key, dpi in PRESETS:
            b = ctk.CTkButton(pr, text=t(key), width=88, height=50,
                               corner_radius=8,
                               font=ctk.CTkFont("Segoe UI", 10),
                               command=lambda d=dpi: self._set_preset(d))
            b.pack(side="left", padx=(0, 6))
            self._preset_btns.append((b, dpi))
        self._refresh_preset_colors()

        ctk.CTkLabel(inner, text=t("q_hint"),
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=(TEXT_SUB[0], TEXT_SUB[1]),
                     anchor="w", wraplength=320,
                     ).pack(anchor="w", pady=(0, 10))

        # Custom DPI
        dpi_row = ctk.CTkFrame(inner, fg_color="transparent")
        dpi_row.pack(anchor="w", pady=(0, 10))
        ctk.CTkLabel(dpi_row, text=t("q_custom_label"),
                     font=ctk.CTkFont("Segoe UI", 11),
                     ).pack(side="left", padx=(0, 8))
        self._dpi_entry = ctk.CTkEntry(dpi_row, width=78,
                                        placeholder_text="300",
                                        justify="left")
        self._dpi_entry.insert(0, str(prefs["dpi"]))
        self._dpi_entry.bind("<KeyRelease>", lambda _: self._on_custom_dpi())
        self._dpi_entry.pack(side="left")

        ctk.CTkFrame(inner, height=1, fg_color=DIVIDER,
                     corner_radius=0).pack(fill="x", pady=(0, 10))

        # Multi-page
        ctk.CTkLabel(inner, text=t("pages_label"),
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     anchor="w").pack(anchor="w")
        self._all_pages = ctk.BooleanVar(value=prefs["all_pages"])
        ctk.CTkCheckBox(inner, text=t("pages_check"),
                         variable=self._all_pages,
                         font=ctk.CTkFont("Segoe UI", 11),
                         ).pack(anchor="w", pady=(4, 2))
        ctk.CTkLabel(inner, text=t("pages_hint"),
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=(TEXT_SUB[0], TEXT_SUB[1]),
                     anchor="w",
                     ).pack(anchor="w", pady=(0, 10))

        # Suffix
        ctk.CTkLabel(inner, text=t("suffix_label"),
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     anchor="w").pack(anchor="w")
        suf_row = ctk.CTkFrame(inner, fg_color="transparent")
        suf_row.pack(anchor="w", pady=(4, 0))
        self._suffix = ctk.StringVar(value=prefs["suffix"])
        ctk.CTkEntry(suf_row, textvariable=self._suffix,
                      width=110, placeholder_text="_web",
                      justify="left").pack(side="left", padx=(0, 8))
        ctk.CTkLabel(suf_row, text=t("suffix_hint"),
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=(TEXT_SUB[0], TEXT_SUB[1]),
                     ).pack(side="left")

    def _build_save(self, parent):
        inner = self._card(parent, t("s4_save"), pack=True)
        self._out_mode = ctk.StringVar(value=prefs["out_mode"])

        ctk.CTkRadioButton(inner, text="  Next to each original file",
                            variable=self._out_mode, value="beside",
                            command=self._save_changed,
                            font=ctk.CTkFont("Segoe UI", 12),
                            ).pack(anchor="w", pady=(0, 10))

        cf = ctk.CTkFrame(inner, fg_color="transparent")
        cf.pack(fill="x")

        self._rb_custom = ctk.CTkRadioButton(
            cf, text="", variable=self._out_mode, value="custom",
            command=self._save_changed, width=20)
        custom_lbl = ctk.CTkLabel(cf, text=t("save_custom"),
                                   font=ctk.CTkFont("Segoe UI", 12), anchor="w",
                                   cursor="hand2")
        custom_lbl.bind("<Button-1>",
                        lambda _: (self._out_mode.set("custom"), self._save_changed()))

        self._out_entry = ctk.CTkEntry(cf, width=270,
                                        placeholder_text="C:\\Output\\folder",
                                        justify="left")
        self._out_entry.insert(0, prefs["last_out_dir"])
        self._browse_btn = ctk.CTkButton(cf, text=t("btn_browse"), width=100,
                                          **self._sec(), command=self._browse_out)

        # Pack in correct visual order: ○  label  [entry]  [browse]
        self._rb_custom.pack(side="left", padx=(0, 4))
        custom_lbl.pack(side="left", padx=(0, 8))
        self._out_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._browse_btn.pack(side="left")

        self._save_changed()

    def _build_log(self, parent):
        inner = self._card(parent, t("log_title"), pack=True)
        self._log_box = ctk.CTkTextbox(inner, height=100, state="disabled",
                                        font=ctk.CTkFont("Consolas", 11),
                                        wrap="word")
        self._log_box.pack(fill="x")

    # ── Card factory ──────────────────────────────────────────────────────

    def _card(self, parent, title: str, pack=False,
              grid_col: int | None = None, top_pad: int = 0) -> ctk.CTkFrame:
        outer = ctk.CTkFrame(parent, corner_radius=12)
        if pack:
            outer.pack(fill="x", padx=PAD, pady=(top_pad, PAD))
        else:
            padx = (0, PAD // 2) if grid_col == 0 else (PAD // 2, 0)
            outer.grid(row=0, column=grid_col, sticky="nsew",
                       padx=padx, pady=(top_pad, PAD))
        ctk.CTkLabel(outer, text=title,
                     font=ctk.CTkFont("Segoe UI", 13, "bold"),
                     anchor="w").pack(anchor="w", padx=PAD, pady=(12, 0))
        ctk.CTkFrame(outer, height=1, fg_color=DIVIDER,
                     corner_radius=0).pack(fill="x", padx=PAD, pady=(6, 0))
        inner = ctk.CTkFrame(outer, fg_color="transparent")
        inner.pack(fill="both", padx=PAD, pady=(10, 14))
        return inner

    def _sec(self) -> dict:
        """Secondary outlined button — clearly clickable in both modes."""
        return dict(
            fg_color=SEC,
            border_width=1,
            border_color=SEC_BORDER,
            hover_color=SEC_HOVER,
            text_color=SEC_TEXT,
            text_color_disabled=TEXT_DISABLED,
        )

    def _ghost(self) -> dict:
        """Tertiary ghost button — light fill, readable text."""
        return dict(
            fg_color=GHOST,
            hover_color=GHOST_HOVER,
            text_color=GHOST_TEXT,
            text_color_disabled=TEXT_DISABLED,
        )

    # ── State ─────────────────────────────────────────────────────────────

    def _update_gs_badge(self):
        if self._gs_exe:
            ver = gs.get_version(self._gs_exe)
            self._gs_badge.configure(text=t("gs_ok", ver=ver),
                                      text_color=("#16A34A", "#4ADE80"))
        else:
            self._gs_badge.configure(text=t("gs_missing"),
                                      text_color=("#DC2626", "#F87171"))

    def _refresh_list(self):
        self._file_box.configure(state="normal")
        self._file_box.delete("1.0", "end")
        for p in self._files:
            self._file_box.insert("end", p + "\n")
        self._file_box.configure(state="disabled")
        n = len(self._files)
        self._count_lbl.configure(
            text=t("n_files_0") if n == 0 else t("n_files_n", n=n))

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
                    hover_color=ctk.ThemeManager.theme["CTkButton"]["hover_color"],
                    text_color=("#FFFFFF", "#FFFFFF"),
                    border_width=0)
            else:
                btn.configure(
                    fg_color=CHIP,
                    hover_color=CHIP_HOVER,
                    text_color=CHIP_TEXT,
                    text_color_disabled=TEXT_DISABLED,
                    border_width=0)

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
            self._jpg_sec.pack_forget()
            self._png_sec.pack(fill="x", pady=(4, 0))
        else:
            self._png_sec.pack_forget()
            self._jpg_sec.pack(fill="x", pady=(4, 0))

    def _save_changed(self):
        beside = self._out_mode.get() == "beside"
        self._out_entry.configure(state="disabled" if beside else "normal")
        self._browse_btn.configure(state="disabled" if beside else "normal")

    def _is_focused(self) -> bool:
        try:
            return bool(self._shell and self._shell.focus_displayof() is not None)
        except Exception:
            return True

    # ── File ops ──────────────────────────────────────────────────────────

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title="Select EPS / AI files",
            filetypes=[("Vector files", "*.eps *.ai *.EPS *.AI"),
                       ("All files", "*.*")])
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
            self._save_changed()

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

        prefs["fmt"] = fmt;  prefs["dpi"] = dpi;  prefs["jpg_quality"] = jpg_q
        prefs["bg"]  = self._bg.get();  prefs["all_pages"] = all_pages
        prefs["suffix"] = suffix;  prefs["out_mode"] = self._out_mode.get()
        if out_dir:
            prefs["last_out_dir"] = out_dir
        prefs.save()

        self._cancel   = False
        self._last_out = out_dir
        self._set_busy(True)
        self._prog.set(0)

        threading.Thread(
            target=self._worker,
            args=(exe, list(self._files), fmt, dpi, jpg_q,
                  all_pages, bg_white, suffix, out_dir),
            daemon=True).start()

    def _worker(self, exe, files, fmt, dpi, jpg_q, all_pages, bg_white,
                suffix, out_dir):
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
                self._q.put(("log", "✓  " + name + "  →  " +
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
                if   kind == "log":      self._log(data)
                elif kind == "status":   self._status_lbl.configure(text=data)
                elif kind == "progress": self._prog.set(data)
                elif kind == "done":
                    ok, fail = data or (0, 0)
                    self._prog.set(1)
                    self._set_busy(False)
                    self._open_btn.configure(
                        state="normal" if self._last_out else "disabled")
                    if not self._is_focused():
                        ti = "Studio Tools — Done ✓"
                        ms = (f"{ok} file(s) exported" +
                              (f",  {fail} failed" if fail else "") +
                              "\nClick to return to Studio Tools")
                        threading.Thread(target=notify.send,
                                         args=(ti, ms), daemon=True).start()
        except queue.Empty:
            pass
        self.after(120, self._drain)
