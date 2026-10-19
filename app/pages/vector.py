"""
pages/vector.py  –  Vector Export page

═══════════════════════════════════════════════════════════
  DEFINITIVE ARABIC / RTL UI RULES  (save for future pages)
═══════════════════════════════════════════════════════════

  1. LAYOUT DIRECTION
     • The whole page flows RIGHT → LEFT in Arabic.
     • First element the eye sees = TOP-RIGHT corner.
     • pack(side="right") adds to the right edge; pack(side="left") adds to left.
     • To build a row R→L: pack first widget side="right", next side="right", etc.

  2. LABEL + COLON
     • Arabic:  label text, then ":" at the END.   e.g.  "جودة JPG:"    ✓
     • NEVER put ":" before Arabic text.           e.g.  ":جودة JPG"   ✗
     • Colons in the strings file must already be at the end of the Arabic string.

  3. INPUT FIELDS (entry boxes)
     • Label is on the RIGHT → input box is to the LEFT of it.
     • Visual row (reading R→L):   "جودة JPG:  [____95____]"
     • In code:  label.pack(side="right"), entry.pack(side="right") after it,
       so entry appears to the left of the label.

  4. RADIO BUTTONS & CHECKBOXES
     • The circle/box is on the RIGHT (reading-start).
     • Text is to the LEFT of the circle.
     • Icons go BETWEEN the circle and the text:
         ○  📁  في نفس المجلد الأصلي
     • Technical codes (PNG, JPG) go on the far LEFT of the text block:
         ○  أعلى جودة، شفافة — PNG
       Reading R→L: PNG is the last word read, nearest the circle.
       Better: put the code to the FAR LEFT so Arabic flows naturally:
         ○  PNG — أعلى جودة، شفافة

  5. TECHNICAL TEXT (file paths, DPI numbers, PNG/JPG codes)
     • Always LTR — never flip numbers or paths.
     • Use  justify="left"  on entry widgets.
     • Wrap in a frame if needed to keep LTR inside an RTL row.

  6. SAVING THESE RULES
     • Every new page must import is_rtl() and use pack(side=R.start()/R.end()).
     • For label+input rows use: _labeled_input(parent, label_text, widget).
     • For radio rows use: _radio_row(parent, text, var, value).
     • For checkbox rows use: _check_row(parent, text, var).
═══════════════════════════════════════════════════════════
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

PRESETS = [("q_screen", 72), ("q_web", 150), ("q_print", 300), ("q_hires", 600)]
PAD = 16


class VectorPage(ctk.CTkFrame):

    def __init__(self, master, shell=None, **kw):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kw)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._shell      = shell
        self._files: list[str] = []
        self._busy       = False
        self._cancel     = False
        self._last_out: str | None = None
        self._q: queue.Queue = queue.Queue()
        self._gs_exe     = gs.find()

        self._build()
        self._update_gs_badge()
        self.after(120, self._drain)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  BUILD
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _build(self):
        self._build_header()
        self._build_body()
        self._build_action_bar()

    # ── Header ──────────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = ctk.CTkFrame(self, corner_radius=0, height=70)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)

        # Title on reading-start side (right in AR, left in EN)
        # Badge (GS status) on reading-end side
        if is_rtl():
            title_col, badge_col = 2, 0
            title_sticky, badge_sticky = "e", "w"
        else:
            title_col, badge_col = 0, 2
            title_sticky, badge_sticky = "w", "e"

        ctk.CTkLabel(hdr, text=t("vec_title"),
                     font=ctk.CTkFont("Segoe UI", 22, "bold"),
                     anchor=title_sticky,
                     ).grid(row=0, column=title_col, padx=(PAD, 10),
                            pady=(14, 2), sticky=title_sticky)

        ctk.CTkLabel(hdr, text=t("vec_subtitle"),
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=("gray40", "gray60"),
                     anchor=title_sticky,
                     ).grid(row=1, column=title_col, padx=(PAD, 10),
                            pady=(0, 10), sticky=title_sticky)

        self._gs_badge = ctk.CTkLabel(hdr, text="",
                                       font=ctk.CTkFont("Segoe UI", 10),
                                       anchor=badge_sticky)
        self._gs_badge.grid(row=0, column=badge_col, rowspan=2,
                            padx=PAD, sticky=badge_sticky)

        # Separator line under header
        ctk.CTkFrame(self, height=1, fg_color=("gray82", "gray28"),
                     corner_radius=0).grid(row=0, column=0, sticky="sew")

    # ── Scrollable body ──────────────────────────────────────────────────────

    def _build_body(self):
        scroll = ctk.CTkScrollableFrame(self, corner_radius=0,
                                         fg_color="transparent")
        scroll.grid(row=1, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        self._build_files_card(scroll)

        # Format + Quality side-by-side
        two = ctk.CTkFrame(scroll, fg_color="transparent")
        two.pack(fill="x", padx=PAD, pady=(0, PAD))
        two.grid_columnconfigure(0, weight=1)
        two.grid_columnconfigure(1, weight=2)
        self._build_format_card(two)
        self._build_quality_card(two)

        self._build_save_card(scroll)
        self._build_log_card(scroll)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  CARDS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _build_files_card(self, parent):
        inner = self._card(parent, t("s1_files"), pack=True, top_pad=PAD)

        # Button row — from reading-start edge
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
            b.pack(side=R.start(), padx=(0, 6))

        self._count_lbl = ctk.CTkLabel(br, text=t("n_files_0"),
                                        font=ctk.CTkFont("Segoe UI", 11),
                                        text_color=("gray40", "gray60"))
        self._count_lbl.pack(side=R.end(), padx=4)

        self._file_box = ctk.CTkTextbox(inner, height=130, state="disabled",
                                         font=ctk.CTkFont("Consolas", 11), wrap="none")
        self._file_box.pack(fill="x")

    # ── Format card ──────────────────────────────────────────────────────────

    def _build_format_card(self, parent):
        # Left column (LTR) / Right column (RTL) — col 0 = first in reading order
        col = 0 if not is_rtl() else 1
        inner = self._card(parent, t("s2_format"), grid_col=col)

        self._fmt = ctk.StringVar(value=prefs["fmt"])

        # Radio buttons for PNG / JPG
        # LTR visual:  ○ PNG — Best quality, transparent
        # RTL visual:  أعلى جودة، شفافة — PNG ○
        # We achieve this by using _radio_row() which handles both directions.
        self._radio_row(inner, t("fmt_png"), self._fmt, "png", self._fmt_changed)
        self._radio_row(inner, t("fmt_jpg"), self._fmt, "jpg", self._fmt_changed)

        # ── PNG background section (shown only when PNG selected) ──────────
        self._png_sec = ctk.CTkFrame(inner, fg_color="transparent")
        self._lbl(self._png_sec, t("png_bg_label"), bold=True
                  ).pack(anchor=R.anchor_start(), pady=(8, 4))
        self._bg = ctk.StringVar(value=prefs["bg"])
        self._radio_row(self._png_sec, t("adv_bg_trans"), self._bg, "transparent")
        self._radio_row(self._png_sec, t("adv_bg_white"), self._bg, "white")
        self._hint(self._png_sec, t("fmt_png_hint"), 220
                   ).pack(anchor=R.anchor_start(), pady=(6, 0))

        # ── JPG quality section (shown only when JPG selected) ─────────────
        self._jpg_sec = ctk.CTkFrame(inner, fg_color="transparent")

        # Label row: "JPG Quality:"  (colon at end, always)
        self._lbl(self._jpg_sec, t("jpg_q_label"), bold=True
                  ).pack(anchor=R.anchor_start(), pady=(8, 6))

        # Value + Slider row
        # Rule: label "95" on reading-START side, slider extends toward reading-END
        # LTR: slider → 95
        # RTL: 95 ← slider
        sl_row = ctk.CTkFrame(self._jpg_sec, fg_color="transparent")
        sl_row.pack(fill="x")

        self._jpg_q   = ctk.IntVar(value=prefs["jpg_quality"])
        self._jpg_lbl = ctk.CTkLabel(sl_row, text=str(prefs["jpg_quality"]),
                                      width=36,
                                      font=ctk.CTkFont("Segoe UI", 13, "bold"))
        self._jpg_sld = ctk.CTkSlider(sl_row,
                                       from_=0 if not is_rtl() else 100,
                                       to=100 if not is_rtl() else 0,
                                       variable=self._jpg_q, width=170)
        self._jpg_q.trace_add("write",
            lambda *_: self._jpg_lbl.configure(text=str(self._jpg_q.get())))

        if is_rtl():
            # RTL: value label on right (reading-start), slider extends left
            self._jpg_lbl.pack(side="right", padx=(0, 8))
            self._jpg_sld.pack(side="right", fill="x", expand=True)
        else:
            self._jpg_sld.pack(side="left", fill="x", expand=True)
            self._jpg_lbl.pack(side="left", padx=(8, 0))

        self._hint(self._jpg_sec, t("jpg_q_hint"), 220
                   ).pack(anchor=R.anchor_start(), pady=(6, 0))

        self._fmt_changed()   # show the right section immediately

    # ── Quality card ─────────────────────────────────────────────────────────

    def _build_quality_card(self, parent):
        col = 1 if not is_rtl() else 0
        inner = self._card(parent, t("s3_quality"), grid_col=col)

        # DPI preset buttons — flow from reading-start
        pr = ctk.CTkFrame(inner, fg_color="transparent")
        pr.pack(anchor=R.anchor_start(), pady=(0, 8))
        self._dpi_var = ctk.IntVar(value=prefs["dpi"])
        self._preset_btns: list[tuple[ctk.CTkButton, int]] = []
        for key, dpi in PRESETS:
            b = ctk.CTkButton(pr, text=t(key), width=88, height=50,
                               corner_radius=8,
                               font=ctk.CTkFont("Segoe UI", 10),
                               command=lambda d=dpi: self._set_preset(d))
            b.pack(side=R.start(), padx=(0, 6))
            self._preset_btns.append((b, dpi))
        self._refresh_preset_colors()

        self._hint(inner, t("q_hint"), 320).pack(anchor=R.anchor_start(),
                                                   pady=(0, 10))

        # ── Custom DPI input ──────────────────────────────────────────────
        # RULE: label on RIGHT, input on LEFT (reading R→L: label first, then value)
        # LTR: "Or type a custom DPI: [300]"   →  label then entry
        # RTL: "[300]  :DPI مخصص أو أدخل"   →  entry on LEFT, label on RIGHT
        dpi_row = ctk.CTkFrame(inner, fg_color="transparent")
        dpi_row.pack(anchor=R.anchor_start(), pady=(0, 10))

        dpi_lbl = self._lbl(dpi_row, t("q_custom_label"))
        self._dpi_entry = ctk.CTkEntry(dpi_row, width=78,
                                        placeholder_text="300",
                                        justify="left")   # numbers always LTR
        self._dpi_entry.insert(0, str(prefs["dpi"]))
        self._dpi_entry.bind("<KeyRelease>", lambda _: self._on_custom_dpi())

        if is_rtl():
            # RTL row (right → left): label | [entry]
            # pack "right" first = rightmost; pack "right" again = next to left of it
            dpi_lbl.pack(side="right", padx=(8, 0))
            self._dpi_entry.pack(side="right")
        else:
            dpi_lbl.pack(side="left", padx=(0, 8))
            self._dpi_entry.pack(side="left")

        # Separator
        ctk.CTkFrame(inner, height=1, fg_color=("gray85", "gray30"),
                     corner_radius=0).pack(fill="x", pady=(0, 10))

        # ── Multi-page export ─────────────────────────────────────────────
        self._lbl(inner, t("pages_label"), bold=True).pack(
            anchor=R.anchor_start())
        self._all_pages = ctk.BooleanVar(value=prefs["all_pages"])
        self._check_row(inner, t("pages_check"), self._all_pages)
        self._hint(inner, t("pages_hint")).pack(
            anchor=R.anchor_start(), pady=(2, 10))

        # ── Filename suffix ───────────────────────────────────────────────
        # RULE: label on right, entry on left, example text further left
        # LTR: "Filename suffix: [____]  e.g. _web → logo_web.png"
        # RTL: "مثال: _web → logo_web.png  [____]  :لاحقة الاسم"
        self._lbl(inner, t("suffix_label"), bold=True).pack(
            anchor=R.anchor_start())

        suf_row = ctk.CTkFrame(inner, fg_color="transparent")
        suf_row.pack(anchor=R.anchor_start(), pady=(4, 0), fill="x")
        self._suffix = ctk.StringVar(value=prefs["suffix"])

        suf_entry  = ctk.CTkEntry(suf_row, textvariable=self._suffix,
                                   width=110, placeholder_text="_web",
                                   justify="left")
        suf_eg_lbl = self._hint(suf_row, t("suffix_hint"))    # "e.g." / "مثال:"
        suf_eg_ex  = ctk.CTkLabel(suf_row,
                                   text=t("suffix_hint_ex"),
                                   font=ctk.CTkFont("Consolas", 10),
                                   text_color=("gray40", "gray60"))

        if is_rtl():
            # RTL row (right→left): label_eg | ex_text | [entry]
            # entry is on far left (reading-end), example near right
            suf_entry.pack(side="left")                       # far left
            suf_eg_ex.pack(side="left", padx=(6, 4))          # middle
            suf_eg_lbl.pack(side="left")                      # nearest right
        else:
            suf_entry.pack(side="left")
            suf_eg_lbl.pack(side="left", padx=(8, 4))
            suf_eg_ex.pack(side="left")

    # ── Save card ─────────────────────────────────────────────────────────────

    def _build_save_card(self, parent):
        inner = self._card(parent, t("s4_save"), pack=True)
        self._out_mode = ctk.StringVar(value=prefs["out_mode"])

        # Option 1: "Next to original" — icon inside label text
        self._radio_row(inner, t("save_beside"), self._out_mode, "beside",
                        command=self._save_mode_changed, pady=(0, 10))

        # Option 2: custom folder row
        # RULE for RTL:
        #   ○  [label text]  [path entry]  [Browse btn]
        #   Pack order: ○ on far-right, Browse on far-left, entry fills middle
        cf = ctk.CTkFrame(inner, fg_color="transparent")
        cf.pack(fill="x")

        # The radio circle (no text — label is separate for spacing control)
        self._rb_custom = ctk.CTkRadioButton(
            cf, text="", variable=self._out_mode, value="custom",
            command=self._save_mode_changed, width=20)

        # Label clickable — selecting it also activates the "custom" radio
        custom_lbl = ctk.CTkLabel(cf, text=t("save_custom"),
                                   font=ctk.CTkFont("Segoe UI", 12),
                                   anchor=R.text_anchor(), cursor="hand2")
        custom_lbl.bind("<Button-1>",
                        lambda _: (self._out_mode.set("custom"),
                                   self._save_mode_changed()))

        # Path entry — always LTR (file paths are LTR in any language)
        self._out_entry = ctk.CTkEntry(cf, width=250,
                                        placeholder_text="C:\\Output\\folder",
                                        justify="left")
        self._out_entry.insert(0, prefs["last_out_dir"])

        self._browse_btn = ctk.CTkButton(cf, text=t("btn_browse"), width=100,
                                          **self._sec(), command=self._browse_out)

        if is_rtl():
            # RTL layout (right → left):
            #   ○  في مجلد محدد:  [C:\Users\...\folder]  [استعراض]
            self._rb_custom.pack(side="right", padx=(4, 0))
            custom_lbl.pack(side="right", padx=(0, 6))
            self._browse_btn.pack(side="left", padx=(0, 6))
            self._out_entry.pack(side="left", fill="x", expand=True)
        else:
            # LTR layout (left → right):
            #   ○  Save to folder:  [C:\Users\...\folder]  [Browse]
            self._rb_custom.pack(side="left", padx=(0, 4))
            custom_lbl.pack(side="left", padx=(0, 6))
            self._out_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
            self._browse_btn.pack(side="left")

        self._save_mode_changed()

    # ── Log card ──────────────────────────────────────────────────────────────

    def _build_log_card(self, parent):
        inner = self._card(parent, t("log_title"), pack=True)
        self._log_box = ctk.CTkTextbox(inner, height=100, state="disabled",
                                        font=ctk.CTkFont("Consolas", 11),
                                        wrap="word")
        self._log_box.pack(fill="x")

    # ── Action bar ────────────────────────────────────────────────────────────

    def _build_action_bar(self):
        bar = ctk.CTkFrame(self, corner_radius=0, height=64)
        bar.grid(row=2, column=0, sticky="ew")
        bar.grid_propagate(False)

        # Separator above bar
        ctk.CTkFrame(bar, height=1, fg_color=("gray82", "gray28"),
                     corner_radius=0).pack(fill="x", side="top")

        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="both", expand=True)

        self._convert_btn = ctk.CTkButton(
            inner, text=t("btn_convert"), width=150, height=42,
            font=ctk.CTkFont("Segoe UI", 14, "bold"), command=self._convert)
        self._cancel_btn = ctk.CTkButton(
            inner, text=t("btn_cancel"), width=110, height=42,
            state="disabled", **self._sec(), command=self._do_cancel)
        self._open_btn = ctk.CTkButton(
            inner, text=t("btn_open"), width=180, height=42,
            state="disabled", **self._sec(), command=self._open_out)
        self._status_lbl = ctk.CTkLabel(
            inner, text=t("status_ready"),
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=("gray40", "gray60"), anchor=R.text_anchor())
        self._prog = ctk.CTkProgressBar(inner, height=6, corner_radius=3)
        self._prog.set(0)

        # Pack buttons from reading-start
        self._convert_btn.pack(side=R.start(), padx=(PAD, 0), pady=10)
        self._cancel_btn.pack(side=R.start(),  padx=(6, 0),   pady=10)
        self._open_btn.pack(side=R.start(),    padx=(6, 0),   pady=10)
        self._status_lbl.pack(side=R.start(),  padx=(10, 0),  pady=10)
        self._prog.pack(side=R.end(), padx=PAD, pady=10, fill="x", expand=True)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  REUSABLE WIDGET BUILDERS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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
                     anchor=R.anchor_start(),
                     ).pack(anchor=R.anchor_start(), padx=PAD, pady=(12, 0))
        ctk.CTkFrame(outer, height=1, fg_color=("gray85", "gray30"),
                     corner_radius=0).pack(fill="x", padx=PAD, pady=(6, 0))
        inner = ctk.CTkFrame(outer, fg_color="transparent")
        inner.pack(fill="both", padx=PAD, pady=(10, 14))
        return inner

    def _lbl(self, parent, text: str, bold=False) -> ctk.CTkLabel:
        return ctk.CTkLabel(parent, text=text,
                             font=ctk.CTkFont("Segoe UI", 11,
                                              "bold" if bold else "normal"),
                             anchor=R.text_anchor(), justify=R.justify())

    def _hint(self, parent, text: str, wraplength: int = 340) -> ctk.CTkLabel:
        return ctk.CTkLabel(parent, text=text,
                             font=ctk.CTkFont("Segoe UI", 10),
                             text_color=("gray40", "gray60"),
                             anchor=R.text_anchor(), justify=R.justify(),
                             wraplength=wraplength)

    def _radio_row(self, parent, text: str, var, value,
                   command=None, pady=(0, 6)):
        """
        Correct RTL radio row:
          LTR:  ○  text
          RTL:  text  ○    (circle on far right = reading-start)

        CTkRadioButton always places circle on its left. For RTL we hide
        the CTkRadioButton text and put a separate label to its left.
        """
        if not is_rtl():
            ctk.CTkRadioButton(parent, text=text, variable=var, value=value,
                               command=command,
                               font=ctk.CTkFont("Segoe UI", 12),
                               ).pack(anchor="w", pady=pady)
        else:
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(anchor="e", pady=pady, fill="x")
            # Text on the far LEFT (reading-end), circle on the far RIGHT (reading-start)
            ctk.CTkLabel(row, text=text,
                         font=ctk.CTkFont("Segoe UI", 12),
                         anchor="e", justify="right",
                         ).pack(side="left", fill="x", expand=True, padx=(0, 8))
            ctk.CTkRadioButton(row, text="", variable=var, value=value,
                               command=command, width=20,
                               ).pack(side="right")

    def _check_row(self, parent, text: str, var, pady=(0, 4)):
        """
        Correct RTL checkbox row:
          LTR:  ☐  text
          RTL:  text  ☐    (box on far right = reading-start)
        """
        if not is_rtl():
            ctk.CTkCheckBox(parent, text=text, variable=var,
                             font=ctk.CTkFont("Segoe UI", 11),
                             ).pack(anchor="w", pady=pady)
        else:
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(anchor="e", pady=pady, fill="x")
            ctk.CTkLabel(row, text=text,
                         font=ctk.CTkFont("Segoe UI", 11),
                         anchor="e", justify="right",
                         ).pack(side="left", fill="x", expand=True, padx=(0, 8))
            ctk.CTkCheckBox(row, text="", variable=var, width=20,
                             ).pack(side="right")

    def _sec(self) -> dict:
        """Secondary button style."""
        return dict(fg_color=("gray80", "gray25"),
                    hover_color=("gray70", "gray35"),
                    text_color=("gray10", "gray90"))

    def _ghost(self) -> dict:
        """Ghost button style."""
        return dict(fg_color=("gray85", "gray20"),
                    hover_color=("gray75", "gray30"),
                    text_color=("gray10", "gray90"))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  STATE HELPERS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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
                    text_color=("white", "white"))
            else:
                btn.configure(**self._ghost())

    def _set_preset(self, dpi: int):
        self._dpi_var.set(dpi)
        self._dpi_entry.delete(0, "end")
        self._dpi_entry.insert(0, str(dpi))
        self._refresh_preset_colors()

    def _on_custom_dpi(self):
        self._dpi_var.set(0)
        self._refresh_preset_colors()

    def _fmt_changed(self):
        """Show PNG or JPG section depending on selected format."""
        if self._fmt.get() == "png":
            self._jpg_sec.pack_forget()
            self._png_sec.pack(fill="x", pady=(4, 0))
        else:
            self._png_sec.pack_forget()
            self._jpg_sec.pack(fill="x", pady=(4, 0))

    def _save_mode_changed(self):
        beside = self._out_mode.get() == "beside"
        self._out_entry.configure(state="disabled" if beside else "normal")
        self._browse_btn.configure(state="disabled" if beside else "normal")

    def _is_focused(self) -> bool:
        try:
            return bool(self._shell and self._shell.focus_displayof() is not None)
        except Exception:
            return True

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  FILE OPERATIONS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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
            self._save_mode_changed()

    def _open_out(self):
        if self._last_out and os.path.isdir(self._last_out):
            try:
                os.startfile(self._last_out)
            except Exception:
                pass

    def _do_cancel(self):
        self._cancel = True

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  CONVERSION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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

        prefs["fmt"] = fmt; prefs["dpi"] = dpi; prefs["jpg_quality"] = jpg_q
        prefs["bg"] = self._bg.get(); prefs["all_pages"] = all_pages
        prefs["suffix"] = suffix; prefs["out_mode"] = self._out_mode.get()
        if out_dir:
            prefs["last_out_dir"] = out_dir
        prefs.save()

        self._cancel = False
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
                    if not self._is_focused():
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
                        threading.Thread(target=notify.send,
                                         args=(title, msg), daemon=True).start()
        except queue.Empty:
            pass
        self.after(120, self._drain)
