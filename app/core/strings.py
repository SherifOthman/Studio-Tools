"""
strings.py  –  All UI text in English and Arabic.
Call  t("key")  anywhere after importing this module.
Call  set_lang("ar")  to switch immediately (no restart).
"""

_lang = "en"

_S = {
    "en": {
        # ── Shell ────────────────────────────────────────────────────
        "app_name":        "Studio Tools",
        "tagline":         "Professional file utilities",
        # ── Nav ─────────────────────────────────────────────────────
        "nav_vector":      "Vector Export",
        "nav_images":      "Image Convert",
        "nav_rename":      "Batch Rename",
        "nav_settings":    "Settings",
        "coming_soon":     "Coming Soon",
        "coming_body":     "This tool is under development.\nCheck back for updates.",
        # ── Vector page ──────────────────────────────────────────────
        "vec_title":       "Vector Export",
        "vec_subtitle":    "Convert EPS / AI files → PNG or JPG  ·  originals never touched",
        "s1_files":        "1  ·  Add Files",
        "s2_format":       "2  ·  Output Format",
        "s3_quality":      "3  ·  Export Quality",
        "s4_save":         "4  ·  Save Location",
        "btn_add_files":   "＋  Add Files",
        "btn_add_folder":  "📂  Add Folder",
        "btn_remove":      "Remove Selected",
        "btn_clear":       "Clear All",
        "n_files_0":       "No files added yet",
        "n_files_n":       "{n} file(s) queued",
        "fmt_png":         "PNG  —  lossless · transparent background",
        "fmt_jpg":         "JPG  —  smaller file · white background",
        "q_screen":        "Screen\n72 DPI",
        "q_web":           "Web\n150 DPI",
        "q_print":         "Print\n300 DPI",
        "q_hires":         "High‑Res\n600 DPI",
        "q_hint":          "300 DPI = Illustrator default 'High Quality'  ·  Higher = sharper, larger file",
        "adv_label":       "▸  Advanced options",
        "adv_label_open":  "▾  Advanced options",
        "adv_dpi":         "Custom DPI:",
        "adv_dpi_hint":    "Overrides the preset above",
        "adv_bg":          "PNG background:",
        "adv_transparent": "Transparent",
        "adv_white":       "White",
        "adv_jpg_q":       "JPG quality:",
        "adv_pages":       "Export every artboard / page  (multi-page AI files)",
        "adv_suffix":      "Filename suffix:",
        "adv_suffix_hint": 'e.g. "_export"  →  logo_export.png',
        "save_beside":     "Next to each original file",
        "save_custom":     "Custom folder:",
        "btn_browse":      "Browse…",
        "btn_convert":     "Convert",
        "btn_cancel":      "Cancel",
        "btn_open":        "Open Output Folder",
        "log_title":       "Activity Log",
        "status_ready":    "Ready — add files to begin",
        "status_done":     "✓  Done — {ok} converted,  {fail} failed",
        "status_cancel":   "Cancelled — {ok} done,  {fail} failed",
        "status_conv":     "{i} / {n}  ·  {name}",
        "log_added":       "Added {n} file(s)",
        "log_no_eps":      "No .eps / .ai files found in that folder",
        # ── Errors ──────────────────────────────────────────────────
        "err_no_files":    "Add at least one .eps or .ai file first.",
        "err_dpi":         "DPI must be a whole number between 1 and 6 000.",
        "err_no_outdir":   "Choose an output folder, or switch to 'Next to each original'.",
        "err_gs":          "Ghostscript not found.\n\nRe-run the installer, or set the\nGS_EXE environment variable.",
        # ── GS status ───────────────────────────────────────────────
        "gs_ok":           "✓  Ghostscript {ver}",
        "gs_missing":      "⚠  Ghostscript not found  —  re-run installer",
        # ── Settings ────────────────────────────────────────────────
        "set_title":       "Settings",
        "set_lang":        "Language",
        "set_theme":       "Colour Theme",
        "set_mode":        "Appearance",
        "set_about":       "About",
        "mode_dark":       "Dark",
        "mode_light":      "Light",
        "mode_system":     "System",
        "about_body": (
            "Studio Tools  v1.0\n\n"
            "Professional batch-file utilities for designers.\n"
            "Rasterisation powered by Ghostscript (AGPL v3).\n\n"
            "Roadmap:\n"
            "  •  Image batch converter\n"
            "  •  Batch file renamer"
        ),
    },

    "ar": {
        # ── Shell ────────────────────────────────────────────────────
        "app_name":        "Studio Tools",
        "tagline":         "أدوات ملفات احترافية",
        # ── Nav ─────────────────────────────────────────────────────
        "nav_vector":      "تصدير المتجهات",
        "nav_images":      "تحويل الصور",
        "nav_rename":      "إعادة التسمية",
        "nav_settings":    "الإعدادات",
        "coming_soon":     "قريباً",
        "coming_body":     "هذه الأداة قيد التطوير.\nترقّبوا التحديثات.",
        # ── Vector page ──────────────────────────────────────────────
        "vec_title":       "تصدير المتجهات",
        "vec_subtitle":    "تحويل ملفات EPS / AI ← PNG أو JPG  ·  الأصل لا يُمسّ أبداً",
        "s1_files":        "١  ·  إضافة الملفات",
        "s2_format":       "٢  ·  صيغة الإخراج",
        "s3_quality":      "٣  ·  جودة التصدير",
        "s4_save":         "٤  ·  مكان الحفظ",
        "btn_add_files":   "＋  إضافة ملفات",
        "btn_add_folder":  "📂  إضافة مجلد",
        "btn_remove":      "حذف المحدد",
        "btn_clear":       "مسح الكل",
        "n_files_0":       "لم تُضَف ملفات بعد",
        "n_files_n":       "{n} ملف(ات) في الانتظار",
        "fmt_png":         "PNG  —  بلا ضغط · خلفية شفافة",
        "fmt_jpg":         "JPG  —  حجم أصغر · خلفية بيضاء",
        "q_screen":        "شاشة\n72 DPI",
        "q_web":           "ويب\n150 DPI",
        "q_print":         "طباعة\n300 DPI",
        "q_hires":         "دقة عالية\n600 DPI",
        "q_hint":          "300 DPI = جودة Illustrator الافتراضية  ·  كلما زاد العدد زادت الدقة وحجم الملف",
        "adv_label":       "▸  خيارات متقدمة",
        "adv_label_open":  "▾  خيارات متقدمة",
        "adv_dpi":         ":DPI مخصص",
        "adv_dpi_hint":    "يتجاوز الإعداد المسبق أعلاه",
        "adv_bg":          ":خلفية PNG",
        "adv_transparent": "شفافة",
        "adv_white":       "بيضاء",
        "adv_jpg_q":       ":جودة JPG",
        "adv_pages":       "تصدير كل لوحة / صفحة  (ملفات AI متعددة الصفحات)",
        "adv_suffix":      ":لاحقة اسم الملف",
        "adv_suffix_hint": '"_export" مثال →  logo_export.png',
        "save_beside":     "بجانب كل ملف أصلي",
        "save_custom":     ":مجلد مخصص",
        "btn_browse":      "…استعراض",
        "btn_convert":     "تحويل",
        "btn_cancel":      "إلغاء",
        "btn_open":        "فتح مجلد الإخراج",
        "log_title":       "سجل النشاط",
        "status_ready":    "جاهز — أضف ملفات للبدء",
        "status_done":     "✓  تم — {ok} مُحوَّل،  {fail} فشل",
        "status_cancel":   "تم الإلغاء — {ok} تم،  {fail} فشل",
        "status_conv":     "{i} / {n}  ·  {name}",
        "log_added":       "تمت إضافة {n} ملف(ات)",
        "log_no_eps":      "لم يُعثر على ملفات .eps / .ai في هذا المجلد",
        # ── Errors ──────────────────────────────────────────────────
        "err_no_files":    ".أضف ملف .eps أو .ai واحداً على الأقل",
        "err_dpi":         ".يجب أن يكون DPI رقماً بين 1 و 6000",
        "err_no_outdir":   ".اختر مجلداً للإخراج، أو اختر 'بجانب كل ملف أصلي'",
        "err_gs":          "لم يُعثر على Ghostscript.\n\nأعد تشغيل المثبّت أو\naضبط متغير البيئة GS_EXE.",
        # ── GS status ───────────────────────────────────────────────
        "gs_ok":           "✓  Ghostscript {ver}",
        "gs_missing":      "⚠  Ghostscript غير موجود  —  أعد التثبيت",
        # ── Settings ────────────────────────────────────────────────
        "set_title":       "الإعدادات",
        "set_lang":        "اللغة",
        "set_theme":       "نمط الألوان",
        "set_mode":        "المظهر",
        "set_about":       "حول التطبيق",
        "mode_dark":       "داكن",
        "mode_light":      "فاتح",
        "mode_system":     "النظام",
        "about_body": (
            "Studio Tools  v1.0\n\n"
            "أدوات ملفات احترافية للمصمِّمين.\n"
            ".Ghostscript (AGPL v3) التحويل بواسطة\n\n"
            ":خارطة الطريق\n"
            "  •  محوّل صور دفعي\n"
            "  •  إعادة تسمية دفعية"
        ),
    },
}


def set_lang(code: str) -> None:
    global _lang
    if code in _S:
        _lang = code


def lang() -> str:
    return _lang


def is_rtl() -> bool:
    return _lang == "ar"


def t(key: str, **kw) -> str:
    s = _S.get(_lang, _S["en"]).get(key) or _S["en"].get(key, key)
    return s.format(**kw) if kw else s
