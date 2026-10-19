"""
rtl.py  –  RTL/LTR layout helpers.

Rules followed (Material Design 3 + Apple HIG + UAE Design System):
  • Everything that follows reading order mirrors: layout, nav, radio buttons,
    checkboxes, icons-before-labels, sliders, progress bars.
  • Things that do NOT mirror: logos, photos, media controls, file paths,
    numbers, DPI values, clocks.

Key tkinter insight:
  pack(side="left")  always fills left→right regardless of language.
  To get a right→left ROW we add children in REVERSED order with side="left",
  OR we pack each child with side="right" so they fill right→left.

  The clean approach this module uses:
    rtl_pack(widget, side="start")  →  translates "start"/"end" to the
    correct tkinter side based on current language direction.

  "start" = the reading-direction start edge:
      LTR → left,   RTL → right
  "end"   = the reading-direction end edge:
      LTR → right,  RTL → left

  This means a row built as:
      icon.rtl_pack("start")   label.rtl_pack("start")
  produces:   [icon] [label] ...   in LTR
  and:        ... [label] [icon]   in RTL   ← icon is still "before" label visually
"""

import customtkinter as ctk
from app.core.strings import is_rtl


def start() -> str:
    """Tkinter pack side for the reading-start edge."""
    return "right" if is_rtl() else "left"


def end() -> str:
    """Tkinter pack side for the reading-end edge."""
    return "left" if is_rtl() else "right"


def anchor_start() -> str:
    """Tkinter anchor / sticky for the reading-start edge."""
    return "e" if is_rtl() else "w"


def anchor_end() -> str:
    return "w" if is_rtl() else "e"


def text_anchor() -> str:
    return "e" if is_rtl() else "w"


def justify() -> str:
    return "right" if is_rtl() else "left"


def padx_start(n: int) -> tuple:
    """Return (left, right) padx tuple where padding is on the START side."""
    return (0, n) if is_rtl() else (0, n)


def row(parent, fg_color="transparent") -> ctk.CTkFrame:
    """Create a transparent horizontal row frame."""
    return ctk.CTkFrame(parent, fg_color=fg_color)


def label(parent, text: str, font=None, color=None,
          anchor=None, wraplength=0, **kw) -> ctk.CTkLabel:
    """Create a label with correct justification for current language."""
    kw.setdefault("anchor", anchor or text_anchor())
    kw.setdefault("justify", justify())
    kwargs = dict(text=text, font=font or ctk.CTkFont("Segoe UI", 11),
                  anchor=kw.pop("anchor"), justify=kw.pop("justify"))
    if color:
        kwargs["text_color"] = color
    if wraplength:
        kwargs["wraplength"] = wraplength
    return ctk.CTkLabel(parent, **kwargs, **kw)


def section_label(parent, text: str) -> ctk.CTkLabel:
    """Bold section label aligned to reading start."""
    return ctk.CTkLabel(
        parent, text=text,
        font=ctk.CTkFont("Segoe UI", 11, "bold"),
        anchor=text_anchor(),
        justify=justify(),
    )


def hint_label(parent, text: str, wraplength: int = 400) -> ctk.CTkLabel:
    """Small dimmed hint label."""
    return ctk.CTkLabel(
        parent, text=text,
        font=ctk.CTkFont("Segoe UI", 10),
        text_color=("gray40", "gray60"),
        anchor=text_anchor(),
        justify=justify(),
        wraplength=wraplength,
    )


def pack_start(widget, padx=(0, 8), pady=0, fill=None, expand=False):
    """Pack a widget from the reading-start edge."""
    kwargs = dict(side=start(), padx=padx, pady=pady)
    if fill:
        kwargs["fill"] = fill
    if expand:
        kwargs["expand"] = True
    widget.pack(**kwargs)


def pack_end(widget, padx=(0, 0), pady=0):
    """Pack a widget from the reading-end edge."""
    widget.pack(side=end(), padx=padx, pady=pady)
