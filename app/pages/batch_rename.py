"""
pages/batch_rename.py  –  Batch Rename + Copy Mode

COPY MODE (new):
  Instead of renaming the original files, the tool can now COPY them to a
  destination folder with the new names. The originals remain untouched.

RENAME ENGINE LOGIC:
  1. Find & Replace   (works on original base name)
  2. Case change      (applied after find/replace)
  3. Spaces normalise (applied after case)
  4. Number block     (assembled: prefix_text + number + suffix_text)
     - If Position = "Replace name": final name = ONLY number block
       → prefix/suffix/find/replace disabled
     - If "Before name": number block prepended
     - If "After name":  number block appended
  5. Extension change (independent)

COMPACT PREVIEW:
  For long filenames, the original name is truncated to show only the end
  (e.g. "...longname.jpg" → "NewName.jpg") so the new name is always visible.
"""

import os
import re
import shutil
import queue
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk

from app.core.palette import (CHIP, CHIP_HOVER, CHIP_TEXT, DIVIDER, EDGE,
                              GHOST, GHOST_HOVER, GHOST_TEXT,
                              SEC, SEC_HOVER, SEC_TEXT,
                              TEXT, TEXT_DISABLED, TEXT_SUB)
from app.core.prefs import prefs

PAD          = 16
PREVIEW_ROWS = 8


# ── Rename engine ─────────────────────────────────────────────────────────

def build_new_name(original: str, opts: dict, counter: int) -> str:
    base, ext = os.path.splitext(original)
    pos = opts.get("num_pos", "suffix")

    # Step 1 – Find & Replace  (skip when replacing whole name with number)
    if opts.get("number_enabled") and pos == "replace":
        pass
    else:
        find    = opts.get("find", "").strip()
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
                    base = re.sub(re.escape(find), replace, base,
                                  flags=re.IGNORECASE)

        # Step 2 – Case
        case = opts.get("case", "keep")
        if case == "upper":
            base = base.upper()
        elif case == "lower":
            base = base.lower()
        elif case == "title":
            base = base.title()

        # Step 3 – Spaces
        space_to = opts.get("space_to", "")
        if space_to == "underscore":
            base = base.replace(" ", "_")
        elif space_to == "dash":
            base = base.replace(" ", "-")
        elif space_to == "trim":
            base = " ".join(base.split())

    # Step 4 – Number block
    if opts.get("number_enabled"):
        try:
            start = int(opts.get("num_start", 1) or 1)
            step  = int(opts.get("num_step",  1) or 1)
            pad   = int(opts.get("num_pad",   2) or 2)
        except ValueError:
            start, step, pad = 1, 1, 2
        before_txt = opts.get("num_before", "")
        after_txt  = opts.get("num_after",  "")
        n      = start + counter * step
        num_s  = str(n).zfill(pad)
        block  = before_txt + num_s + after_txt

        if pos == "prefix":
            base = block + base
        elif pos == "replace":
            base = block
        else:
            base = base + block

    # Step 5 – Extension
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

        # Widgets — initialized early so callbacks during _build() are safe
        self._prefix_entry: ctk.CTkEntry | None = None
        self._suffix_entry: ctk.CTkEntry | None = None
        self._find_entry:   ctk.CTkEntry | None = None
        self._repl_entry:   ctk.CTkEntry | None = None
        self._num_option_widgets: list = []
        self._prev_rows: list = []          # preview row widgets

        self._build()
        self.after(120, self._drain)

    # ── Layout ─────────────────────────────────────────────────────────────

    def _build(self):
        hdr = ctk.CTkFrame(self, corner_radius=0, height=70)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(hdr, text="Batch Rename",
                     font=ctk.CTkFont("Segoe UI", 22, "bold"),
                     anchor="w").grid(row=0, column=0, padx=(PAD, 10),
                                      pady=(14, 2), sticky="w")
        ctk.CTkLabel(hdr, text="Rename or copy files in bulk  ·  "
                               "live preview updates as you type",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=TEXT_SUB, anchor="w").grid(
            row=1, column=0, padx=(PAD, 10), pady=(0, 10), sticky="w")
        ctk.CTkFrame(self, height=1, fg_color=EDGE,
                     corner_radius=0).grid(row=0, column=0, sticky="sew")

        body = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=4)
        body.grid_columnconfigure(1, weight=0, minsize=1)
        body.grid_columnconfigure(2, weight=6)

        left = ctk.CTkScrollableFrame(body, corner_radius=0,
                                       fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkFrame(body, width=1, corner_radius=0,
                     fg_color=EDGE).grid(row=0, column=1, sticky="nsew")

        right = ctk.CTkFrame(body, corner_radius=0, fg_color="transparent")
        right.grid(row=0, column=2, sticky="nsew")
        right.grid_rowconfigure(2, weight=1)
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
            inner, text="▶  Apply Changes", width=150, height=42,
            font=ctk.CTkFont("Segoe UI", 14, "bold"), command=self._rename)
        self._undo_btn = ctk.CTkButton(
            inner, text="↩  Undo", width=100, height=42, state="disabled",
            fg_color=SEC, hover_color=SEC_HOVER, text_color=SEC_TEXT,
            text_color_disabled=TEXT_DISABLED, command=self._undo)
        self._cancel_btn = ctk.CTkButton(
            inner, text="✕  Cancel", width=100, height=42, state="disabled",
            fg_color=SEC, hover_color=SEC_HOVER, text_color=SEC_TEXT,
            text_color_disabled=TEXT_DISABLED,
            command=lambda: setattr(self, "_cancel", True))
        self._status_lbl = ctk.CTkLabel(
            inner, text="Add files, choose Rename or Copy, then press Apply",
            font=ctk.CTkFont("Segoe UI", 11), text_color=TEXT_SUB, anchor="w")
        self._prog = ctk.CTkProgressBar(inner, height=6, corner_radius=3)
        self._prog.set(0)

        self._rename_btn.pack(side="left", padx=(PAD, 0), pady=10)
        self._undo_btn.pack(  side="left", padx=(8,  0), pady=10)
        self._cancel_btn.pack(side="left", padx=(6,  0), pady=10)
        self._status_lbl.pack(side="left", padx=(12, 0), pady=10)
        self._prog.pack(side="right", padx=PAD, pady=10, fill="x", expand=True)

    # ── Left panel ─────────────────────────────────────────────────────────

    def _build_left(self, parent):
        # Files
        fc = self._card(parent, "① Files")
        br = ctk.CTkFrame(fc, fg_color="transparent")
        br.pack(fill="x", pady=(0, 8))
        self._btn_add_f = ctk.CTkButton(br, text="📄  Add Files", width=120,
                                         command=self._add_files)
        self._btn_add_d = ctk.CTkButton(br, text="📂  Add Folder", width=130,
                                         fg_color=SEC, hover_color=SEC_HOVER,
                                         text_color=SEC_TEXT,
                                         text_color_disabled=TEXT_DISABLED,
                                         command=self._add_folder)
        self._btn_clear = ctk.CTkButton(br, text="🗑  Clear", width=80,
                                         fg_color=GHOST, hover_color=GHOST_HOVER,
                                         text_color=GHOST_TEXT,
                                         text_color_disabled=TEXT_DISABLED,
                                         command=self._clear_files)
        self._count_lbl = ctk.CTkLabel(br, text="0 files",
                                        font=ctk.CTkFont("Segoe UI", 11),
                                        text_color=TEXT_SUB)
        for b in (self._btn_add_f, self._btn_add_d, self._btn_clear):
            b.pack(side="left", padx=(0, 6))
        self._count_lbl.pack(side="right", padx=4)
        self._file_box = ctk.CTkTextbox(fc, height=110, state="disabled",
                                         font=ctk.CTkFont("Consolas", 10),
                                         wrap="none")
        self._file_box.pack(fill="x")

        # Mode: Rename or Copy
        mc = self._card(parent, "② Mode")
        self._mode = ctk.StringVar(value="copy")  # Default to copy mode

        row1 = ctk.CTkFrame(mc, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 8))
        ctk.CTkRadioButton(row1, text="Rename files  (originals are changed)",
                            variable=self._mode, value="rename",
                            command=self._mode_changed,
                            font=ctk.CTkFont("Segoe UI", 12, "bold"),
                            ).pack(anchor="w")
        ctk.CTkLabel(row1, text="The original files are modified in place.",
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=TEXT_SUB, anchor="w").pack(anchor="w",
                                                            padx=(28, 0))

        row2 = ctk.CTkFrame(mc, fg_color="transparent")
        row2.pack(fill="x")
        ctk.CTkRadioButton(row2, text="Copy with new names  (originals kept)",
                            variable=self._mode, value="copy",
                            command=self._mode_changed,
                            font=ctk.CTkFont("Segoe UI", 12, "bold"),
                            ).pack(anchor="w")
        ctk.CTkLabel(row2, text="Creates copies with the new names. Originals remain.",
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=TEXT_SUB, anchor="w").pack(anchor="w",
                                                            padx=(28, 0))

        # Copy destination
        self._copy_frame = ctk.CTkFrame(mc, fg_color="transparent")
        cf_row = ctk.CTkFrame(self._copy_frame, fg_color="transparent")
        cf_row.pack(fill="x", pady=(8, 0))
        ctk.CTkLabel(cf_row, text="Copy to:",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     width=70, anchor="w").pack(side="left")
        saved_copy_dir = prefs.get("last_rename_copy_dir", "")
        self._copy_entry = ctk.CTkEntry(cf_row, width=180,
                                         placeholder_text="C:\\Output\\folder")
        if saved_copy_dir:
            self._copy_entry.insert(0, saved_copy_dir)
        self._copy_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._copy_browse = ctk.CTkButton(
            cf_row, text="Browse…", width=90,
            fg_color=SEC, hover_color=SEC_HOVER, text_color=SEC_TEXT,
            text_color_disabled=TEXT_DISABLED,
            command=self._browse_copy)
        self._copy_browse.pack(side="left")
        # Not shown by default
        self._mode_changed()

        # Options
        oc = self._card(parent, "③ Rename Options")

        def R(p):
            f = ctk.CTkFrame(p, fg_color="transparent")
            f.pack(fill="x", pady=3)
            return f

        def lbl(p, t, w=110):
            ctk.CTkLabel(p, text=t, font=ctk.CTkFont("Segoe UI", 11, "bold"),
                         anchor="w", width=w).pack(side="left")

        # Prefix
        r = R(oc)
        lbl(r, "Add Prefix:")
        self._pfx = ctk.StringVar()
        self._prefix_entry = ctk.CTkEntry(r, textvariable=self._pfx,
                                           placeholder_text="e.g. 2024_")
        self._prefix_entry.pack(side="left", fill="x", expand=True)
        self._pfx.trace_add("write", lambda *_: self._refresh_preview())

        # Suffix
        r = R(oc)
        lbl(r, "Add Suffix:")
        self._sfx = ctk.StringVar()
        self._suffix_entry = ctk.CTkEntry(r, textvariable=self._sfx,
                                           placeholder_text="e.g. _final")
        self._suffix_entry.pack(side="left", fill="x", expand=True)
        self._sfx.trace_add("write", lambda *_: self._refresh_preview())

        ctk.CTkFrame(oc, height=1, fg_color=DIVIDER,
                     corner_radius=0).pack(fill="x", pady=(6, 6))

        # Find & Replace
        r = R(oc)
        lbl(r, "Find:")
        self._find = ctk.StringVar()
        self._find_entry = ctk.CTkEntry(r, textvariable=self._find)
        self._find_entry.pack(side="left", fill="x", expand=True)
        self._find.trace_add("write", lambda *_: self._refresh_preview())

        r = R(oc)
        lbl(r, "Replace with:")
        self._repl = ctk.StringVar()
        self._repl_entry = ctk.CTkEntry(r, textvariable=self._repl,
                                         placeholder_text="(blank = delete)")
        self._repl_entry.pack(side="left", fill="x", expand=True)
        self._repl.trace_add("write", lambda *_: self._refresh_preview())

        chk_row = ctk.CTkFrame(oc, fg_color="transparent")
        chk_row.pack(anchor="w", pady=(2, 0))
        self._regex     = ctk.BooleanVar(value=False)
        self._case_sens = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(chk_row, text="Regex", variable=self._regex,
                         command=self._refresh_preview,
                         font=ctk.CTkFont("Segoe UI", 11)
                         ).pack(side="left", padx=(0, 16))
        ctk.CTkCheckBox(chk_row, text="Case sensitive", variable=self._case_sens,
                         command=self._refresh_preview,
                         font=ctk.CTkFont("Segoe UI", 11)
                         ).pack(side="left")

        ctk.CTkFrame(oc, height=1, fg_color=DIVIDER,
                     corner_radius=0).pack(fill="x", pady=(8, 6))

        # Spaces
        r = R(oc)
        lbl(r, "Spaces:")
        self._space_to = ctk.StringVar(value="Keep")
        self._space_seg = ctk.CTkSegmentedButton(
            r, values=["Keep", "_ Underscore", "- Dash", "Trim"],
            command=lambda _: self._refresh_preview(),
            font=ctk.CTkFont("Segoe UI", 10), height=30,
            variable=self._space_to)
        self._space_map = {"Keep": "", "_ Underscore": "underscore",
                           "- Dash": "dash", "Trim": "trim"}
        self._space_seg.set("Keep")
        self._space_seg.pack(side="left", fill="x", expand=True)

        # Case
        r = R(oc)
        lbl(r, "Case:")
        self._case = ctk.StringVar(value="Keep")
        self._case_seg = ctk.CTkSegmentedButton(
            r, values=["Keep", "UPPER", "lower", "Title"],
            command=lambda _: self._refresh_preview(),
            font=ctk.CTkFont("Segoe UI", 10), height=30,
            variable=self._case)
        self._case_map = {"Keep": "keep", "UPPER": "upper",
                          "lower": "lower", "Title": "title"}
        self._case_seg.set("Keep")
        self._case_seg.pack(side="left", fill="x", expand=True)

        ctk.CTkFrame(oc, height=1, fg_color=DIVIDER,
                     corner_radius=0).pack(fill="x", pady=(8, 6))

        # Sequential numbers
        num_hdr = ctk.CTkFrame(oc, fg_color="transparent")
        num_hdr.pack(fill="x", pady=(0, 6))
        self._num_en = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(num_hdr, text="Add sequential numbers",
                         variable=self._num_en,
                         command=self._toggle_num,
                         font=ctk.CTkFont("Segoe UI", 11, "bold")
                         ).pack(side="left")

        self._num_frame = ctk.CTkFrame(oc, fg_color="transparent")
        nf = self._num_frame

        # Position row
        r = ctk.CTkFrame(nf, fg_color="transparent")
        r.pack(fill="x", pady=3)
        ctk.CTkLabel(r, text="Position:", width=80, anchor="w",
                     font=ctk.CTkFont("Segoe UI", 11)).pack(side="left")
        self._num_pos = ctk.StringVar(value="suffix")
        for v, lb in (("prefix", "Before name"),
                       ("suffix", "After name"),
                       ("replace", "Replace name")):
            rb = ctk.CTkRadioButton(r, text=lb, variable=self._num_pos, value=v,
                                     command=self._on_pos_change,
                                     font=ctk.CTkFont("Segoe UI", 11))
            rb.pack(side="left", padx=(0, 12))
            self._num_option_widgets.append(rb)

        # Text before/after
        r = ctk.CTkFrame(nf, fg_color="transparent")
        r.pack(fill="x", pady=3)
        ctk.CTkLabel(r, text="Text before #:", width=100, anchor="w",
                     font=ctk.CTkFont("Segoe UI", 11)).pack(side="left")
        self._num_before = ctk.StringVar()
        e1 = ctk.CTkEntry(r, textvariable=self._num_before,
                           width=120, placeholder_text="e.g. IMG_")
        e1.pack(side="left")
        e1.bind("<KeyRelease>", lambda _: self._refresh_preview())
        self._num_option_widgets.append(e1)

        r = ctk.CTkFrame(nf, fg_color="transparent")
        r.pack(fill="x", pady=3)
        ctk.CTkLabel(r, text="Text after #:", width=100, anchor="w",
                     font=ctk.CTkFont("Segoe UI", 11)).pack(side="left")
        self._num_after = ctk.StringVar()
        e2 = ctk.CTkEntry(r, textvariable=self._num_after,
                           width=120, placeholder_text="e.g. _beach")
        e2.pack(side="left")
        e2.bind("<KeyRelease>", lambda _: self._refresh_preview())
        self._num_option_widgets.append(e2)

        ctk.CTkLabel(nf, text='Example:  before="IMG_"  #=001  after="_beach"  →  IMG_001_beach',
                     font=ctk.CTkFont("Segoe UI", 10), text_color=TEXT_SUB,
                     anchor="w").pack(anchor="w", pady=(0, 4))

        # Numeric params
        r = ctk.CTkFrame(nf, fg_color="transparent")
        r.pack(fill="x", pady=3)
        for lb, attr, ph in (("Start:", "_num_start", "1"),
                              ("Step:", "_num_step", "1"),
                              ("Pad:", "_num_pad", "2")):
            ctk.CTkLabel(r, text=lb, width=46, anchor="w",
                         font=ctk.CTkFont("Segoe UI", 11)).pack(side="left")
            v = ctk.StringVar(value=ph)
            setattr(self, attr, v)
            e = ctk.CTkEntry(r, textvariable=v, width=52, justify="left")
            e.pack(side="left", padx=(0, 10))
            e.bind("<KeyRelease>", lambda _: self._refresh_preview())
            self._num_option_widgets.append(e)

        # Extension
        ctk.CTkFrame(oc, height=1, fg_color=DIVIDER,
                     corner_radius=0).pack(fill="x", pady=(8, 6))
        r = R(oc)
        lbl(r, "Extension:")
        self._ext_op = ctk.StringVar(value="Keep")
        ext_seg = ctk.CTkSegmentedButton(
            r, values=["Keep", ".lowercase", ".UPPERCASE"],
            command=lambda _: self._refresh_preview(),
            font=ctk.CTkFont("Segoe UI", 10), height=30,
            variable=self._ext_op)
        self._ext_map = {"Keep": "keep", ".lowercase": "lower",
                         ".UPPERCASE": "upper"}
        ext_seg.set("Keep")
        ext_seg.pack(side="left", fill="x", expand=True)

    # ── Right panel ────────────────────────────────────────────────────────

    def _build_right(self, parent):
        hdr = ctk.CTkFrame(parent, corner_radius=0, height=48,
                            fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=PAD, pady=(PAD, 0))
        ctk.CTkLabel(hdr, text="Live Preview  (first 8 files)",
                     font=ctk.CTkFont("Segoe UI", 13, "bold"),
                     anchor="w").pack(side="left")
        self._conflict_lbl = ctk.CTkLabel(hdr, text="",
                                           font=ctk.CTkFont("Segoe UI", 10),
                                           text_color=("#DC2626", "#F87171"))
        self._conflict_lbl.pack(side="right")

        col_hdr = ctk.CTkFrame(parent, corner_radius=0,
                                fg_color=("gray88", "gray22"), height=28)
        col_hdr.grid(row=1, column=0, sticky="ew", padx=PAD)
        col_hdr.grid_propagate(False)
        col_hdr.grid_columnconfigure(0, weight=1)
        col_hdr.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(col_hdr, text="ORIGINAL",
                     font=ctk.CTkFont("Segoe UI", 10, "bold"),
                     text_color=TEXT_SUB, anchor="w").grid(
            row=0, column=0, sticky="w", padx=10)
        ctk.CTkLabel(col_hdr, text="NEW NAME",
                     font=ctk.CTkFont("Segoe UI", 10, "bold"),
                     text_color=TEXT_SUB, anchor="w").grid(
            row=0, column=1, sticky="w", padx=10)

        self._prev_container = ctk.CTkScrollableFrame(
            parent, corner_radius=0, fg_color="transparent")
        self._prev_container.grid(row=2, column=0, sticky="nsew",
                                   padx=PAD, pady=(4, PAD))
        self._prev_container.grid_columnconfigure(0, weight=1)
        self._prev_rows: list = []

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

    # ── Disable logic ──────────────────────────────────────────────────────

    def _mode_changed(self):
        is_copy = self._mode.get() == "copy"
        if is_copy:
            self._copy_frame.pack(fill="x")
        else:
            self._copy_frame.pack_forget()
        # Update button text (only after action bar is built)
        if hasattr(self, "_rename_btn"):
            txt = "▶  Apply Copies" if is_copy else "▶  Rename Files"
            self._rename_btn.configure(text=txt)
            self._undo_btn.configure(state="disabled")
        self._undo_map = None
        self._refresh_preview()

    def _browse_copy(self):
        init = prefs.get("last_rename_copy_dir", "")
        d = filedialog.askdirectory(title="Choose output folder",
                                     initialdir=init or None)
        if d:
            self._copy_entry.delete(0, "end")
            self._copy_entry.insert(0, d)
            prefs["last_rename_copy_dir"] = d
            prefs.save()

    def _toggle_num(self):
        if self._num_en.get():
            self._num_frame.pack(fill="x", pady=(0, 4))
        else:
            self._num_frame.pack_forget()
        self._on_pos_change()

    def _on_pos_change(self):
        """When 'Replace name' selected, disable prefix/suffix/find/replace."""
        is_replace = (self._num_en.get() and
                      self._num_pos.get() == "replace")
        s = "disabled" if is_replace else "normal"
        for w in (self._prefix_entry, self._suffix_entry,
                  self._find_entry, self._repl_entry):
            if w:
                w.configure(state=s)
        self._space_seg.configure(state=s)
        self._case_seg.configure(state=s)
        self._refresh_preview()

    # ── Options collector ──────────────────────────────────────────────────

    def _get_opts(self) -> dict:
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
            "num_before":     self._num_before.get() if self._num_en.get() else "",
            "num_after":      self._num_after.get()  if self._num_en.get() else "",
            "num_start":      self._num_start.get()  if self._num_en.get() else "1",
            "num_step":       self._num_step.get()   if self._num_en.get() else "1",
            "num_pad":        self._num_pad.get()    if self._num_en.get() else "2",
            "num_pos":        self._num_pos.get()    if self._num_en.get() else "suffix",
            "ext_op":         self._ext_map.get(self._ext_op.get(), "keep"),
        }

    # ── Preview ────────────────────────────────────────────────────────────

    def _refresh_preview(self, *_):
        # Called during _build() before the right panel exists — skip safely
        if not hasattr(self, "_prev_container"):
            return
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

        opts   = self._get_opts()
        sample = self._files[:PREVIEW_ROWS]
        all_new_sample = [build_new_name(os.path.basename(p), opts, i)
                          for i, p in enumerate(sample)]
        all_new_full   = [build_new_name(os.path.basename(p), opts, i)
                          for i, p in enumerate(self._files)]

        seen: dict[str, int] = {}
        for n in all_new_full:
            seen[n] = seen.get(n, 0) + 1
        conflicts = {n for n, c in seen.items() if c > 1}

        if conflicts:
            self._conflict_lbl.configure(
                text=f"⚠  {len(conflicts)} naming conflict(s)",
                text_color=("#DC2626", "#F87171"))
        else:
            self._conflict_lbl.configure(
                text="✓  No conflicts",
                text_color=("#16A34A", "#4ADE80"))

        for orig_path, new_name in zip(sample, all_new_sample):
            orig = os.path.basename(orig_path)
            is_same     = (new_name == orig)
            is_conflict = (new_name in conflicts)

            # Compact display: if orig is long (>30 ch), show only end
            MAX_ORIG_LEN = 30
            if len(orig) > MAX_ORIG_LEN:
                disp_orig = "..." + orig[-(MAX_ORIG_LEN-3):]
            else:
                disp_orig = orig

            row = ctk.CTkFrame(
                self._prev_container, corner_radius=6,
                fg_color=("gray90","gray20") if is_same else
                         ("#FEE2E2","#3B1111") if is_conflict else
                         ("#F0FDF4","#0F2B1A"))
            row.pack(fill="x", pady=(0, 2))
            row.grid_columnconfigure(0, weight=1, uniform="col")
            row.grid_columnconfigure(2, weight=1, uniform="col")
            self._prev_rows.append(row)

            orig_col = TEXT_SUB if is_same else ("gray40", "gray60")
            new_col  = TEXT_SUB if is_same else \
                       ("#DC2626","#F87171") if is_conflict else \
                       ("#16A34A","#4ADE80")

            ctk.CTkLabel(row, text=disp_orig,
                         font=ctk.CTkFont("Consolas", 10),
                         text_color=orig_col, anchor="w").grid(
                row=0, column=0, sticky="w", padx=(8, 2), pady=4)
            ctk.CTkLabel(row, text="→",
                         font=ctk.CTkFont("Segoe UI", 10),
                         text_color=TEXT_SUB, width=16).grid(
                row=0, column=1)
            ctk.CTkLabel(row, text=new_name,
                         font=ctk.CTkFont("Consolas", 10, "bold"),
                         text_color=new_col, anchor="w").grid(
                row=0, column=2, sticky="w", padx=(2, 8), pady=4)

        if len(self._files) > PREVIEW_ROWS:
            info = ctk.CTkLabel(
                self._prev_container,
                text=f"  … and {len(self._files) - PREVIEW_ROWS} more",
                font=ctk.CTkFont("Segoe UI", 10), text_color=TEXT_SUB, anchor="w")
            info.pack(anchor="w", padx=4, pady=(4, 0))
            self._prev_rows.append(info)

    # ── File operations ────────────────────────────────────────────────────

    def _add_files(self):
        init_dir = prefs.get("last_rename_input_dir", "")
        paths = filedialog.askopenfilenames(title="Select files to rename",
                                            initialdir=init_dir or None)
        if paths:
            prefs["last_rename_input_dir"] = os.path.dirname(paths[0])
            prefs.save()
            self._ingest(list(paths))

    def _add_folder(self):
        init_dir = prefs.get("last_rename_input_dir", "")
        folder = filedialog.askdirectory(title="Choose folder",
                                          initialdir=init_dir or None)
        if not folder:
            return
        prefs["last_rename_input_dir"] = folder
        prefs.save()
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

    # ── Rename / Copy ──────────────────────────────────────────────────────

    def _rename(self):
        if self._busy or not self._files:
            if not self._files:
                messagebox.showinfo("Studio Tools",
                                    "Add some files first.")
            return

        mode = self._mode.get()
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

        changed = sum(1 for o, n in zip(
            [os.path.basename(p) for p in self._files], new_names) if o != n)
        if not changed:
            messagebox.showinfo("Studio Tools",
                                "None of the filenames would change.")
            return

        # Copy mode: check output dir
        out_dir = None
        if mode == "copy":
            out_dir = self._copy_entry.get().strip()
            if not out_dir:
                messagebox.showerror("Studio Tools",
                    "Choose an output folder for the copies.")
                return
            os.makedirs(out_dir, exist_ok=True)
            prefs["last_rename_copy_dir"] = out_dir
            prefs.save()

        verb = "Copy" if mode == "copy" else "Rename"
        if not messagebox.askyesno(f"Confirm {verb}",
                                   f"{verb} {changed} file(s)?\n\n"
                                   f"{'Copies will be created in the output folder.' if mode == 'copy' else 'You can undo immediately after.'}"):
            return

        self._cancel = False
        self._set_busy(True)
        self._prog.set(0)
        threading.Thread(target=self._worker,
                         args=(list(self._files), list(new_names), mode, out_dir),
                         daemon=True).start()

    def _worker(self, files, new_names, mode, out_dir):
        total = len(files)
        ok = fail = 0
        undo_map: dict[str, str] = {}

        for i, (src, new_name) in enumerate(zip(files, new_names)):
            if self._cancel:
                self._q.put(("status",
                              f"Cancelled — {ok} done, {fail} failed"))
                self._q.put(("done", undo_map or None))
                return

            orig = os.path.basename(src)
            if orig == new_name and mode == "rename":
                ok += 1
                self._q.put(("progress", (i + 1) / total))
                continue

            if mode == "copy":
                dst = os.path.join(out_dir, new_name)
            else:
                dst = os.path.join(os.path.dirname(src), new_name)

            self._q.put(("status", f"Processing  {i+1}/{total}  ·  {orig}"))
            try:
                if os.path.exists(dst):
                    raise FileExistsError(f"Target exists: {new_name}")
                if mode == "copy":
                    shutil.copy2(src, dst)
                else:
                    os.rename(src, dst)
                    undo_map[dst] = src
                ok += 1
            except Exception as e:
                fail += 1
            self._q.put(("progress", (i + 1) / total))

        verb = "copied" if mode == "copy" else "renamed"
        self._q.put(("status", f"✓  Done — {ok} {verb}, {fail} failed"))
        self._q.put(("done", undo_map or None))

    def _undo(self):
        if not self._undo_map:
            return
        errors = []
        new_list = list(self._files)
        for new_p, old_p in self._undo_map.items():
            try:
                if os.path.exists(new_p):
                    os.rename(new_p, old_p)
                    if new_p in new_list:
                        new_list[new_list.index(new_p)] = old_p
            except Exception as e:
                errors.append(str(e))
        self._undo_map = None
        self._undo_btn.configure(state="disabled")
        self._files = new_list
        self._refresh_file_box()
        self._refresh_preview()
        msg = "Undo complete." if not errors else \
              "Some files could not be restored:\n" + "\n".join(errors[:5])
        self._status_lbl.configure(text=msg)

    def _set_busy(self, busy: bool):
        self._busy = busy
        s = "disabled" if busy else "normal"
        for w in (self._rename_btn, self._btn_add_f,
                  self._btn_add_d, self._btn_clear):
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
                    if data and self._mode.get() == "rename":
                        self._undo_map = data
                        self._undo_btn.configure(state="normal")
                        self._files = list(data.keys())
                        self._refresh_file_box()
                        self._refresh_preview()
        except queue.Empty:
            pass
        self.after(120, self._drain)
