"""
pages/batch_rename.py  –  Professional Batch Rename

Supports all common rename scenarios:
  • Add prefix / suffix
  • Find & Replace (plain text or regex)
  • Auto-number (sequential, with customisable start, step, padding, position)
  • Change case (UPPER, lower, Title, Sentence)
  • Remove parts: leading/trailing spaces, extra spaces, brackets,
    specific characters, character ranges by index
  • Replace spaces with underscore / dash / dot (or vice-versa)
  • Strip / replace the extension
  • Live preview table: shows original → new name before any file is touched
  • Conflict detection: warns if two files would get the same name
  • Undo last rename (stores a rollback map)
"""

import os
import re
import glob
import queue
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk

from app.core.palette import (CHIP, CHIP_HOVER, CHIP_TEXT,
                              DIVIDER, EDGE, GHOST, GHOST_HOVER, GHOST_TEXT,
                              ROW, SEC, SEC_BORDER, SEC_HOVER, SEC_TEXT,
                              TEXT, TEXT_DISABLED, TEXT_SUB)
from app.core.strings import t

PAD = 16


# ── Rename engine (pure functions — no tkinter) ───────────────────────────

def apply_rule(name: str, ext: str, rule: dict, counter: int) -> tuple[str, str]:
    """
    Apply a single rule dict to (name_without_ext, extension).
    Returns (new_name, new_ext).
    """
    op = rule.get("op", "")

    # ── Prefix / Suffix ──────────────────────────────────────────────────
    if op == "prefix":
        name = rule["text"] + name

    elif op == "suffix":
        name = name + rule["text"]

    # ── Find & Replace ───────────────────────────────────────────────────
    elif op == "replace":
        find    = rule["find"]
        replace = rule["replace"]
        if not find:
            pass
        elif rule.get("regex"):
            try:
                flags = 0 if rule.get("case_sensitive") else re.IGNORECASE
                name = re.sub(find, replace, name, flags=flags)
            except re.error:
                pass   # bad regex — leave unchanged
        else:
            if rule.get("case_sensitive"):
                name = name.replace(find, replace)
            else:
                # Case-insensitive plain replace
                pattern = re.compile(re.escape(find), re.IGNORECASE)
                name = pattern.sub(replace, name)

    # ── Auto-number ──────────────────────────────────────────────────────
    elif op == "number":
        n       = rule.get("start", 1) + counter * rule.get("step", 1)
        pad     = rule.get("pad", 1)
        num_str = str(n).zfill(pad)
        sep     = rule.get("sep", "_")
        pos     = rule.get("pos", "suffix")     # "prefix" | "suffix" | "replace"
        if pos == "prefix":
            name = num_str + sep + name
        elif pos == "replace":
            name = num_str
        else:
            name = name + sep + num_str

    # ── Case change ──────────────────────────────────────────────────────
    elif op == "case":
        mode = rule.get("mode", "lower")
        if mode == "upper":
            name = name.upper()
        elif mode == "lower":
            name = name.lower()
        elif mode == "title":
            name = name.title()
        elif mode == "sentence":
            name = name.capitalize()

    # ── Remove / strip ───────────────────────────────────────────────────
    elif op == "remove_extra_spaces":
        name = " ".join(name.split())

    elif op == "trim":
        name = name.strip()

    elif op == "remove_brackets":
        kinds = rule.get("kinds", "()[]{}") 
        for open_b, close_b in [("(", ")"), ("[", "]"), ("{", "}")]:
            if open_b in kinds:
                name = re.sub(re.escape(open_b) + r"[^" +
                              re.escape(close_b) + r"]*" +
                              re.escape(close_b), "", name)
        name = name.strip()

    elif op == "remove_chars":
        chars = rule.get("chars", "")
        for c in chars:
            name = name.replace(c, "")

    elif op == "slice":
        start = rule.get("start", None)
        end   = rule.get("end",   None)
        name  = name[start:end]

    # ── Space / separator normalise ───────────────────────────────────────
    elif op == "spaces_to":
        char = rule.get("char", "_")
        name = name.replace(" ", char)

    elif op == "to_spaces":
        char = rule.get("char", "_")
        name = name.replace(char, " ")

    # ── Extension ────────────────────────────────────────────────────────
    elif op == "ext_lower":
        ext = ext.lower()

    elif op == "ext_upper":
        ext = ext.upper()

    elif op == "ext_change":
        new_ext = rule.get("new_ext", ext)
        if new_ext and not new_ext.startswith("."):
            new_ext = "." + new_ext
        ext = new_ext

    elif op == "ext_strip":
        ext = ""

    return name, ext


def build_new_name(original: str, rules: list[dict], counter: int) -> str:
    """Apply a list of rules in order and return the final filename."""
    base, ext = os.path.splitext(original)
    for rule in rules:
        base, ext = apply_rule(base, ext, rule, counter)
    # Sanitise: remove characters forbidden in Windows filenames
    for ch in r'\/:*?"<>|':
        base = base.replace(ch, "_")
    result = base + ext
    return result if result.strip(".") else original   # never produce empty/dot-only


# ── UI ─────────────────────────────────────────────────────────────────────

class BatchRenamePage(ctk.CTkFrame):

    def __init__(self, master, **kw):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kw)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._files: list[str] = []          # absolute paths
        self._rules: list[dict] = []          # ordered list of rule dicts
        self._undo_map: dict[str, str] | None = None   # new_path → old_path
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
        ctk.CTkLabel(hdr, text="Rename files in bulk  ·  live preview  ·  undo supported",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=TEXT_SUB, anchor="w").grid(
            row=1, column=0, padx=(PAD, 10), pady=(0, 10), sticky="w")
        ctk.CTkFrame(self, height=1, fg_color=EDGE,
                     corner_radius=0).grid(row=0, column=0, sticky="sew")

        # 3-column body: files | rules | preview
        body = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=3)   # files
        body.grid_columnconfigure(1, weight=0, minsize=1)  # sep
        body.grid_columnconfigure(2, weight=4)   # rules
        body.grid_columnconfigure(3, weight=0, minsize=1)  # sep
        body.grid_columnconfigure(4, weight=4)   # preview

        self._build_files_panel(body)
        ctk.CTkFrame(body, width=1, corner_radius=0,
                     fg_color=EDGE).grid(row=0, column=1, sticky="nsew")
        self._build_rules_panel(body)
        ctk.CTkFrame(body, width=1, corner_radius=0,
                     fg_color=EDGE).grid(row=0, column=3, sticky="nsew")
        self._build_preview_panel(body)

        # Action bar
        bar = ctk.CTkFrame(self, corner_radius=0, height=64)
        bar.grid(row=2, column=0, sticky="ew")
        bar.grid_propagate(False)
        ctk.CTkFrame(bar, height=1, fg_color=EDGE,
                     corner_radius=0).pack(fill="x", side="top")
        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="both", expand=True)

        self._rename_btn = ctk.CTkButton(
            inner, text="▶  Rename Files", width=160, height=42,
            font=ctk.CTkFont("Segoe UI", 14, "bold"),
            command=self._rename)
        self._undo_btn = ctk.CTkButton(
            inner, text="↩  Undo Last Rename", width=170, height=42,
            state="disabled",
            fg_color=SEC,
            hover_color=SEC_HOVER, text_color=SEC_TEXT,
            text_color_disabled=TEXT_DISABLED,
            command=self._undo)
        self._cancel_btn = ctk.CTkButton(
            inner, text="✕  Cancel", width=100, height=42,
            state="disabled",
            fg_color=SEC,
            hover_color=SEC_HOVER, text_color=SEC_TEXT,
            text_color_disabled=TEXT_DISABLED,
            command=self._do_cancel)
        self._status_lbl = ctk.CTkLabel(
            inner, text="Add files, add rules, then press Rename.",
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=TEXT_SUB, anchor="w")
        self._prog = ctk.CTkProgressBar(inner, height=6, corner_radius=3)
        self._prog.set(0)

        self._rename_btn.pack(side="left", padx=(PAD, 0), pady=10)
        self._undo_btn.pack(side="left",   padx=(8, 0),   pady=10)
        self._cancel_btn.pack(side="left", padx=(6, 0),   pady=10)
        self._status_lbl.pack(side="left", padx=(12, 0),  pady=10)
        self._prog.pack(side="right", padx=PAD, pady=10,
                        fill="x", expand=True)

    # ── Files panel ────────────────────────────────────────────────────────

    def _build_files_panel(self, parent):
        frame = ctk.CTkFrame(parent, corner_radius=0, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(frame, corner_radius=0, height=46,
                            fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=PAD, pady=(PAD, 4))
        ctk.CTkLabel(hdr, text="Files",
                     font=ctk.CTkFont("Segoe UI", 13, "bold")).pack(side="left")

        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.grid(row=1, column=0, sticky="ew", padx=PAD, pady=(0, 6))

        self._btn_add_f = ctk.CTkButton(btn_row, text="📄 Add Files", width=110,
                                         command=self._add_files)
        self._btn_add_d = ctk.CTkButton(btn_row, text="📂 Add Folder", width=120,
                                         fg_color=SEC, border_width=1,
                                         border_color=SEC_BORDER,
                                         hover_color=SEC_HOVER,
                                         text_color=SEC_TEXT,
                                         text_color_disabled=TEXT_DISABLED,
                                         command=self._add_folder)
        self._btn_clear_f = ctk.CTkButton(btn_row, text="🗑 Clear", width=80,
                                           fg_color=GHOST, hover_color=GHOST_HOVER,
                                           text_color=GHOST_TEXT,
                                           text_color_disabled=TEXT_DISABLED,
                                           command=self._clear_files)
        self._file_count = ctk.CTkLabel(btn_row, text="0 files",
                                         font=ctk.CTkFont("Segoe UI", 11),
                                         text_color=TEXT_SUB)
        for b in (self._btn_add_f, self._btn_add_d, self._btn_clear_f):
            b.pack(side="left", padx=(0, 6))
        self._file_count.pack(side="right")

        self._file_box = ctk.CTkTextbox(frame, state="disabled",
                                         font=ctk.CTkFont("Consolas", 10),
                                         wrap="none")
        self._file_box.grid(row=2, column=0, sticky="nsew",
                            padx=PAD, pady=(0, PAD))

    # ── Rules panel ────────────────────────────────────────────────────────

    def _build_rules_panel(self, parent):
        frame = ctk.CTkFrame(parent, corner_radius=0, fg_color="transparent")
        frame.grid(row=0, column=2, sticky="nsew")
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="Rules  (applied top to bottom)",
                     font=ctk.CTkFont("Segoe UI", 13, "bold"),
                     anchor="w").grid(row=0, column=0, sticky="w",
                                      padx=PAD, pady=(PAD, 6))

        # Compact rule adder using a CTkTabview for categories
        tabs = ctk.CTkTabview(frame, height=320)
        tabs.grid(row=1, column=0, sticky="ew", padx=PAD, pady=(0, 8))
        for cat in ("Text", "Numbers", "Case", "Clean", "Extension"):
            tabs.add(cat)

        self._build_tab_text(tabs.tab("Text"))
        self._build_tab_numbers(tabs.tab("Numbers"))
        self._build_tab_case(tabs.tab("Case"))
        self._build_tab_clean(tabs.tab("Clean"))
        self._build_tab_ext(tabs.tab("Extension"))

        # Active rules list
        ctk.CTkLabel(frame, text="Active rules:",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     anchor="w").grid(row=2, column=0, sticky="nw",
                                      padx=PAD, pady=(0, 2))
        rules_outer = ctk.CTkScrollableFrame(frame, corner_radius=8,
                                              height=180)
        rules_outer.grid(row=3, column=0, sticky="nsew",
                         padx=PAD, pady=(0, PAD))
        rules_outer.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(3, weight=1)
        self._rules_frame = rules_outer
        self._rules_widgets: list[ctk.CTkFrame] = []

    # ── Rule tabs ──────────────────────────────────────────────────────────

    def _build_tab_text(self, parent):
        parent.grid_columnconfigure(1, weight=1)

        def lbl(r, txt):
            ctk.CTkLabel(parent, text=txt,
                         font=ctk.CTkFont("Segoe UI", 11),
                         anchor="w").grid(row=r, column=0, sticky="w",
                                          padx=(0, 8), pady=3)

        lbl(0, "Prefix:")
        self._prefix_var = ctk.StringVar()
        ctk.CTkEntry(parent, textvariable=self._prefix_var,
                      placeholder_text="e.g. 2024_").grid(
            row=0, column=1, sticky="ew", pady=3)
        ctk.CTkButton(parent, text="+ Add", width=70,
                       command=lambda: self._add_rule(
                           {"op": "prefix", "text": self._prefix_var.get()},
                           f'Add prefix "{self._prefix_var.get()}"')
                       ).grid(row=0, column=2, padx=(6, 0), pady=3)

        lbl(1, "Suffix:")
        self._suffix_var = ctk.StringVar()
        ctk.CTkEntry(parent, textvariable=self._suffix_var,
                      placeholder_text="e.g. _final").grid(
            row=1, column=1, sticky="ew", pady=3)
        ctk.CTkButton(parent, text="+ Add", width=70,
                       command=lambda: self._add_rule(
                           {"op": "suffix", "text": self._suffix_var.get()},
                           f'Add suffix "{self._suffix_var.get()}"')
                       ).grid(row=1, column=2, padx=(6, 0), pady=3)

        lbl(2, "Find:")
        self._find_var = ctk.StringVar()
        ctk.CTkEntry(parent, textvariable=self._find_var).grid(
            row=2, column=1, sticky="ew", pady=3)

        lbl(3, "Replace with:")
        self._repl_var = ctk.StringVar()
        ctk.CTkEntry(parent, textvariable=self._repl_var).grid(
            row=3, column=1, sticky="ew", pady=3)

        opts_row = ctk.CTkFrame(parent, fg_color="transparent")
        opts_row.grid(row=4, column=0, columnspan=3, sticky="w", pady=3)
        self._regex_var = ctk.BooleanVar(value=False)
        self._casesens_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(opts_row, text="Regex",
                         variable=self._regex_var,
                         font=ctk.CTkFont("Segoe UI", 11)
                         ).pack(side="left", padx=(0, 12))
        ctk.CTkCheckBox(opts_row, text="Case sensitive",
                         variable=self._casesens_var,
                         font=ctk.CTkFont("Segoe UI", 11)
                         ).pack(side="left", padx=(0, 12))
        ctk.CTkButton(opts_row, text="+ Add Replace Rule", width=150,
                       command=lambda: self._add_rule(
                           {"op": "replace",
                            "find": self._find_var.get(),
                            "replace": self._repl_var.get(),
                            "regex": self._regex_var.get(),
                            "case_sensitive": self._casesens_var.get()},
                           f'Replace "{self._find_var.get()}" → "{self._repl_var.get()}"')
                       ).pack(side="left")

        # Spaces
        sp_row = ctk.CTkFrame(parent, fg_color="transparent")
        sp_row.grid(row=5, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ctk.CTkLabel(sp_row, text="Spaces →",
                     font=ctk.CTkFont("Segoe UI", 11)).pack(side="left",
                                                             padx=(0, 6))
        for char, label in (("_", "Underscore"), ("-", "Dash"), (".", "Dot")):
            ctk.CTkButton(sp_row, text=label, width=80,
                           command=lambda c=char: self._add_rule(
                               {"op": "spaces_to", "char": c},
                               f"Spaces → '{c}'")
                           ).pack(side="left", padx=(0, 4))

    def _build_tab_numbers(self, parent):
        parent.grid_columnconfigure(1, weight=1)

        def lbl(r, txt):
            ctk.CTkLabel(parent, text=txt,
                         font=ctk.CTkFont("Segoe UI", 11),
                         anchor="w").grid(row=r, column=0, sticky="w",
                                          padx=(0, 8), pady=3)

        lbl(0, "Start at:")
        self._num_start = ctk.CTkEntry(parent, width=80,
                                        placeholder_text="1")
        self._num_start.grid(row=0, column=1, sticky="w", pady=3)

        lbl(1, "Step:")
        self._num_step = ctk.CTkEntry(parent, width=80,
                                       placeholder_text="1")
        self._num_step.grid(row=1, column=1, sticky="w", pady=3)

        lbl(2, "Padding (digits):")
        self._num_pad = ctk.CTkEntry(parent, width=80,
                                      placeholder_text="2")
        self._num_pad.grid(row=2, column=1, sticky="w", pady=3)

        lbl(3, "Separator:")
        self._num_sep = ctk.CTkEntry(parent, width=80,
                                      placeholder_text="_")
        self._num_sep.grid(row=3, column=1, sticky="w", pady=3)

        lbl(4, "Position:")
        self._num_pos = ctk.StringVar(value="suffix")
        pos_row = ctk.CTkFrame(parent, fg_color="transparent")
        pos_row.grid(row=4, column=1, sticky="w", pady=3)
        for v, lbl_text in (("prefix", "Prefix"), ("suffix", "Suffix"),
                              ("replace", "Replace name")):
            ctk.CTkRadioButton(pos_row, text=lbl_text,
                                variable=self._num_pos, value=v,
                                font=ctk.CTkFont("Segoe UI", 11),
                                ).pack(side="left", padx=(0, 10))

        def _add_number():
            try:
                start = int(self._num_start.get() or 1)
                step  = int(self._num_step.get()  or 1)
                pad   = int(self._num_pad.get()   or 1)
                sep   = self._num_sep.get() or "_"
                pos   = self._num_pos.get()
            except ValueError:
                messagebox.showerror("Studio Tools",
                                     "Start, Step, and Padding must be whole numbers.")
                return
            self._add_rule({"op": "number", "start": start, "step": step,
                             "pad": pad, "sep": sep, "pos": pos},
                            f"Number ({pos}, start={start}, step={step}, "
                            f"pad={pad}, sep='{sep}')")

        ctk.CTkButton(parent, text="+ Add Numbering", width=140,
                       command=_add_number
                       ).grid(row=5, column=0, columnspan=2, sticky="w",
                               pady=(10, 0))

    def _build_tab_case(self, parent):
        for mode, label, desc in (
            ("upper",    "UPPERCASE",     "INVOICE → INVOICE"),
            ("lower",    "lowercase",     "INVOICE → invoice"),
            ("title",    "Title Case",    "my file → My File"),
            ("sentence", "Sentence case", "my file → My file"),
        ):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=4)
            ctk.CTkButton(row, text=f"+ {label}", width=140,
                           command=lambda m=mode, l=label:
                               self._add_rule({"op": "case", "mode": m},
                                              f"Case → {l}")
                           ).pack(side="left", padx=(0, 10))
            ctk.CTkLabel(row, text=desc,
                         font=ctk.CTkFont("Segoe UI", 10),
                         text_color=TEXT_SUB).pack(side="left")

    def _build_tab_clean(self, parent):
        ops = [
            ("remove_extra_spaces", "+ Collapse spaces",
             "hello  world → hello world"),
            ("trim",                "+ Trim whitespace",
             "  name  → name"),
        ]
        for op, lbl_text, desc in ops:
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=4)
            ctk.CTkButton(row, text=lbl_text, width=160,
                           command=lambda o=op, l=lbl_text:
                               self._add_rule({"op": o}, l.lstrip("+ "))
                           ).pack(side="left", padx=(0, 10))
            ctk.CTkLabel(row, text=desc,
                         font=ctk.CTkFont("Segoe UI", 10),
                         text_color=TEXT_SUB).pack(side="left")

        # Remove brackets
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=4)
        ctk.CTkButton(row, text="+ Remove brackets", width=160,
                       command=lambda: self._add_rule(
                           {"op": "remove_brackets", "kinds": "([{"},
                           "Remove (...) [...] {...}")
                       ).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(row, text="file (copy) → file",
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=TEXT_SUB).pack(side="left")

        # Remove specific characters
        rc_row = ctk.CTkFrame(parent, fg_color="transparent")
        rc_row.pack(fill="x", pady=4)
        ctk.CTkLabel(rc_row, text="Remove chars:",
                     font=ctk.CTkFont("Segoe UI", 11)).pack(side="left",
                                                              padx=(0, 6))
        self._rm_chars_var = ctk.StringVar()
        ctk.CTkEntry(rc_row, textvariable=self._rm_chars_var,
                      width=120, placeholder_text="e.g. #@!").pack(
            side="left", padx=(0, 6))
        ctk.CTkButton(rc_row, text="+ Add", width=70,
                       command=lambda: self._add_rule(
                           {"op": "remove_chars",
                            "chars": self._rm_chars_var.get()},
                           f'Remove chars "{self._rm_chars_var.get()}"')
                       ).pack(side="left")

        # Truncate
        tr_row = ctk.CTkFrame(parent, fg_color="transparent")
        tr_row.pack(fill="x", pady=4)
        ctk.CTkLabel(tr_row, text="Truncate to (chars):",
                     font=ctk.CTkFont("Segoe UI", 11)).pack(side="left",
                                                              padx=(0, 6))
        self._trunc_var = ctk.StringVar(value="")
        ctk.CTkEntry(tr_row, textvariable=self._trunc_var,
                      width=70, placeholder_text="50").pack(side="left",
                                                              padx=(0, 6))
        ctk.CTkButton(tr_row, text="+ Add", width=70,
                       command=lambda: self._add_rule(
                           {"op": "slice",
                            "end": (int(self._trunc_var.get())
                                    if self._trunc_var.get().strip().isdigit()
                                    else None)},
                           f'Truncate to {self._trunc_var.get()} chars')
                       ).pack(side="left")

    def _build_tab_ext(self, parent):
        ops = [
            ({"op": "ext_lower"}, "→ lowercase extension",
             ".JPG → .jpg"),
            ({"op": "ext_upper"}, "→ UPPERCASE extension",
             ".jpg → .JPG"),
            ({"op": "ext_strip"}, "Strip extension entirely",
             "file.txt → file"),
        ]
        for rule, lbl_text, desc in ops:
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=4)
            ctk.CTkButton(row, text=f"+ {lbl_text}", width=200,
                           command=lambda r=rule, l=lbl_text:
                               self._add_rule(r, l)
                           ).pack(side="left", padx=(0, 10))
            ctk.CTkLabel(row, text=desc,
                         font=ctk.CTkFont("Segoe UI", 10),
                         text_color=TEXT_SUB).pack(side="left")

        ext_row = ctk.CTkFrame(parent, fg_color="transparent")
        ext_row.pack(fill="x", pady=(8, 0))
        ctk.CTkLabel(ext_row, text="Change extension to:",
                     font=ctk.CTkFont("Segoe UI", 11)).pack(side="left",
                                                              padx=(0, 6))
        self._new_ext_var = ctk.StringVar()
        ctk.CTkEntry(ext_row, textvariable=self._new_ext_var,
                      width=80, placeholder_text=".png").pack(side="left",
                                                               padx=(0, 6))
        ctk.CTkButton(ext_row, text="+ Add", width=70,
                       command=lambda: self._add_rule(
                           {"op": "ext_change",
                            "new_ext": self._new_ext_var.get()},
                           f'Change extension → {self._new_ext_var.get()}')
                       ).pack(side="left")

    # ── Preview panel ──────────────────────────────────────────────────────

    def _build_preview_panel(self, parent):
        frame = ctk.CTkFrame(parent, corner_radius=0, fg_color="transparent")
        frame.grid(row=0, column=4, sticky="nsew")
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        hdr_row = ctk.CTkFrame(frame, corner_radius=0, height=46,
                                fg_color="transparent")
        hdr_row.grid(row=0, column=0, sticky="ew", padx=PAD,
                     pady=(PAD, 4))
        ctk.CTkLabel(hdr_row, text="Preview",
                     font=ctk.CTkFont("Segoe UI", 13, "bold")
                     ).pack(side="left")
        self._conflict_lbl = ctk.CTkLabel(
            hdr_row, text="",
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=("#DC2626", "#F87171"))
        self._conflict_lbl.pack(side="right")

        self._preview_box = ctk.CTkTextbox(
            frame, state="disabled",
            font=ctk.CTkFont("Consolas", 10),
            wrap="none")
        self._preview_box.grid(row=1, column=0, sticky="nsew",
                               padx=PAD, pady=(0, PAD))
        self._preview_box.tag_config("ok",      foreground="#16A34A")
        self._preview_box.tag_config("same",    foreground="#94A3B8")
        self._preview_box.tag_config("conflict",foreground="#DC2626")

    # ── Rule management ────────────────────────────────────────────────────

    def _add_rule(self, rule: dict, label: str):
        if not rule.get("op"):
            return
        self._rules.append(rule)
        self._render_rules()
        self._refresh_preview()

    def _render_rules(self):
        """Re-draw the active-rules list."""
        for w in self._rules_widgets:
            w.destroy()
        self._rules_widgets.clear()

        if not self._rules:
            lbl = ctk.CTkLabel(self._rules_frame,
                                text="No rules yet — add one above.",
                                font=ctk.CTkFont("Segoe UI", 11),
                                text_color=TEXT_SUB)
            lbl.pack(anchor="w")
            self._rules_widgets.append(lbl)
            return

        for i, rule in enumerate(self._rules):
            row = ctk.CTkFrame(self._rules_frame, corner_radius=8,
                                fg_color=CHIP)
            row.pack(fill="x", pady=(0, 4))
            self._rules_widgets.append(row)

            label = self._rule_label(rule)
            ctk.CTkLabel(row, text=f"{i+1}.  {label}",
                         font=ctk.CTkFont("Segoe UI", 11),
                         anchor="w", text_color=CHIP_TEXT
                         ).pack(side="left", padx=(10, 4), pady=6,
                                fill="x", expand=True)

            # Move up / down / delete
            btn_f = ctk.CTkFrame(row, fg_color="transparent")
            btn_f.pack(side="right", padx=6)
            for sym, action in (("↑", lambda x=i: self._move_rule(x, -1)),
                                  ("↓", lambda x=i: self._move_rule(x, 1)),
                                  ("✕", lambda x=i: self._delete_rule(x))):
                ctk.CTkButton(btn_f, text=sym, width=28, height=26,
                               fg_color="transparent",
                               hover_color=GHOST_HOVER,
                               text_color=GHOST_TEXT,
                               command=action
                               ).pack(side="left", padx=1)

    def _rule_label(self, rule: dict) -> str:
        op = rule.get("op", "?")
        if op == "prefix":
            return f'Add prefix "{rule["text"]}"'
        if op == "suffix":
            return f'Add suffix "{rule["text"]}"'
        if op == "replace":
            tag = " [regex]" if rule.get("regex") else ""
            tag += " [case]" if rule.get("case_sensitive") else ""
            return f'Replace "{rule["find"]}" → "{rule["replace"]}"{tag}'
        if op == "number":
            return (f'Number ({rule.get("pos","suffix")}, '
                    f'start={rule.get("start",1)}, step={rule.get("step",1)}, '
                    f'pad={rule.get("pad",1)}, sep="{rule.get("sep","_")}")')
        if op == "case":
            return f'Case → {rule.get("mode","lower")}'
        if op == "remove_extra_spaces":
            return "Collapse extra spaces"
        if op == "trim":
            return "Trim leading/trailing spaces"
        if op == "remove_brackets":
            return "Remove brackets  ( )  [ ]  { }"
        if op == "remove_chars":
            return f'Remove chars: "{rule.get("chars","")}"'
        if op == "slice":
            return f'Truncate to {rule.get("end","?")} chars'
        if op == "spaces_to":
            return f'Spaces → "{rule.get("char","_")}"'
        if op == "to_spaces":
            return f'"{rule.get("char","_")}" → spaces'
        if op == "ext_lower":
            return "Extension → lowercase"
        if op == "ext_upper":
            return "Extension → UPPERCASE"
        if op == "ext_strip":
            return "Strip extension"
        if op == "ext_change":
            return f'Change extension → "{rule.get("new_ext","")}"'
        return op

    def _move_rule(self, idx: int, delta: int):
        new_idx = idx + delta
        if 0 <= new_idx < len(self._rules):
            self._rules[idx], self._rules[new_idx] = (
                self._rules[new_idx], self._rules[idx])
        self._render_rules()
        self._refresh_preview()

    def _delete_rule(self, idx: int):
        del self._rules[idx]
        self._render_rules()
        self._refresh_preview()

    # ── Preview ────────────────────────────────────────────────────────────

    def _refresh_preview(self):
        self._preview_box.configure(state="normal")
        self._preview_box.delete("1.0", "end")

        new_names: list[str] = []
        for i, path in enumerate(self._files):
            orig = os.path.basename(path)
            new  = build_new_name(orig, self._rules, i)
            new_names.append(new)

        # Detect conflicts
        name_counts: dict[str, int] = {}
        for n in new_names:
            name_counts[n] = name_counts.get(n, 0) + 1
        conflicts = {n for n, c in name_counts.items() if c > 1}

        rows: list[str] = []
        for orig_path, new_name in zip(self._files, new_names):
            orig = os.path.basename(orig_path)
            if new_name == orig:
                tag = "same"
                line = f"  ─  {orig}"
            elif new_name in conflicts:
                tag = "conflict"
                line = f"  ⚠  {orig}  →  {new_name}"
            else:
                tag = "ok"
                line = f"  ✓  {orig}  →  {new_name}"
            self._preview_box.insert("end", line + "\n", tag)

        if conflicts:
            self._conflict_lbl.configure(
                text=f"⚠  {len(conflicts)} naming conflict(s) — fix before renaming")
        else:
            self._conflict_lbl.configure(text="")

        self._preview_box.configure(state="disabled")

    # ── File operations ────────────────────────────────────────────────────

    def _add_files(self):
        paths = filedialog.askopenfilenames(title="Select files to rename")
        if paths:
            self._ingest(list(paths))

    def _add_folder(self):
        folder = filedialog.askdirectory(title="Choose folder")
        if not folder:
            return
        files = [os.path.join(folder, f) for f in os.listdir(folder)
                 if os.path.isfile(os.path.join(folder, f))]
        self._ingest(sorted(files))

    def _ingest(self, paths: list[str]):
        existing = set(self._files)
        added = 0
        for p in paths:
            p = os.path.abspath(p)
            if p not in existing:
                self._files.append(p)
                existing.add(p)
                added += 1
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
        self._file_count.configure(
            text="0 files" if n == 0 else f"{n} file(s)")

    # ── Rename ─────────────────────────────────────────────────────────────

    def _rename(self):
        if self._busy or not self._files:
            if not self._files:
                messagebox.showinfo("Studio Tools",
                                    "Add some files to rename first.")
            return
        if not self._rules:
            messagebox.showinfo("Studio Tools",
                                "Add at least one rename rule first.")
            return

        # Build preview and check conflicts
        new_names: list[str] = []
        for i, path in enumerate(self._files):
            new_names.append(build_new_name(os.path.basename(path),
                                             self._rules, i))
        name_counts: dict[str, int] = {}
        for n in new_names:
            name_counts[n] = name_counts.get(n, 0) + 1
        if any(c > 1 for c in name_counts.values()):
            messagebox.showerror(
                "Studio Tools",
                "There are naming conflicts in the preview.\n"
                "Fix the rules before renaming.")
            return

        if not messagebox.askyesno(
                "Confirm Rename",
                f"Rename {len(self._files)} file(s)?\n\n"
                "This will rename files on disk.  You can undo immediately after."):
            return

        self._cancel = False
        self._set_busy(True)
        self._prog.set(0)

        threading.Thread(
            target=self._worker,
            args=(list(self._files), list(new_names)),
            daemon=True).start()

    def _worker(self, files: list[str], new_names: list[str]):
        total   = len(files)
        ok      = fail = 0
        undo_map: dict[str, str] = {}

        for i, (src, new_name) in enumerate(zip(files, new_names)):
            if self._cancel:
                self._q.put(("status", f"Cancelled — {ok} renamed, {fail} failed"))
                self._q.put(("done", undo_map if ok else None))
                return

            dst = os.path.join(os.path.dirname(src), new_name)
            self._q.put(("status",
                          f"Renaming  {i+1} / {total}  ·  "
                          f"{os.path.basename(src)}"))
            try:
                if src == dst:
                    ok += 1
                    self._q.put(("log_ok", os.path.basename(src)))
                    continue
                if os.path.exists(dst):
                    raise FileExistsError(
                        f"Target already exists: {os.path.basename(dst)}")
                os.rename(src, dst)
                undo_map[dst] = src
                ok += 1
                self._q.put(("log_ok",
                              f"{os.path.basename(src)}  →  {new_name}"))
            except Exception as e:
                fail += 1
                self._q.put(("log_fail",
                              f"✗  {os.path.basename(src)}  —  {e}"))
            self._q.put(("progress", (i + 1) / total))

        self._q.put(("status", f"✓  Done — {ok} renamed, {fail} failed"))
        self._q.put(("done", undo_map if ok else None))

    def _undo(self):
        if not self._undo_map:
            return
        errors = []
        for new_path, old_path in self._undo_map.items():
            try:
                if os.path.exists(new_path):
                    os.rename(new_path, old_path)
            except Exception as e:
                errors.append(str(e))
        self._undo_map = None
        self._undo_btn.configure(state="disabled")
        if errors:
            messagebox.showerror("Studio Tools",
                                 "Some files could not be undone:\n" +
                                 "\n".join(errors[:5]))
        else:
            self._status_lbl.configure(text="Undo complete — all files restored.")
        # Refresh the file list to show original names
        restored = list(self._undo_map.values() if self._undo_map else [])
        self._files = [p for p in self._files
                       if not any(p == v for v in (self._undo_map or {}))]
        self._refresh_file_box()
        self._refresh_preview()

    def _do_cancel(self):
        self._cancel = True

    def _set_busy(self, busy: bool):
        self._busy = busy
        s = "disabled" if busy else "normal"
        for w in (self._rename_btn, self._btn_add_f, self._btn_add_d,
                  self._btn_clear_f):
            w.configure(state=s)
        self._cancel_btn.configure(state="normal" if busy else "disabled")

    # ── Queue drain ────────────────────────────────────────────────────────

    def _drain(self):
        try:
            while True:
                kind, data = self._q.get_nowait()
                if kind == "status":
                    self._status_lbl.configure(text=data)
                elif kind in ("log_ok", "log_fail"):
                    pass   # Could add a log panel later
                elif kind == "progress":
                    self._prog.set(data)
                elif kind == "done":
                    self._prog.set(1)
                    self._set_busy(False)
                    if data:   # undo_map
                        self._undo_map = data
                        self._undo_btn.configure(state="normal")
                        # Update file list to new paths
                        self._files = list(data.keys())
                        self._refresh_file_box()
                        self._refresh_preview()
        except queue.Empty:
            pass
        self.after(120, self._drain)
