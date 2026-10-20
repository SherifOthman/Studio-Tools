"""
pages/batch_rename.py  –  Batch Rename (simple, visual, user-friendly)

Layout:
  Left  (40%)  : Files list + rule controls (simple form, no tabs)
  Right (60%)  : Live preview table — always visible, updates instantly
                 Shows up to 8 sample filenames from the list with
                 Before → After columns so you see the effect immediately.

Rules available (most common scenarios):
  • Prefix / Suffix
  • Find & Replace (plain or regex)
  • Sequential numbering (with position and padding)
  • Case change
  • Spaces ↔ underscores / dashes
  • Trim / clean up spaces

Undo is always one click away after renaming.
"""

import os
import re
import glob
import queue
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk

from app.core.palette import (CHIP, CHIP_HOVER, CHIP_TEXT, DIVIDER, EDGE,
                              GHOST, GHOST_HOVER, GHOST_TEXT,
                              ROW, SEC, SEC_HOVER, SEC_TEXT,
                              TEXT, TEXT_DISABLED, TEXT_SUB)

PAD = 16
PREVIEW_ROWS = 8          # how many sample filenames to show in preview
SEC_BORDER   = ("#94A3B8", "gray45")


# ── Pure rename engine (no tkinter) ───────────────────────────────────────

def build_new_name(original: str, opts: dict, counter: int) -> str:
    """Apply all active options and return the new filename."""
    base, ext = os.path.splitext(original)

    # ── Prefix ───────────────────────────────────────────────────────────
    pfx = opts.get("prefix", "").strip()
    if pfx:
        base = pfx + base

    # ── Suffix ───────────────────────────────────────────────────────────
    sfx = opts.get("suffix", "").strip()
    if sfx:
        base = base + sfx

    # ── Find & replace ───────────────────────────────────────────────────
    find    = opts.get("find", "")
    replace = opts.get("replace", "")
    if find:
        if opts.get("regex"):
            try:
                flags = 0 if opts.get("case_sensitive") else re.IGNORECASE
                base = re.sub(find, replace, base, flags=flags)
            except re.error:
                pass
        else:
            if opts.get("case_sensitive"):
                base = base.replace(find, replace)
            else:
                base = re.sub(re.escape(find), replace, base, flags=re.IGNORECASE)

    # ── Spaces normalise ─────────────────────────────────────────────────
    space_to = opts.get("space_to", "")   # "underscore" | "dash" | "dot" | ""
    if space_to == "underscore":
        base = base.replace(" ", "_")
    elif space_to == "dash":
        base = base.replace(" ", "-")
    elif space_to == "dot":
        base = base.replace(" ", ".")
    elif space_to == "trim":
        base = " ".join(base.split())

    # ── Case ─────────────────────────────────────────────────────────────
    case = opts.get("case", "")
    if case == "upper":
        base = base.upper()
    elif case == "lower":
        base = base.lower()
    elif case == "title":
        base = base.title()

    # ── Sequential number ─────────────────────────────────────────────────
    if opts.get("number_enabled"):
        start = int(opts.get("num_start", 1) or 1)
        step  = int(opts.get("num_step",  1) or 1)
        pad   = int(opts.get("num_pad",   2) or 2)
        sep   = opts.get("num_sep", "_") or "_"
        pos   = opts.get("num_pos", "suffix")
        n     = start + counter * step
        num_s = str(n).zfill(pad)
        if pos == "prefix":
            base = num_s + sep + base
        elif pos == "replace":
            base = num_s
        else:
            base = base + sep + num_s

    # ── Extension ────────────────────────────────────────────────────────
    ext_op = opts.get("ext_op", "keep")
    if ext_op == "lower":
        ext = ext.lower()
    elif ext_op == "upper":
        ext = ext.upper()

    # Sanitise
    for ch in r'\/:*?"<>|':
        base = base.replace(ch, "_")
    result = base + ext
    return result if result.strip(". ") else original


# ── UI ─────────────────────────────────────────────────────────────────────

class BatchRenamePage(ctk.CTkFrame):

    def __init__(self, master, **kw):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kw)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._files: list[str] = []
        self._undo_map: dict[str, str] | None = None
        self._busy   = False
        self._cancel = False
        self._q: queue.Queue = queue.Queue()

        self._build()
        self.after(120, self._drain)

    # ── Layout ─────────────────────────────────────────────────────────────

    def _build(self):
        # Header
        hdr = ctk.CTkFrame(self, corner_radius=0, height=70)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(hdr, text="Batch Rename",
                     font=ctk.CTkFont("Segoe UI", 22, "bold"),
                     anchor="w").grid(row=0, column=0, padx=(PAD, 10),
                                      pady=(14, 2), sticky="w")
        ctk.CTkLabel(hdr, text="Rename files in bulk  ·  results update live as you type",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=TEXT_SUB, anchor="w").grid(
            row=1, column=0, padx=(PAD, 10), pady=(0, 10), sticky="w")
        ctk.CTkFrame(self, height=1, fg_color=EDGE,
                     corner_radius=0).grid(row=0, column=0, sticky="sew")

        # Two-column body
        body = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=5)   # left: files + options
        body.grid_columnconfigure(1, weight=0, minsize=1)
        body.grid_columnconfigure(2, weight=6)   # right: preview

        left = ctk.CTkScrollableFrame(body, corner_radius=0,
                                       fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkFrame(body, width=1, corner_radius=0,
                     fg_color=EDGE).grid(row=0, column=1, sticky="nsew")

        right = ctk.CTkFrame(body, corner_radius=0, fg_color="transparent")
        right.grid(row=0, column=2, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self._build_left(left)
        self._build_right(right)

        # Action bar
        bar = ctk.CTkFrame(self, corner_radius=0, height=64)
        bar.grid(row=2, column=0, sticky="ew")
        bar.grid_propagate(False)
        ctk.CTkFrame(bar, height=1, fg_color=EDGE,
                     corner_radius=0).pack(fill="x", side="top")
        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="both", expand=True)

        self._rename_btn = ctk.CTkButton(
            inner, text="▶  Rename Files", width=150, height=42,
            font=ctk.CTkFont("Segoe UI", 14, "bold"),
            command=self._rename)
        self._undo_btn = ctk.CTkButton(
            inner, text="↩  Undo", width=100, height=42,
            state="disabled",
            fg_color=SEC, hover_color=SEC_HOVER, text_color=SEC_TEXT,
            text_color_disabled=TEXT_DISABLED,
            command=self._undo)
        self._cancel_btn = ctk.CTkButton(
            inner, text="✕  Cancel", width=100, height=42,
            state="disabled",
            fg_color=SEC, hover_color=SEC_HOVER, text_color=SEC_TEXT,
            text_color_disabled=TEXT_DISABLED,
            command=lambda: setattr(self, "_cancel", True))
        self._status_lbl = ctk.CTkLabel(
            inner, text="Add files, fill in the options, then press Rename.",
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=TEXT_SUB, anchor="w")
        self._prog = ctk.CTkProgressBar(inner, height=6, corner_radius=3)
        self._prog.set(0)

        self._rename_btn.pack(side="left", padx=(PAD, 0), pady=10)
        self._undo_btn.pack(  side="left", padx=(8,  0), pady=10)
        self._cancel_btn.pack(side="left", padx=(6,  0), pady=10)
        self._status_lbl.pack(side="left", padx=(12, 0), pady=10)
        self._prog.pack(side="right", padx=PAD, pady=10,
                        fill="x", expand=True)

    # ── Left panel: files + options ────────────────────────────────────────

    def _build_left(self, parent):
        # Files section
        fc = self._card(parent, "① Files")
        btn_row = ctk.CTkFrame(fc, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 8))

        self._btn_add_f = ctk.CTkButton(btn_row, text="📄  Add Files", width=120,
                                         command=self._add_files)
        self._btn_add_d = ctk.CTkButton(btn_row, text="📂  Add Folder", width=130,
                                         fg_color=SEC, hover_color=SEC_HOVER,
                                         text_color=SEC_TEXT,
                                         text_color_disabled=TEXT_DISABLED,
                                         command=self._add_folder)
        self._btn_clear = ctk.CTkButton(btn_row, text="🗑  Clear", width=80,
                                         fg_color=GHOST, hover_color=GHOST_HOVER,
                                         text_color=GHOST_TEXT,
                                         text_color_disabled=TEXT_DISABLED,
                                         command=self._clear_files)
        self._count_lbl = ctk.CTkLabel(btn_row, text="0 files",
                                        font=ctk.CTkFont("Segoe UI", 11),
                                        text_color=TEXT_SUB)
        for b in (self._btn_add_f, self._btn_add_d, self._btn_clear):
            b.pack(side="left", padx=(0, 6))
        self._count_lbl.pack(side="right", padx=4)

        self._file_box = ctk.CTkTextbox(fc, height=110, state="disabled",
                                         font=ctk.CTkFont("Consolas", 10),
                                         wrap="none")
        self._file_box.pack(fill="x")

        # Options section
        oc = self._card(parent, "② Rename Options")

        def row_lbl(p, text):
            ctk.CTkLabel(p, text=text,
                         font=ctk.CTkFont("Segoe UI", 11, "bold"),
                         anchor="w", width=100).pack(side="left")

        def opt_row(p):
            f = ctk.CTkFrame(p, fg_color="transparent")
            f.pack(fill="x", pady=4)
            return f

        # Prefix
        r = opt_row(oc)
        row_lbl(r, "Add Prefix:")
        self._pfx = ctk.StringVar()
        ctk.CTkEntry(r, textvariable=self._pfx,
                      placeholder_text="e.g. 2024_").pack(
            side="left", fill="x", expand=True)
        self._pfx.trace_add("write", lambda *_: self._refresh_preview())

        # Suffix
        r = opt_row(oc)
        row_lbl(r, "Add Suffix:")
        self._sfx = ctk.StringVar()
        ctk.CTkEntry(r, textvariable=self._sfx,
                      placeholder_text="e.g. _final").pack(
            side="left", fill="x", expand=True)
        self._sfx.trace_add("write", lambda *_: self._refresh_preview())

        # Find & Replace
        ctk.CTkFrame(oc, height=1, fg_color=DIVIDER,
                     corner_radius=0).pack(fill="x", pady=(8, 6))
        r = opt_row(oc)
        row_lbl(r, "Find:")
        self._find = ctk.StringVar()
        ctk.CTkEntry(r, textvariable=self._find).pack(
            side="left", fill="x", expand=True)
        self._find.trace_add("write", lambda *_: self._refresh_preview())

        r = opt_row(oc)
        row_lbl(r, "Replace with:")
        self._repl = ctk.StringVar()
        ctk.CTkEntry(r, textvariable=self._repl,
                      placeholder_text="(leave blank to delete)").pack(
            side="left", fill="x", expand=True)
        self._repl.trace_add("write", lambda *_: self._refresh_preview())

        chk_row = ctk.CTkFrame(oc, fg_color="transparent")
        chk_row.pack(anchor="w", pady=(2, 0))
        self._regex     = ctk.BooleanVar(value=False)
        self._case_sens = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(chk_row, text="Regex",
                         variable=self._regex,
                         command=self._refresh_preview,
                         font=ctk.CTkFont("Segoe UI", 11)
                         ).pack(side="left", padx=(0, 16))
        ctk.CTkCheckBox(chk_row, text="Case sensitive",
                         variable=self._case_sens,
                         command=self._refresh_preview,
                         font=ctk.CTkFont("Segoe UI", 11)
                         ).pack(side="left")

        # Spaces
        ctk.CTkFrame(oc, height=1, fg_color=DIVIDER,
                     corner_radius=0).pack(fill="x", pady=(8, 6))
        r = opt_row(oc)
        row_lbl(r, "Spaces:")
        self._space_to = ctk.StringVar(value="")
        seg = ctk.CTkSegmentedButton(
            r,
            values=["Keep", "_ Underscore", "- Dash", "Trim"],
            command=lambda _: self._refresh_preview(),
            font=ctk.CTkFont("Segoe UI", 10),
            height=30,
            variable=self._space_to,
        )
        # Map display → internal value
        self._space_map = {
            "Keep": "",
            "_ Underscore": "underscore",
            "- Dash": "dash",
            "Trim": "trim",
        }
        seg.set("Keep")
        seg.pack(side="left", fill="x", expand=True)

        # Case
        ctk.CTkFrame(oc, height=1, fg_color=DIVIDER,
                     corner_radius=0).pack(fill="x", pady=(8, 6))
        r = opt_row(oc)
        row_lbl(r, "Case:")
        self._case = ctk.StringVar(value="keep")
        case_seg = ctk.CTkSegmentedButton(
            r,
            values=["Keep", "UPPER", "lower", "Title"],
            command=lambda _: self._refresh_preview(),
            font=ctk.CTkFont("Segoe UI", 10),
            height=30,
            variable=self._case,
        )
        self._case_map = {
            "Keep": "keep", "UPPER": "upper",
            "lower": "lower", "Title": "title",
        }
        case_seg.set("Keep")
        case_seg.pack(side="left", fill="x", expand=True)

        # Sequential numbers
        ctk.CTkFrame(oc, height=1, fg_color=DIVIDER,
                     corner_radius=0).pack(fill="x", pady=(8, 6))

        num_hdr = ctk.CTkFrame(oc, fg_color="transparent")
        num_hdr.pack(fill="x", pady=(0, 6))
        self._num_en = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(num_hdr, text="Add sequential numbers",
                         variable=self._num_en,
                         command=self._toggle_num,
                         font=ctk.CTkFont("Segoe UI", 11, "bold")
                         ).pack(side="left")

        self._num_frame = ctk.CTkFrame(oc, fg_color="transparent")
        # Not packed until enabled

        nf = self._num_frame
        def nrow():
            f = ctk.CTkFrame(nf, fg_color="transparent")
            f.pack(fill="x", pady=3)
            return f

        r = nrow()
        ctk.CTkLabel(r, text="Position:", width=80, anchor="w",
                     font=ctk.CTkFont("Segoe UI", 11)).pack(side="left")
        self._num_pos = ctk.StringVar(value="suffix")
        for v, lbl in (("prefix", "Before name"), ("suffix", "After name"),
                        ("replace", "Replace name")):
            ctk.CTkRadioButton(r, text=lbl, variable=self._num_pos,
                                value=v, command=self._refresh_preview,
                                font=ctk.CTkFont("Segoe UI", 11),
                                ).pack(side="left", padx=(0, 12))

        r = nrow()
        for lbl, attr, ph in (("Start:", "_num_start", "1"),
                               ("Step:",  "_num_step",  "1"),
                               ("Pad (digits):", "_num_pad", "2"),
                               ("Separator:", "_num_sep", "_")):
            ctk.CTkLabel(r, text=lbl, anchor="w",
                         font=ctk.CTkFont("Segoe UI", 11),
                         width=95).pack(side="left")
            v = ctk.StringVar(value=ph)
            setattr(self, attr, v)
            ctk.CTkEntry(r, textvariable=v, width=52,
                          justify="left").pack(side="left", padx=(0, 10))
            v.trace_add("write", lambda *_: self._refresh_preview())

        # Extension
        ctk.CTkFrame(oc, height=1, fg_color=DIVIDER,
                     corner_radius=0).pack(fill="x", pady=(8, 6))
        r = opt_row(oc)
        row_lbl(r, "Extension:")
        self._ext_op = ctk.StringVar(value="keep")
        ext_seg = ctk.CTkSegmentedButton(
            r,
            values=["Keep", ".lowercase", ".UPPERCASE"],
            command=lambda _: self._refresh_preview(),
            font=ctk.CTkFont("Segoe UI", 10),
            height=30,
            variable=self._ext_op,
        )
        self._ext_map = {
            "Keep": "keep", ".lowercase": "lower", ".UPPERCASE": "upper",
        }
        ext_seg.set("Keep")
        ext_seg.pack(side="left", fill="x", expand=True)

    # ── Right panel: preview ───────────────────────────────────────────────

    def _build_right(self, parent):
        hdr = ctk.CTkFrame(parent, corner_radius=0, height=48,
                            fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=PAD,
                 pady=(PAD, 0))
        ctk.CTkLabel(hdr, text="Live Preview  (first 8 files)",
                     font=ctk.CTkFont("Segoe UI", 13, "bold"),
                     anchor="w").pack(side="left")
        self._conflict_lbl = ctk.CTkLabel(
            hdr, text="",
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=("#DC2626", "#F87171"))
        self._conflict_lbl.pack(side="right")

        # Column headers
        col_hdr = ctk.CTkFrame(parent, corner_radius=0,
                                fg_color=("gray88", "gray22"), height=28)
        col_hdr.grid(row=1, column=0, sticky="ew", padx=PAD)
        col_hdr.grid_propagate(False)
        ctk.CTkLabel(col_hdr, text="ORIGINAL",
                     font=ctk.CTkFont("Segoe UI", 10, "bold"),
                     text_color=TEXT_SUB, anchor="w").pack(
            side="left", padx=10, fill="x", expand=True)
        ctk.CTkLabel(col_hdr, text="NEW NAME",
                     font=ctk.CTkFont("Segoe UI", 10, "bold"),
                     text_color=TEXT_SUB, anchor="w").pack(
            side="right", padx=10, fill="x", expand=True)

        # Preview rows container
        self._prev_container = ctk.CTkScrollableFrame(
            parent, corner_radius=0, fg_color="transparent")
        self._prev_container.grid(row=2, column=0, sticky="nsew",
                                   padx=PAD, pady=(4, PAD))
        parent.grid_rowconfigure(2, weight=1)
        self._prev_container.grid_columnconfigure(0, weight=1)
        self._prev_rows: list[ctk.CTkFrame] = []

    # ── Card helper ────────────────────────────────────────────────────────

    def _card(self, parent, title: str) -> ctk.CTkFrame:
        outer = ctk.CTkFrame(parent, corner_radius=12)
        outer.pack(fill="x", padx=PAD, pady=(PAD, 0))
        ctk.CTkLabel(outer, text=title,
                     font=ctk.CTkFont("Segoe UI", 13, "bold"),
                     anchor="w").pack(anchor="w", padx=PAD, pady=(12, 0))
        ctk.CTkFrame(outer, height=1, fg_color=DIVIDER,
                     corner_radius=0).pack(fill="x", padx=PAD, pady=(6, 0))
        inner = ctk.CTkFrame(outer, fg_color="transparent")
        inner.pack(fill="both", padx=PAD, pady=(10, 14))
        return inner

    # ── Options helpers ────────────────────────────────────────────────────

    def _toggle_num(self):
        if self._num_en.get():
            self._num_frame.pack(fill="x", pady=(0, 4))
        else:
            self._num_frame.pack_forget()
        self._refresh_preview()

    def _get_opts(self) -> dict:
        """Collect all option values into a dict for the rename engine."""
        return {
            "prefix":         self._pfx.get(),
            "suffix":         self._sfx.get(),
            "find":           self._find.get(),
            "replace":        self._repl.get(),
            "regex":          self._regex.get(),
            "case_sensitive": self._case_sens.get(),
            "space_to":       self._space_map.get(self._space_to.get(), ""),
            "case":           self._case_map.get(self._case.get(), "keep"),
            "number_enabled": self._num_en.get(),
            "num_start":      self._num_start.get() if self._num_en.get() else "1",
            "num_step":       self._num_step.get()  if self._num_en.get() else "1",
            "num_pad":        self._num_pad.get()   if self._num_en.get() else "2",
            "num_sep":        self._num_sep.get()   if self._num_en.get() else "_",
            "num_pos":        self._num_pos.get()   if self._num_en.get() else "suffix",
            "ext_op":         self._ext_map.get(self._ext_op.get(), "keep"),
        }

    # ── Preview ────────────────────────────────────────────────────────────

    def _refresh_preview(self, *_):
        # Clear old rows
        for w in self._prev_rows:
            w.destroy()
        self._prev_rows.clear()

        if not self._files:
            lbl = ctk.CTkLabel(self._prev_container,
                                text="Add files to see preview here.",
                                font=ctk.CTkFont("Segoe UI", 11),
                                text_color=TEXT_SUB)
            lbl.pack(anchor="w", padx=4, pady=8)
            self._prev_rows.append(lbl)
            self._conflict_lbl.configure(text="")
            return

        opts = self._get_opts()
        sample = self._files[:PREVIEW_ROWS]
        all_new = [build_new_name(os.path.basename(p), opts, i)
                   for i, p in enumerate(sample)]

        # Check conflicts in the full list (not just sample)
        all_new_full = [build_new_name(os.path.basename(p), opts, i)
                        for i, p in enumerate(self._files)]
        seen: dict[str, int] = {}
        for n in all_new_full:
            seen[n] = seen.get(n, 0) + 1
        conflicts = {n for n, c in seen.items() if c > 1}

        if conflicts:
            self._conflict_lbl.configure(
                text=f"⚠  {len(conflicts)} naming conflict(s)")
        else:
            self._conflict_lbl.configure(text="✓  No conflicts")

        for orig_path, new_name in zip(sample, all_new):
            orig = os.path.basename(orig_path)
            is_same     = (new_name == orig)
            is_conflict = (new_name in conflicts)

            row = ctk.CTkFrame(self._prev_container, corner_radius=6,
                                fg_color=("gray90", "gray20") if is_same else
                                         ("#FEE2E2", "#3B1111") if is_conflict else
                                         ("#F0FDF4", "#0F2B1A"))
            row.pack(fill="x", pady=(0, 3))
            row.grid_columnconfigure(0, weight=1)
            row.grid_columnconfigure(1, weight=0)
            row.grid_columnconfigure(2, weight=1)
            self._prev_rows.append(row)

            orig_color = TEXT_SUB if is_same else ("#374151", "#9CA3AF")
            new_color  = TEXT_SUB if is_same else \
                         ("#DC2626", "#F87171") if is_conflict else \
                         ("#16A34A", "#4ADE80")

            ctk.CTkLabel(row, text=orig,
                         font=ctk.CTkFont("Consolas", 10),
                         text_color=orig_color, anchor="w",
                         wraplength=0).grid(
                row=0, column=0, sticky="w", padx=(8, 4), pady=5)

            ctk.CTkLabel(row, text="→",
                         font=ctk.CTkFont("Segoe UI", 10),
                         text_color=TEXT_SUB).grid(
                row=0, column=1, padx=4)

            ctk.CTkLabel(row, text=new_name,
                         font=ctk.CTkFont("Consolas", 10, "bold"),
                         text_color=new_color, anchor="w",
                         wraplength=0).grid(
                row=0, column=2, sticky="w", padx=(4, 8), pady=5)

        if len(self._files) > PREVIEW_ROWS:
            info = ctk.CTkLabel(
                self._prev_container,
                text=f"  … and {len(self._files) - PREVIEW_ROWS} more file(s) "
                     f"— all will be renamed.",
                font=ctk.CTkFont("Segoe UI", 10),
                text_color=TEXT_SUB, anchor="w")
            info.pack(anchor="w", padx=4, pady=(4, 0))
            self._prev_rows.append(info)

    # ── File operations ────────────────────────────────────────────────────

    def _add_files(self):
        paths = filedialog.askopenfilenames(title="Select files to rename")
        if paths:
            self._ingest(list(paths))

    def _add_folder(self):
        folder = filedialog.askdirectory(title="Choose folder")
        if not folder:
            return
        files = sorted([os.path.join(folder, f)
                        for f in os.listdir(folder)
                        if os.path.isfile(os.path.join(folder, f))])
        self._ingest(files)

    def _ingest(self, paths: list[str]):
        existing = set(self._files)
        for p in paths:
            p = os.path.abspath(p)
            if p not in existing:
                self._files.append(p)
                existing.add(p)
        self._refresh_file_box()
        self._refresh_preview()

    def _clear_files(self):
        self._files.clear()
        self._refresh_file_box()
        self._refresh_preview()

    def _refresh_file_box(self):
        self._file_box.configure(state="normal")
        self._file_box.delete("1.0", "end")
        for p in self._files:
            self._file_box.insert("end", os.path.basename(p) + "\n")
        self._file_box.configure(state="disabled")
        n = len(self._files)
        self._count_lbl.configure(
            text="0 files" if n == 0 else f"{n} file(s)")

    # ── Rename ─────────────────────────────────────────────────────────────

    def _rename(self):
        if self._busy:
            return
        if not self._files:
            messagebox.showinfo("Studio Tools",
                                "Add some files to rename first.")
            return

        opts = self._get_opts()
        new_names = [build_new_name(os.path.basename(p), opts, i)
                     for i, p in enumerate(self._files)]

        # Conflict check
        seen: dict[str, int] = {}
        for n in new_names:
            seen[n] = seen.get(n, 0) + 1
        if any(c > 1 for c in seen.values()):
            messagebox.showerror("Studio Tools",
                                 "There are naming conflicts in the preview.\n"
                                 "Fix your options so all new names are unique.")
            return

        # Confirm
        changed = [(o, n) for o, n in zip(
            [os.path.basename(p) for p in self._files], new_names)
            if o != n]
        if not changed:
            messagebox.showinfo("Studio Tools",
                                "None of the filenames would change with "
                                "the current options.")
            return

        if not messagebox.askyesno(
                "Confirm Rename",
                f"Rename {len(changed)} file(s) on disk?\n\n"
                "You can undo immediately after."):
            return

        self._cancel = False
        self._set_busy(True)
        self._prog.set(0)
        threading.Thread(target=self._worker,
                         args=(list(self._files), list(new_names)),
                         daemon=True).start()

    def _worker(self, files: list[str], new_names: list[str]):
        total = len(files)
        ok = fail = 0
        undo_map: dict[str, str] = {}

        for i, (src, new_name) in enumerate(zip(files, new_names)):
            if self._cancel:
                self._q.put(("status",
                              f"Cancelled — {ok} renamed, {fail} failed"))
                self._q.put(("done", undo_map or None))
                return

            orig = os.path.basename(src)
            if orig == new_name:
                ok += 1
                self._q.put(("progress", (i + 1) / total))
                continue

            dst = os.path.join(os.path.dirname(src), new_name)
            self._q.put(("status",
                          f"Renaming  {i+1} / {total}  ·  {orig}"))
            try:
                if os.path.exists(dst):
                    raise FileExistsError(
                        f"Target already exists: {new_name}")
                os.rename(src, dst)
                undo_map[dst] = src
                ok += 1
            except Exception as e:
                fail += 1
                self._q.put(("err", f"✗  {orig}  —  {e}"))
            self._q.put(("progress", (i + 1) / total))

        self._q.put(("status", f"✓  Done — {ok} renamed, {fail} failed"))
        self._q.put(("done", undo_map or None))

    def _undo(self):
        if not self._undo_map:
            return
        errors = []
        new_file_list = list(self._files)
        for new_path, old_path in self._undo_map.items():
            try:
                if os.path.exists(new_path):
                    os.rename(new_path, old_path)
                    if new_path in new_file_list:
                        idx = new_file_list.index(new_path)
                        new_file_list[idx] = old_path
            except Exception as e:
                errors.append(str(e))
        self._undo_map = None
        self._undo_btn.configure(state="disabled")
        self._files = new_file_list
        self._refresh_file_box()
        self._refresh_preview()
        if errors:
            messagebox.showerror("Undo", "Some files could not be restored:\n"
                                 + "\n".join(errors[:5]))
        else:
            self._status_lbl.configure(text="Undo complete.")

    def _set_busy(self, busy: bool):
        self._busy = busy
        s = "disabled" if busy else "normal"
        for w in (self._rename_btn, self._btn_add_f, self._btn_add_d,
                  self._btn_clear):
            w.configure(state=s)
        self._cancel_btn.configure(
            state="normal" if busy else "disabled")

    def _drain(self):
        try:
            while True:
                kind, data = self._q.get_nowait()
                if kind == "status":
                    self._status_lbl.configure(text=data)
                elif kind == "progress":
                    self._prog.set(data)
                elif kind == "done":
                    self._prog.set(1)
                    self._set_busy(False)
                    if data:
                        self._undo_map = data
                        self._undo_btn.configure(state="normal")
                        self._files = list(data.keys())
                        self._refresh_file_box()
                        self._refresh_preview()
        except queue.Empty:
            pass
        self.after(120, self._drain)
