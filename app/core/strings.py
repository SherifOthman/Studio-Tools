"""strings.py – All UI text, English only."""

_S = {
    "app_name":       "Studio Tools",
    "tagline":        "Professional file utilities",
    "nav_vector":     "Vector Export",
    "nav_images":     "Image Convert",
    "nav_rename":     "Batch Rename",
    "nav_bgremove":   "Remove Background",
    "nav_settings":   "Settings",
    "coming_soon":    "Coming Soon",
    "coming_body":    "This tool is under development.\nCheck back for updates.",
    "vec_title":      "Vector Export",
    "vec_subtitle":   "Convert EPS / AI files to PNG or JPG  ·  originals are never changed",
    "s1_files":       "① Files",
    "s2_format":      "② Output Format",
    "s3_quality":     "③ Export Quality",
    "s4_save":        "④ Where to Save",
    "btn_add_files":  "📄  Add Files",
    "btn_add_folder": "📂  Add Folder",
    "btn_remove":     "✕  Remove Last",
    "btn_clear":      "🗑  Clear All",
    "n_files_0":      "No files added yet",
    "n_files_n":      "{n} file(s) ready",
    "fmt_png":        "PNG  —  Best quality, supports transparency",
    "fmt_jpg":        "JPG  —  Smaller file size, white background",
    "fmt_png_hint":   "Use PNG to keep transparent backgrounds (logos, icons)",
    "fmt_jpg_hint":   "Use JPG for photos or when file size matters",
    "png_bg_label":   "PNG Background:",
    "adv_bg_trans":   "Transparent",
    "adv_bg_white":   "White",
    "q_screen":       "Screen\n72 DPI",
    "q_web":          "Web\n150 DPI",
    "q_print":        "Print\n300 DPI",
    "q_hires":        "High‑Res\n600 DPI",
    "q_hint":         "300 DPI = ideal for print.  72–150 = fine for screens and web.",
    "q_custom_label": "Or enter a custom DPI:",
    "jpg_q_label":    "JPG Quality:",
    "jpg_q_hint":     "Higher = better quality, larger file  (95 is a good default)",
    "pages_label":    "Multi-page export:",
    "pages_check":    "Export each artboard / page as a separate image",
    "pages_hint":     "Only needed for AI files that contain multiple artboards",
    "suffix_label":   "Filename suffix:",
    "suffix_hint":    "e.g.  _web  →  logo_web.png",
    "save_beside":    "📁  Next to each original file",
    "save_custom":    "📂  Save to a specific folder:",
    "btn_browse":     "Browse…",
    "btn_convert":    "▶  Convert",
    "btn_cancel":     "✕  Cancel",
    "btn_open":       "📂  Open Output Folder",
    "log_title":      "Progress Log",
    "status_ready":   "Ready — add files, then press Convert",
    "status_done":    "✓  Done — {ok} exported,  {fail} failed",
    "status_cancel":  "Cancelled — {ok} done,  {fail} failed",
    "status_conv":    "Converting  {i} / {n}  ·  {name}",
    "log_added":      "✓  Added {n} file(s)",
    "log_no_eps":     "No .eps or .ai files found in that folder",
    "err_no_files":   "Please add at least one .eps or .ai file first.",
    "err_dpi":        "DPI must be a whole number between 1 and 6000.",
    "err_no_outdir":  "Please choose an output folder, or switch to 'Next to each original'.",
    "err_gs":         "Ghostscript is not installed.\n\nRe-run the installer, or set the GS_EXE environment variable.",
    "gs_ok":          "✓  Ghostscript {ver}",
    "gs_missing":     "⚠  Ghostscript not found — re-run installer",
    "set_title":      "Settings",
    "set_theme":      "Colour Theme",
    "set_mode":       "Appearance",
    "set_about":      "About Studio Tools",
    "mode_dark":      "🌙  Dark",
    "mode_light":     "☀️  Light",
    "mode_system":    "🖥  System",
    "about_body": (
        "Studio Tools  v1.0\n\n"
        "Professional batch-file utilities for designers.\n"
        "Rasterisation engine: Ghostscript (AGPL v3).\n\n"
        "Coming soon:\n"
        "  •  Image batch converter\n"
        "  •  Batch file renamer"
    ),
}


def t(key: str, **kw) -> str:
    s = _S.get(key, key)
    return s.format(**kw) if kw else s
