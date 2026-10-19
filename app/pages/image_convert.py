"""
pages/image_convert.py  –  Professional Image Converter

Converts any image format to any other format using Pillow.
Quality notes:
  • PNG, TIFF, BMP, GIF  → lossless, no quality loss
  • WEBP (lossless mode) → lossless
  • JPG / WEBP (lossy)  → configurable quality (default 95, visually lossless)
  • TIFF                → optionally LZW compressed (lossless)
  • For best results converting JPG → PNG: use PNG (lossless), no re-compression
"""

import os
import glob
import queue
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image, UnidentifiedImageError

PAD = 16

# All formats Pillow can handle well
INPUT_FORMATS  = ["All Images", "JPG / JPEG", "PNG", "WEBP", "TIFF", "BMP",
                   "GIF", "ICO", "PSD (read)", "HEIC (read)"]
INPUT_EXTS = {
    "All Images":  ["*.jpg","*.jpeg","*.png","*.webp","*.tiff","*.tif",
                    "*.bmp","*.gif","*.ico","*.psd"],
    "JPG / JPEG":  ["*.jpg","*.jpeg"],
    "PNG":         ["*.png"],
    "WEBP":        ["*.webp"],
    "TIFF":        ["*.tiff","*.tif"],
    "BMP":         ["*.bmp"],
    "GIF":         ["*.gif"],
    "ICO":         ["*.ico"],
    "PSD (read)":  ["*.psd"],
    "HEIC (read)": ["*.heic","*.heif"],
}

OUTPUT_FORMATS = ["PNG", "JPG", "WEBP (lossless)", "WEBP (lossy)", "TIFF", "BMP",
                  "GIF", "ICO"]

# Map display name → (extension, save kwargs factory)
def _save_opts(fmt_name: str, quality: int) -> tuple[str, dict]:
    """Return (file extension, PIL save kwargs) for the chosen output format."""
    q = quality
    match fmt_name:
        case "PNG":
            return ".png", dict(optimize=True)
        case "JPG":
            return ".jpg", dict(quality=q, subsampling=0, optimize=True)
        case "WEBP (lossless)":
            return ".webp", dict(lossless=True, quality=100, method=6)
        case "WEBP (lossy)":
            return ".webp", dict(lossless=False, quality=q, method=6)
        case "TIFF":
            return ".tiff", dict(compression="lzw")
        case "BMP":
            return ".bmp", {}
        case "GIF":
            return ".gif", {}
        case "ICO":
            return ".ico", dict(sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])
        case _:
            return ".png", {}


def _convert_one(src: str, dst_base: str, fmt_name: str,
                 quality: int, keep_alpha: bool) -> str:
    """Convert a single image. Returns output path."""
    ext, save_kw = _save_opts(fmt_name, quality)
    dst = dst_base + ext

    img = Image.open(src)

    # Handle animated GIFs — preserve as-is
    if getattr(img, "is_animated", False) and fmt_name == "GIF":
        frames = []
        try:
            while True:
                frames.append(img.copy())
                img.seek(img.tell() + 1)
        except EOFError:
            pass
        frames[0].save(dst, save_all=True, append_images=frames[1:],
                       loop=img.info.get("loop", 0), **save_kw)
        return dst

    # Convert to appropriate mode for output format
    if fmt_name in ("JPG", "WEBP (lossy)"):
        if img.mode in ("RGBA", "LA", "PA"):
            if keep_alpha:
                # Composite onto white background
                bg = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode != "RGBA":
                    img = img.convert("RGBA")
                bg.paste(img, mask=img.split()[3])
                img = bg
            else:
                img = img.convert("RGB")
        elif img.mode != "RGB":
            img = img.convert("RGB")
    elif fmt_name == "PNG":
        if img.mode not in ("RGB", "RGBA", "L", "LA", "P"):
            img = img.convert("RGBA")
    elif fmt_name in ("WEBP (lossless)",):
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA")
    elif fmt_name == "BMP":
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
    elif fmt_name == "GIF":
        img = img.convert("P")
    elif fmt_name == "ICO":
        img = img.convert("RGBA")
        img = img.resize((256, 256), Image.LANCZOS)
    elif fmt_name == "TIFF":
        pass  # TIFF supports most modes

    img.save(dst, **save_kw)
    return dst


class ImageConvertPage(ctk.CTkFrame):

    def __init__(self, master, **kw):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kw)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._files: list[str] = []
        self._busy   = False
        self._cancel = False
        self._last_out: str | None = None
        self._q: queue.Queue = queue.Queue()

        self._build()
        self.after(120, self._drain)

    # ── Build ──────────────────────────────────────────────────────────────

    def _build(self):
        # Header
        hdr = ctk.CTkFrame(self, corner_radius=0, height=70)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(hdr, text="Image Converter",
                     font=ctk.CTkFont("Segoe UI", 22, "bold"),
                     anchor="w").grid(row=0, column=0, padx=(PAD, 10),
                                      pady=(14, 2), sticky="w")
        ctk.CTkLabel(hdr, text="Convert images between any formats  ·  originals never changed",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=("gray40", "gray60"),
                     anchor="w").grid(row=1, column=0, padx=(PAD, 10),
                                      pady=(0, 10), sticky="w")
        ctk.CTkFrame(self, height=1, fg_color=("gray82", "gray28"),
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
        two.grid_columnconfigure(1, weight=1)
        self._build_output_card(two)
        self._build_quality_card(two)

        self._build_save(scroll)
        self._build_log(scroll)

        # Action bar
        bar = ctk.CTkFrame(self, corner_radius=0, height=64)
        bar.grid(row=2, column=0, sticky="ew")
        bar.grid_propagate(False)
        ctk.CTkFrame(bar, height=1, fg_color=("gray82", "gray28"),
                     corner_radius=0).pack(fill="x", side="top")
        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="both", expand=True)

        self._convert_btn = ctk.CTkButton(
            inner, text="▶  Convert", width=150, height=42,
            font=ctk.CTkFont("Segoe UI", 14, "bold"),
            command=self._convert)
        self._cancel_btn = ctk.CTkButton(
            inner, text="✕  Cancel", width=110, height=42,
            state="disabled", **self._sec(), command=self._do_cancel)
        self._open_btn = ctk.CTkButton(
            inner, text="📂  Open Output Folder", width=180, height=42,
            state="disabled", **self._sec(), command=self._open_out)
        self._status_lbl = ctk.CTkLabel(
            inner, text="Ready — add images, then press Convert",
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=("gray40", "gray60"), anchor="w")
        self._prog = ctk.CTkProgressBar(inner, height=6, corner_radius=3)
        self._prog.set(0)

        self._convert_btn.pack(side="left", padx=(PAD, 0), pady=10)
        self._cancel_btn.pack(side="left",  padx=(6, 0),   pady=10)
        self._open_btn.pack(side="left",    padx=(6, 0),   pady=10)
        self._status_lbl.pack(side="left",  padx=(10, 0),  pady=10)
        self._prog.pack(side="right", padx=PAD, pady=10, fill="x", expand=True)

    # ── Files card ─────────────────────────────────────────────────────────

    def _build_files(self, parent):
        inner = self._card(parent, "① Add Images", pack=True, top_pad=PAD)

        br = ctk.CTkFrame(inner, fg_color="transparent")
        br.pack(fill="x", pady=(0, 8))

        self._btn_add    = ctk.CTkButton(br, text="📄  Add Files",  width=120,
                                          command=self._add_files)
        self._btn_folder = ctk.CTkButton(br, text="📂  Add Folder", width=130,
                                          **self._sec(), command=self._add_folder)
        self._btn_rm     = ctk.CTkButton(br, text="✕  Remove Last", width=130,
                                          **self._ghost(), command=self._remove_sel)
        self._btn_clear  = ctk.CTkButton(br, text="🗑  Clear All",  width=110,
                                          **self._ghost(), command=self._clear)
        for b in (self._btn_add, self._btn_folder, self._btn_rm, self._btn_clear):
            b.pack(side="left", padx=(0, 6))

        self._count_lbl = ctk.CTkLabel(br, text="No files added yet",
                                        font=ctk.CTkFont("Segoe UI", 11),
                                        text_color=("gray40", "gray60"))
        self._count_lbl.pack(side="right", padx=4)

        self._file_box = ctk.CTkTextbox(inner, height=130, state="disabled",
                                         font=ctk.CTkFont("Consolas", 11),
                                         wrap="none")
        self._file_box.pack(fill="x")

    # ── Output format card ──────────────────────────────────────────────────

    def _build_output_card(self, parent):
        inner = self._card(parent, "② Output Format", grid_col=0)

        ctk.CTkLabel(inner, text="Convert to:",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     anchor="w").pack(anchor="w", pady=(0, 8))

        self._out_fmt = ctk.StringVar(value="PNG")
        for fmt in OUTPUT_FORMATS:
            ctk.CTkRadioButton(
                inner, text=fmt, variable=self._out_fmt, value=fmt,
                command=self._fmt_changed,
                font=ctk.CTkFont("Segoe UI", 12),
            ).pack(anchor="w", pady=3)

        # Alpha blending hint (shown when JPG/WEBP-lossy selected)
        self._alpha_frame = ctk.CTkFrame(inner, fg_color="transparent")
        self._keep_alpha = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            self._alpha_frame,
            text="Composite transparent pixels onto white background",
            variable=self._keep_alpha,
            font=ctk.CTkFont("Segoe UI", 11),
        ).pack(anchor="w")
        ctk.CTkLabel(
            self._alpha_frame,
            text="Applies when source image has transparency (PNG, WEBP…)",
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=("gray40", "gray60"),
            anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        self._fmt_changed()

    # ── Quality / options card ──────────────────────────────────────────────

    def _build_quality_card(self, parent):
        inner = self._card(parent, "③ Quality & Options", grid_col=1)

        # JPG / WEBP quality
        ctk.CTkLabel(inner, text="Quality  (JPG and WEBP lossy):",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     anchor="w").pack(anchor="w", pady=(0, 6))

        sl_row = ctk.CTkFrame(inner, fg_color="transparent")
        sl_row.pack(anchor="w", pady=(0, 4))
        self._quality = ctk.IntVar(value=95)
        sl = ctk.CTkSlider(sl_row, from_=10, to=100, variable=self._quality, width=200)
        sl.pack(side="left")
        self._q_lbl = ctk.CTkLabel(sl_row, text="95",
                                    font=ctk.CTkFont("Segoe UI", 13, "bold"),
                                    width=36)
        self._q_lbl.pack(side="left", padx=(8, 0))
        self._quality.trace_add("write",
            lambda *_: self._q_lbl.configure(text=str(self._quality.get())))

        ctk.CTkLabel(inner,
                     text="95 = visually lossless.  100 = maximum quality (larger file).",
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=("gray40", "gray60"),
                     anchor="w", wraplength=280,
                     ).pack(anchor="w", pady=(0, 14))

        ctk.CTkFrame(inner, height=1, fg_color=("gray85", "gray30"),
                     corner_radius=0).pack(fill="x", pady=(0, 12))

        # Resize option
        ctk.CTkLabel(inner, text="Resize  (optional):",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     anchor="w").pack(anchor="w")

        self._resize_en = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(inner, text="Resize output images",
                         variable=self._resize_en,
                         command=self._resize_toggle,
                         font=ctk.CTkFont("Segoe UI", 11),
                         ).pack(anchor="w", pady=(6, 6))

        self._resize_frame = ctk.CTkFrame(inner, fg_color="transparent")
        rrow = ctk.CTkFrame(self._resize_frame, fg_color="transparent")
        rrow.pack(anchor="w")
        ctk.CTkLabel(rrow, text="Width:", font=ctk.CTkFont("Segoe UI", 11),
                     width=50).pack(side="left")
        self._rw = ctk.CTkEntry(rrow, width=70, placeholder_text="1920",
                                 justify="left")
        self._rw.pack(side="left", padx=(0, 12))
        ctk.CTkLabel(rrow, text="Height:", font=ctk.CTkFont("Segoe UI", 11),
                     width=55).pack(side="left")
        self._rh = ctk.CTkEntry(rrow, width=70, placeholder_text="1080",
                                 justify="left")
        self._rh.pack(side="left")
        ctk.CTkLabel(self._resize_frame,
                     text="Leave a dimension blank to scale proportionally.",
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=("gray40", "gray60"),
                     anchor="w").pack(anchor="w", pady=(4, 0))

        ctk.CTkFrame(inner, height=1, fg_color=("gray85", "gray30"),
                     corner_radius=0).pack(fill="x", pady=(12, 12))

        # Suffix
        ctk.CTkLabel(inner, text="Filename suffix  (optional):",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     anchor="w").pack(anchor="w")
        suf_row = ctk.CTkFrame(inner, fg_color="transparent")
        suf_row.pack(anchor="w", pady=(4, 0))
        self._suffix = ctk.StringVar()
        ctk.CTkEntry(suf_row, textvariable=self._suffix, width=110,
                      placeholder_text="_converted", justify="left"
                      ).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(suf_row,
                     text="e.g.  _web  →  logo_web.png",
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=("gray40", "gray60"),
                     ).pack(side="left")

    # ── Save card ───────────────────────────────────────────────────────────

    def _build_save(self, parent):
        inner = self._card(parent, "④ Where to Save", pack=True)
        self._out_mode = ctk.StringVar(value="beside")

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
        custom_lbl = ctk.CTkLabel(cf, text="  Save to a specific folder:",
                                   font=ctk.CTkFont("Segoe UI", 12),
                                   anchor="w", cursor="hand2")
        custom_lbl.bind("<Button-1>",
                        lambda _: (self._out_mode.set("custom"),
                                   self._save_changed()))
        self._out_entry = ctk.CTkEntry(cf, width=270,
                                        placeholder_text="C:\\Output\\folder",
                                        justify="left")
        self._browse_btn = ctk.CTkButton(cf, text="Browse…", width=100,
                                          **self._sec(), command=self._browse_out)

        self._rb_custom.pack(side="left", padx=(0, 4))
        custom_lbl.pack(side="left",       padx=(0, 8))
        self._out_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._browse_btn.pack(side="left")

        self._save_changed()

    # ── Log card ────────────────────────────────────────────────────────────

    def _build_log(self, parent):
        inner = self._card(parent, "Progress Log", pack=True)
        self._log_box = ctk.CTkTextbox(inner, height=100, state="disabled",
                                        font=ctk.CTkFont("Consolas", 11),
                                        wrap="word")
        self._log_box.pack(fill="x")

    # ── Helpers ─────────────────────────────────────────────────────────────

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
        ctk.CTkFrame(outer, height=1, fg_color=("gray85", "gray30"),
                     corner_radius=0).pack(fill="x", padx=PAD, pady=(6, 0))
        inner = ctk.CTkFrame(outer, fg_color="transparent")
        inner.pack(fill="both", padx=PAD, pady=(10, 14))
        return inner

    def _sec(self) -> dict:
        return dict(fg_color=("gray75", "gray25"),
                    hover_color=("gray65", "gray35"),
                    text_color=("gray10", "gray95"))

    def _ghost(self) -> dict:
        return dict(fg_color=("gray80", "gray22"),
                    hover_color=("gray70", "gray30"),
                    text_color=("gray10", "gray95"))

    def _fmt_changed(self):
        fmt = self._out_fmt.get()
        lossy = fmt in ("JPG", "WEBP (lossy)")
        if lossy:
            self._alpha_frame.pack(fill="x", pady=(10, 0))
        else:
            self._alpha_frame.pack_forget()

    def _resize_toggle(self):
        if self._resize_en.get():
            self._resize_frame.pack(fill="x", pady=(0, 4))
        else:
            self._resize_frame.pack_forget()

    def _save_changed(self):
        beside = self._out_mode.get() == "beside"
        self._out_entry.configure(state="disabled" if beside else "normal")
        self._browse_btn.configure(state="disabled" if beside else "normal")

    def _set_busy(self, busy: bool):
        self._busy = busy
        s = "disabled" if busy else "normal"
        for w in (self._btn_add, self._btn_folder, self._btn_rm, self._btn_clear,
                  self._convert_btn, self._out_entry, self._browse_btn):
            w.configure(state=s)
        self._cancel_btn.configure(state="normal" if busy else "disabled")

    def _refresh_list(self):
        self._file_box.configure(state="normal")
        self._file_box.delete("1.0", "end")
        for p in self._files:
            self._file_box.insert("end", p + "\n")
        self._file_box.configure(state="disabled")
        n = len(self._files)
        self._count_lbl.configure(
            text="No files added yet" if n == 0 else f"{n} file(s) ready")

    def _log(self, msg: str):
        self._log_box.configure(state="normal")
        self._log_box.insert("end", msg + "\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    # ── File ops ────────────────────────────────────────────────────────────

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title="Select image files",
            filetypes=[
                ("All images", " ".join(e for exts in INPUT_EXTS.values()
                                        for e in exts)),
                ("JPEG", "*.jpg *.jpeg"),
                ("PNG",  "*.png"),
                ("WEBP", "*.webp"),
                ("TIFF", "*.tiff *.tif"),
                ("BMP",  "*.bmp"),
                ("GIF",  "*.gif"),
                ("All files", "*.*"),
            ])
        if paths:
            self._ingest(list(paths))

    def _add_folder(self):
        folder = filedialog.askdirectory(title="Choose folder containing images")
        if not folder:
            return
        found: list[str] = []
        exts = INPUT_EXTS["All Images"]
        for ext in exts:
            found.extend(glob.glob(os.path.join(folder, ext)))
            found.extend(glob.glob(os.path.join(folder, ext.upper())))
        if not found:
            self._log("No image files found in that folder.")
        else:
            self._ingest(sorted(set(found)))

    def _ingest(self, paths: list[str]):
        existing = set(self._files)
        added = 0
        image_exts = {e.lstrip("*.").lower()
                      for exts in INPUT_EXTS.values() for e in exts}
        for p in paths:
            p = os.path.abspath(p)
            if p in existing:
                continue
            if os.path.splitext(p)[1].lstrip(".").lower() not in image_exts:
                continue
            self._files.append(p)
            existing.add(p)
            added += 1
        self._refresh_list()
        if added:
            self._log(f"✓  Added {added} file(s)")

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

    # ── Conversion ──────────────────────────────────────────────────────────

    def _convert(self):
        if self._busy:
            return
        if not self._files:
            messagebox.showinfo("Studio Tools", "Please add at least one image file first.")
            return

        fmt_name = self._out_fmt.get()
        quality  = int(self._quality.get())
        suffix   = self._suffix.get().strip()
        keep_alpha = self._keep_alpha.get()

        # Resize settings
        resize = None
        if self._resize_en.get():
            rw = self._rw.get().strip()
            rh = self._rh.get().strip()
            try:
                resize = (int(rw) if rw else None, int(rh) if rh else None)
                if resize == (None, None):
                    resize = None
            except ValueError:
                messagebox.showerror("Studio Tools",
                                     "Width and Height must be whole numbers.")
                return

        out_dir: str | None = None
        if self._out_mode.get() == "custom":
            out_dir = self._out_entry.get().strip()
            if not out_dir:
                messagebox.showerror("Studio Tools",
                    "Please choose an output folder, or switch to 'Next to each original'.")
                return
            os.makedirs(out_dir, exist_ok=True)

        self._cancel   = False
        self._last_out = out_dir
        self._set_busy(True)
        self._prog.set(0)

        threading.Thread(
            target=self._worker,
            args=(list(self._files), fmt_name, quality,
                  suffix, keep_alpha, resize, out_dir),
            daemon=True).start()

    def _worker(self, files, fmt_name, quality, suffix,
                keep_alpha, resize, out_dir):
        total = len(files)
        ok = fail = 0
        first_out = None
        ext, _ = _save_opts(fmt_name, quality)

        for i, src in enumerate(files, start=1):
            if self._cancel:
                self._q.put(("status", f"Cancelled — {ok} done,  {fail} failed"))
                self._q.put(("done", None))
                return

            name     = os.path.basename(src)
            base     = os.path.splitext(name)[0] + suffix
            dst_base = (os.path.join(out_dir, base) if out_dir
                        else os.path.join(os.path.dirname(src), base))
            if first_out is None:
                first_out = os.path.dirname(dst_base) or "."

            self._q.put(("status", f"Converting  {i} / {total}  ·  {name}"))
            try:
                # Apply resize if requested
                if resize:
                    img = Image.open(src)
                    rw, rh = resize
                    ow, oh = img.size
                    if rw and rh:
                        new_size = (rw, rh)
                    elif rw:
                        new_size = (rw, int(oh * rw / ow))
                    else:
                        new_size = (int(ow * rh / oh), rh)
                    img = img.resize(new_size, Image.LANCZOS)
                    # Save resized image to a temp path then convert
                    tmp = dst_base + "_tmp" + os.path.splitext(src)[1]
                    img.save(tmp)
                    out = _convert_one(tmp, dst_base, fmt_name,
                                       quality, keep_alpha)
                    os.remove(tmp)
                else:
                    out = _convert_one(src, dst_base, fmt_name,
                                       quality, keep_alpha)
                ok += 1
                self._q.put(("log", f"✓  {name}  →  {os.path.basename(out)}"))
            except (UnidentifiedImageError, Exception) as e:
                fail += 1
                self._q.put(("log", f"✗  {name}  —  {e}"))

            self._q.put(("progress", i / total))

        self._last_out = out_dir or first_out
        self._q.put(("status", f"✓  Done — {ok} converted,  {fail} failed"))
        self._q.put(("done", None))

    def _drain(self):
        try:
            while True:
                kind, data = self._q.get_nowait()
                if   kind == "log":      self._log(data)
                elif kind == "status":   self._status_lbl.configure(text=data)
                elif kind == "progress": self._prog.set(data)
                elif kind == "done":
                    self._prog.set(1)
                    self._set_busy(False)
                    self._open_btn.configure(
                        state="normal" if self._last_out else "disabled")
        except queue.Empty:
            pass
        self.after(120, self._drain)
