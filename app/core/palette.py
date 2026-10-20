"""
app/core/palette.py  –  Single source of truth for all UI colours.

Uses Tailwind Slate scale for neutral surfaces — proven in real apps.

Light mode ladder:
  Page bg       #F1F5F9  (Slate-100)
  Card bg       #FFFFFF  (white)
  Input bg      #F8FAFC  (Slate-50)
  Border        #CBD5E1  (Slate-300)
  Text primary  #1E293B  (Slate-800)
  Text secondary#64748B  (Slate-500)
  Text disabled #94A3B8  (Slate-400)

Dark mode ladder:
  Page bg       #0F1117
  Card bg       #1E1E2E
  Input bg      #1A1A2A
  Border        #334155  (Slate-700 darkened)
  Text primary  #F1F5F9  (Slate-100)
  Text secondary#94A3B8  (Slate-400)
  Text disabled #64748B  (Slate-500)

CTk uses (light, dark) tuples for all colour params.
"""

# ── Text ──────────────────────────────────────────────────────────────────
TEXT            = ("#1E293B", "#F1F5F9")   # primary body text
TEXT_SUB        = ("#64748B", "#94A3B8")   # secondary / hint text
TEXT_DISABLED   = ("#94A3B8", "#64748B")   # disabled state text

# ── Secondary buttons (outlined, clearly clickable in both modes) ─────────
# Solid light fill in light mode, dark fill in dark — always readable
SEC             = ("#E8EDF5", "#2A2A3C")           # subtle surface tint
SEC_BORDER      = ("#94A3B8",  "#4B5563")          # Slate-400 / Gray-600
SEC_HOVER       = ("#D1D9E8", "#353548")
SEC_TEXT        = ("#1E293B",  "#F1F5F9")

# ── Ghost / tertiary buttons (very light fill, text only) ─────────────────
GHOST           = ("#F1F5F9",  "#252535")          # Slate-100 / dark surface
GHOST_HOVER     = ("#E2E8F0",  "#2D2D40")          # Slate-200
GHOST_TEXT      = ("#475569",  "#94A3B8")          # Slate-600 / Slate-400

# ── Preset / chip buttons (inactive — must be clearly clickable) ──────────
CHIP            = ("#E2E8F0",  "#2D2D40")          # Slate-200 / dark surface
CHIP_HOVER      = ("#CBD5E1",  "#3D3D52")          # Slate-300
CHIP_TEXT       = ("#334155",  "#CBD5E1")          # Slate-700 / Slate-200

# ── Lines / dividers ──────────────────────────────────────────────────────
DIVIDER         = ("#E2E8F0",  "#2D2D40")          # rule inside a card
EDGE            = ("#CBD5E1",  "#252535")          # rule between regions (sidebar sep)

# ── Navigation ────────────────────────────────────────────────────────────
NAV_HOVER       = ("#E2E8F0",  "#2D2D40")

# ── Selectable rows (e.g. theme picker inactive card) ─────────────────────
ROW             = ("#E2E8F0",  "#2D2D40")          # inactive selectable row/card
