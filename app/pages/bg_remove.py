"""
pages/bg_remove.py  –  AI Background Remover

Uses rembg (U²Net / BiRefNet AI models) to remove backgrounds from images.
Output is always PNG with a transparent background — or a solid colour fill
if the user picks one.

Features:
  • Batch: process many images at once
  • Multiple AI models: u2net (general), u2net_human_seg (people),
    isnet-general-use (high accuracy), birefnet-general (best quality)
  • Output: transparent PNG or fill with custom colour
  • Optional: keep original, or save as _nobg
  • Progress bar — model is downloaded once then cached (~170 MB)
"""

import io
import os
import glob
import queue
import threading
from tkinter import filedialog, messagebox, colorchooser

import customtkinter as ctk

from app.core.palette import (CHIP, CHIP_HOVER, CHIP_TEXT, DIVIDER, EDGE,
                              GHOST, GHOST_HOVER, GHOST_TEXT,
                              SEC, SEC_HOVER, SEC_TEXT,
                              TEXT, TEXT_DISABLED, TEXT_SUB)

PAD = 16

MODELS = [
    ("u2net",               "General  (fast, good)"),
    ("isnet-general-use",   "ISNet  (higher accuracy, slower)"),
    ("u2net_human_seg",     "People & portraits"),
    ("silueta",             "Silhouette  (objects)"),
]


class BgRemovePage(ctk.CTkFrame):

    def __init__(self, master, **kw):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kw)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._files: list[str] = []
        self._busy   = False
        self._cancel = False
        self._q: queue.Queue = queue.Queue()
        self._fill_color: str | None = None   # None = transparent

        self._build()
        self.after(120, self._drain)

    # ── Layout ─────────────────────────────────────────────────────────────

    def _build(self):
        # Header
        hdr = ctk.CTkFrame(self, corner_radius=0, height=70)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(hdr, text="Remove Background",
                     font=ctk.CTkFont("Segoe UI", 22, "bold"),
                     anchor="w").grid(row=0, column=0, padx=(PAD, 10),
                                      pady=(14, 2), sticky="w")
        ctk.CTkLabel(hdr, text="AI-powered background removal  ·  "
                               "transparent PNG output  ·  originals never changed",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=TEXT_SUB,
                     anchor="w").grid(row=1, column=0, padx=(PAD, 10),
                                      pady=(0, 10), sticky="w")
        ctk.CTkFrame(self, height=1, fg_color=EDGE,
                     corner_radius=0).grid(row=0, column=0, sticky="sew")

        # Body: two columns
        body = ctk.CTkScrollableFrame(self, corner_radius=0,
                                       fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)

        self._build_files_card(body)

        two = ctk.CTkFrame(body, fg_color="transparent")
        two.pack(fill="x", padx=PAD, pady=(0, PAD))
        two.grid_columnconfigure(0, weight=1)
        two.grid_columnconfigure(1, weight=1)
        self._build_model_card(two)
        self._build_output_card(two)

        self._build_save_card(body)
        self._build_log_card(body)

        # Action bar
        bar = ctk.CTkFrame(self, corner_radius=0, height=64)
        bar.grid(row=2, column=0, sticky="ew")
        bar.grid_propagate(False)
        ctk.CTkFrame(bar, height=1, fg_color=EDGE,
                     corner_radius=0).pack(fill="x", side="top")
        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="both", expand=True)

        self._run_btn = ctk.CTkButton(
            inner, text="▶  Remove Backgrounds", width=180, height=42,
            font=ctk.CTkFont("Segoe UI", 14, "bold"),
            command=self._run)
        self._cancel_btn = ctk.CTkButton(
            inner, text="✕  Cancel", width=100, height=42,
            state="disabled",
            fg_color=SEC, hover_color=SEC_HOVER, text_color=SEC_TEXT,
            text_color_disabled=TEXT_DISABLED,
            command=lambda: setattr(self, "_cancel", True))
        self._open_btn = ctk.CTkButton(
            inner, text="📂  Open Output Folder", width=180, height=42,
            state="disabled",
            fg_color=SEC, hover_color=SEC_HOVER, text_color=SEC_TEXT,
            text_color_disabled=TEXT_DISABLED,
            command=self._open_out)
        self._status_lbl = ctk.CTkLabel(
            inner, text="Ready — add images then press Remove Backgrounds",
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=TEXT_SUB, anchor="w")
        self._prog = ctk.CTkProgressBar(inner, height=6, corner_radius=3)
        self._prog.set(0)

        self._run_btn.pack(   side="left", padx=(PAD, 0), pady=10)
        self._cancel_btn.pack(side="left", padx=(8,  0),  pady=10)
        self._open_btn.pack(  side="left", padx=(8,  0),  pady=10)
        self._status_lbl.pack(side="left", padx=(12, 0),  pady=10)
        self._prog.pack(side="right", padx=PAD, pady=10,
                        fill="x", expand=True)

    # ── Cards ──────────────────────────────────────────────────────────────

    def _build_files_card(self, parent):
        inner = self._card(parent, "① Images", pack=True, top_pad=PAD)

        br = ctk.CTkFrame(inner, fg_color="transparent")
        br.pack(fill="x", pady=(0, 8))

        self._btn_add    = ctk.CTkButton(br, text="📄  Add Images", width=130,
                                          command=self._add_files)
        self._btn_folder = ctk.CTkButton(br, text="📂  Add Folder", width=130,
                                          fg_color=SEC, hover_color=SEC_HOVER,
                                          text_color=SEC_TEXT,
                                          text_color_disabled=TEXT_DISABLED,
                                          command=self._add_folder)
        self._btn_rm     = ctk.CTkButton(br, text="✕  Remove Last", width=130,
                                          fg_color=GHOST, hover_color=GHOST_HOVER,
                                          text_color=GHOST_TEXT,
                                          text_color_disabled=TEXT_DISABLED,
                                          command=self._remove_last)
        self._btn_clear  = ctk.CTkButton(br, text="🗑  Clear All", width=100,
                                          fg_color=GHOST, hover_color=GHOST_HOVER,
                                          text_color=GHOST_TEXT,
                                          text_color_disabled=TEXT_DISABLED,
                                          command=self._clear)
        for b in (self._btn_add, self._btn_folder, self._btn_rm, self._btn_clear):
            b.pack(side="left", padx=(0, 6))

        self._count_lbl = ctk.CTkLabel(br, text="0 images",
                                        font=ctk.CTkFont("Segoe UI", 11),
                                        text_color=TEXT_SUB)
        self._count_lbl.pack(side="right", padx=4)

        self._file_box = ctk.CTkTextbox(inner, height=120, state="disabled",
                                         font=ctk.CTkFont("Consolas", 11),
                                         wrap="none")
        self._file_box.pack(fill="x")

    def _build_model_card(self, parent):
        inner = self._card(parent, "② AI Model", grid_col=0)

        ctk.CTkLabel(inner,
                     text="Choose a model based on your image type:",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=TEXT_SUB, anchor="w",
                     wraplength=260).pack(anchor="w", pady=(0, 10))

        self._model = ctk.StringVar(value="u2net")
        for value, desc in MODELS:
            row = ctk.CTkFrame(inner, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkRadioButton(row, text=desc,
                                variable=self._model, value=value,
                                font=ctk.CTkFont("Segoe UI", 12),
                                ).pack(anchor="w")

        ctk.CTkFrame(inner, height=1, fg_color=DIVIDER,
                     corner_radius=0).pack(fill="x", pady=(12, 8))

        ctk.CTkLabel(inner,
                     text="ℹ  The AI model is downloaded automatically the first time "
                          "you use it (~100–170 MB) and cached for future use.",
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=TEXT_SUB, anchor="w",
                     wraplength=270, justify="left").pack(anchor="w")

    def _build_output_card(self, parent):
        inner = self._card(parent, "③ Output", grid_col=1)

        ctk.CTkLabel(inner, text="Background replacement:",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     anchor="w").pack(anchor="w", pady=(0, 6))

        self._fill_mode = ctk.StringVar(value="transparent")
        ctk.CTkRadioButton(inner,
                            text="Transparent  (PNG with alpha channel)",
                            variable=self._fill_mode, value="transparent",
                            command=self._fill_changed,
                            font=ctk.CTkFont("Segoe UI", 12),
                            ).pack(anchor="w", pady=(0, 6))
        ctk.CTkRadioButton(inner,
                            text="White background",
                            variable=self._fill_mode, value="white",
                            command=self._fill_changed,
                            font=ctk.CTkFont("Segoe UI", 12),
                            ).pack(anchor="w", pady=(0, 6))

        color_row = ctk.CTkFrame(inner, fg_color="transparent")
        color_row.pack(anchor="w", pady=(0, 12))
        ctk.CTkRadioButton(color_row,
                            text="Custom colour:",
                            variable=self._fill_mode, value="custom",
                            command=self._fill_changed,
                            font=ctk.CTkFont("Segoe UI", 12),
                            ).pack(side="left")
        self._color_swatch = ctk.CTkFrame(
            color_row, width=28, height=28,
            corner_radius=6, fg_color="#FFFFFF",
            cursor="hand2")
        self._color_swatch.pack(side="left", padx=(8, 0))
        self._color_swatch.bind("<Button-1>", lambda _: self._pick_color())

        ctk.CTkFrame(inner, height=1, fg_color=DIVIDER,
                     corner_radius=0).pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(inner, text="Output filename:",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     anchor="w").pack(anchor="w", pady=(0, 4))
        self._out_suffix = ctk.StringVar(value="_nobg")
        suf_row = ctk.CTkFrame(inner, fg_color="transparent")
        suf_row.pack(anchor="w")
        ctk.CTkLabel(suf_row, text="Original name  +",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=TEXT_SUB).pack(side="left", padx=(0, 6))
        ctk.CTkEntry(suf_row, textvariable=self._out_suffix,
                      width=90, placeholder_text="_nobg").pack(side="left")
        ctk.CTkLabel(suf_row, text=".png",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=TEXT_SUB).pack(side="left", padx=(4, 0))

    def _build_save_card(self, parent):
        inner = self._card(parent, "④ Where to Save", pack=True)
        self._out_mode = ctk.StringVar(value="beside")

        ctk.CTkRadioButton(inner,
                            text="  Next to each original file",
                            variable=self._out_mode, value="beside",
                            command=self._save_changed,
                            font=ctk.CTkFont("Segoe UI", 12),
                            ).pack(anchor="w", pady=(0, 10))

        cf = ctk.CTkFrame(inner, fg_color="transparent")
        cf.pack(fill="x")
        self._rb_custom = ctk.CTkRadioButton(
            cf, text="", variable=self._out_mode, value="custom",
            command=self._save_changed, width=20)
        custom_lbl = ctk.CTkLabel(cf, text="  Save to a specific folder:",
                                   font=ctk.CTkFont("Segoe UI", 12),
                                   anchor="w", cursor="hand2")
        custom_lbl.bind("<Button-1>",
                        lambda _: (self._out_mode.set("custom"),
                                   self._save_changed()))
        self._out_entry = ctk.CTkEntry(cf, width=270,
                                        placeholder_text="C:\\Output\\folder",
                                        justify="left")
        self._browse_btn = ctk.CTkButton(
            cf, text="Browse…", width=100,
            fg_color=SEC, hover_color=SEC_HOVER, text_color=SEC_TEXT,
            text_color_disabled=TEXT_DISABLED,
            command=self._browse_out)

        self._rb_custom.pack(side="left", padx=(0, 4))
        custom_lbl.pack(side="left",      padx=(0, 8))
        self._out_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._browse_btn.pack(side="left")
        self._save_changed()

    def _build_log_card(self, parent):
        inner = self._card(parent, "Progress Log", pack=True)
        self._log = ctk.CTkTextbox(inner, height=100, state="disabled",
                                    font=ctk.CTkFont("Consolas", 11),
                                    wrap="word")
        self._log.pack(fill="x")

    # ── Card factory ───────────────────────────────────────────────────────

    def _card(self, parent, title: str, pack=False,
              grid_col: int | None = None,
              top_pad: int = 0) -> ctk.CTkFrame:
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

    # ── State helpers ──────────────────────────────────────────────────────

    def _fill_changed(self):
        pass   # just triggers the variable update; colour is read at run time

    def _pick_color(self):
        color = colorchooser.askcolor(
            title="Choose background colour",
            color=self._fill_color or "#FFFFFF")
        if color and color[1]:
            self._fill_color = color[1]
            self._color_swatch.configure(fg_color=self._fill_color)
            self._fill_mode.set("custom")

    def _save_changed(self):
        beside = self._out_mode.get() == "beside"
        self._out_entry.configure(state="disabled" if beside else "normal")
        self._browse_btn.configure(state="disabled" if beside else "normal")

    def _browse_out(self):
        d = filedialog.askdirectory(title="Choose output folder")
        if d:
            self._out_entry.configure(state="normal")
            self._out_entry.delete(0, "end")
            self._out_entry.insert(0, d)
            self._out_mode.set("custom")
            self._save_changed()

    def _open_out(self):
        if hasattr(self, "_last_out") and self._last_out and \
                os.path.isdir(self._last_out):
            try:
                os.startfile(self._last_out)
            except Exception:
                pass

    def _log_msg(self, msg: str):
        self._log.configure(state="normal")
        self._log.insert("end", msg + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def _set_busy(self, busy: bool):
        self._busy = busy
        s = "disabled" if busy else "normal"
        for w in (self._run_btn, self._btn_add, self._btn_folder,
                  self._btn_rm, self._btn_clear, self._out_entry,
                  self._browse_btn):
            w.configure(state=s)
        self._cancel_btn.configure(state="normal" if busy else "disabled")

    # ── File operations ────────────────────────────────────────────────────

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title="Select images",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp *.bmp "
                                  "*.tiff *.tif *.JPG *.PNG *.WEBP"),
                       ("All files", "*.*")])
        if paths:
            self._ingest(list(paths))

    def _add_folder(self):
        folder = filedialog.askdirectory(title="Choose folder")
        if not folder:
            return
        found = []
        for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp", "*.bmp",
                    "*.tiff", "*.tif"):
            found.extend(glob.glob(os.path.join(folder, ext)))
            found.extend(glob.glob(os.path.join(folder, ext.upper())))
        self._ingest(sorted(set(found)))

    def _ingest(self, paths: list[str]):
        existing = set(self._files)
        for p in paths:
            p = os.path.abspath(p)
            if p not in existing:
                self._files.append(p)
                existing.add(p)
        self._refresh_list()

    def _remove_last(self):
        if self._files:
            self._files.pop()
            self._refresh_list()

    def _clear(self):
        self._files.clear()
        self._refresh_list()

    def _refresh_list(self):
        self._file_box.configure(state="normal")
        self._file_box.delete("1.0", "end")
        for p in self._files:
            self._file_box.insert("end", p + "\n")
        self._file_box.configure(state="disabled")
        n = len(self._files)
        self._count_lbl.configure(
            text="0 images" if n == 0 else f"{n} image(s)")

    # ── Main processing ────────────────────────────────────────────────────

    def _run(self):
        if self._busy:
            return
        if not self._files:
            messagebox.showinfo("Studio Tools",
                                "Add some images first.")
            return

        out_dir: str | None = None
        if self._out_mode.get() == "custom":
            out_dir = self._out_entry.get().strip()
            if not out_dir:
                messagebox.showerror("Studio Tools",
                    "Choose an output folder or switch to 'Next to original'.")
                return
            os.makedirs(out_dir, exist_ok=True)

        model    = self._model.get()
        fill_mode = self._fill_mode.get()
        fill_col  = self._fill_color or "#FFFFFF"
        suffix    = self._out_suffix.get().strip() or "_nobg"

        self._cancel = False
        self._last_out = out_dir
        self._set_busy(True)
        self._prog.set(0)

        threading.Thread(
            target=self._worker,
            args=(list(self._files), model, fill_mode, fill_col,
                  suffix, out_dir),
            daemon=True).start()

    def _worker(self, files, model, fill_mode, fill_col,
                suffix, out_dir):
        """Background thread — runs rembg on each image."""
        total = len(files)
        ok = fail = 0

        try:
            from rembg import remove, new_session
            from PIL import Image
        except ImportError as e:
            self._q.put(("status", f"Error: {e}"))
            self._q.put(("done", None))
            return

        self._q.put(("status", f"Loading AI model '{model}'…"))
        try:
            session = new_session(model)
        except Exception as e:
            self._q.put(("status", f"Failed to load model: {e}"))
            self._q.put(("done", None))
            return

        first_out = None
        for i, src in enumerate(files, start=1):
            if self._cancel:
                self._q.put(("status",
                              f"Cancelled — {ok} done, {fail} failed"))
                self._q.put(("done", out_dir or first_out))
                return

            name = os.path.basename(src)
            base = os.path.splitext(name)[0]
            dst  = os.path.join(
                out_dir if out_dir else os.path.dirname(src),
                base + suffix + ".png")
            if first_out is None:
                first_out = os.path.dirname(dst)

            self._q.put(("status",
                          f"Processing  {i} / {total}  ·  {name}"))
            try:
                with open(src, "rb") as f:
                    img_bytes = f.read()

                # Remove background
                out_bytes = remove(img_bytes, session=session)
                img = Image.open(io.BytesIO(out_bytes)).convert("RGBA")

                # Apply fill if needed
                if fill_mode == "white":
                    bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
                    bg.paste(img, mask=img.split()[3])
                    img = bg.convert("RGB")
                elif fill_mode == "custom":
                    # Parse hex colour
                    hx = fill_col.lstrip("#")
                    r_, g_, b_ = (int(hx[i:i+2], 16) for i in (0, 2, 4))
                    bg = Image.new("RGBA", img.size, (r_, g_, b_, 255))
                    bg.paste(img, mask=img.split()[3])
                    img = bg.convert("RGB")
                # else: transparent — keep RGBA as-is

                img.save(dst, "PNG", optimize=True)
                ok += 1
                self._q.put(("log", f"✓  {name}  →  {os.path.basename(dst)}"))
            except Exception as e:
                fail += 1
                self._q.put(("log", f"✗  {name}  —  {e}"))

            self._q.put(("progress", i / total))

        self._last_out = out_dir or first_out
        self._q.put(("status", f"✓  Done — {ok} processed, {fail} failed"))
        self._q.put(("done", out_dir or first_out))

    def _drain(self):
        try:
            while True:
                kind, data = self._q.get_nowait()
                if kind == "log":
                    self._log_msg(data)
                elif kind == "status":
                    self._status_lbl.configure(text=data)
                elif kind == "progress":
                    self._prog.set(data)
                elif kind == "done":
                    self._prog.set(1)
                    self._set_busy(False)
                    self._last_out = data
                    self._open_btn.configure(
                        state="normal" if data else "disabled")
        except queue.Empty:
            pass
        self.after(120, self._drain)
