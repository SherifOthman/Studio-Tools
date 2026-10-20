"""
app/core/palette.py  –  Single source of truth for all UI colour pairs.

Dark mode: keeps original CustomTkinter values (gray17, #1D1E1E etc.) which
           looked great before — only the light mode was the problem.
Light mode: uses Tailwind Slate scale for proper contrast and modern look.

CTk convention: (light_value, dark_value) tuples.
"""

# ── Text ──────────────────────────────────────────────────────────────────
TEXT            = ("#1E293B", "#DCE4EE")   # primary text
TEXT_SUB        = ("#64748B", "#9AA0B0")   # secondary / hints
TEXT_DISABLED   = ("#94A3B8", "gray60")   # disabled state

# ── Secondary buttons ─────────────────────────────────────────────────────
# Light: soft blue-gray fill — clearly a button, not background
# Dark: original CTk gray (was working fine)
SEC             = ("#E8EDF5", "gray28")
SEC_HOVER       = ("#D1D9E8", "gray38")
SEC_TEXT        = ("#1E293B", "#DCE4EE")

# ── Ghost / tertiary buttons ──────────────────────────────────────────────
GHOST           = ("#F1F5F9", "gray22")
GHOST_HOVER     = ("#E2E8F0", "gray32")
GHOST_TEXT      = ("#475569", "#9AA0B0")

# ── DPI preset / chip buttons ─────────────────────────────────────────────
# Light: Slate-200 with Slate-700 text → clearly clickable, not background
# Dark: original CTk subtle dark → same as before
CHIP            = ("#E2E8F0", "gray25")
CHIP_HOVER      = ("#CBD5E1", "gray35")
CHIP_TEXT       = ("#334155", "#DCE4EE")

# ── Lines / dividers ──────────────────────────────────────────────────────
DIVIDER         = ("#E2E8F0", "gray30")    # rule inside a card
EDGE            = ("#CBD5E1", "gray28")    # rule between regions

# ── Navigation ────────────────────────────────────────────────────────────
NAV_HOVER       = ("#E2E8F0", "gray25")

# ── Selectable rows ───────────────────────────────────────────────────────
ROW             = ("#E2E8F0", "gray20")

# ── SEC_BORDER (kept for compatibility but SEC no longer uses border) ──────
SEC_BORDER      = ("#94A3B8", "gray45")
