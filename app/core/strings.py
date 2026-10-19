"""
strings.py  –  All UI text in English and Arabic.
Arabic is written to be natural and clear, not literal.
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
        "vec_subtitle":    "Convert EPS / AI files to PNG or JPG  ·  originals are never changed",
        "s1_files":        "① Files",
        "s2_format":       "② Output Format",
        "s3_quality":      "③ Export Quality",
        "s4_save":         "④ Where to Save",
        "btn_add_files":   "📄  Add Files",
        "btn_add_folder":  "📂  Add Folder",
        "btn_remove":      "✕  Remove Last",
        "btn_clear":       "🗑  Clear All",
        "n_files_0":       "No files added yet",
        "n_files_n":       "{n} file(s) ready",
        "fmt_png":         "PNG  —  Best quality, supports transparency",
        "fmt_jpg":         "JPG  —  Smaller file size, white background",
        "fmt_png_hint":    "Choose PNG to keep transparent backgrounds (logos, icons)",
        "fmt_jpg_hint":    "Choose JPG for photos or when a smaller file size matters",
        "png_bg_label":    "PNG Background:",
        "adv_bg_trans":    "Transparent",
        "adv_bg_white":    "White",
        "q_screen":        "Screen\n72 DPI",
        "q_web":           "Web\n150 DPI",
        "q_print":         "Print\n300 DPI",
        "q_hires":         "High‑Res\n600 DPI",
        "q_hint":          "300 DPI is ideal for printing.  72–150 is fine for screens and web.",
        "q_custom_label":  "Or type a custom DPI:",
        "jpg_q_label":     "JPG Quality:",
        "jpg_q_hint":      "Higher = better quality, larger file (95 is a good balance)",
        "pages_label":     "Multi-page export:",
        "pages_check":     "Export all artboards/pages as separate images",
        "pages_hint":      "Only needed for AI files with multiple artboards",
        "suffix_label":    "Filename suffix:",
        "suffix_hint":     "e.g.",
        "suffix_hint_ex":  "_web  →  logo_web.png",
        "save_beside":     "📁  Next to each original file",
        "save_custom":     "📂  Save to a specific folder:",
        "btn_browse":      "Browse…",
        "btn_convert":     "▶  Convert",
        "btn_cancel":      "✕  Cancel",
        "btn_open":        "📂  Open Output Folder",
        "log_title":       "Progress Log",
        "status_ready":    "Ready — add files above, then press Convert",
        "status_done":     "✓  Done — {ok} exported,  {fail} failed",
        "status_cancel":   "Cancelled — {ok} done,  {fail} failed",
        "status_conv":     "Converting  {i} / {n}  ·  {name}",
        "log_added":       "✓  Added {n} file(s)",
        "log_no_eps":      "No .eps or .ai files found in that folder",
        # ── Errors ──────────────────────────────────────────────────
        "err_no_files":    "Please add at least one .eps or .ai file first.",
        "err_dpi":         "DPI must be a number between 1 and 6000.",
        "err_no_outdir":   "Please choose an output folder, or switch to 'Next to each original'.",
        "err_gs":          "Ghostscript is not installed.\n\nPlease re-run the installer,\nor set the GS_EXE environment variable.",
        # ── GS status ───────────────────────────────────────────────
        "gs_ok":           "✓  Ghostscript {ver}  (ready)",
        "gs_missing":      "⚠  Ghostscript not found — please re-run the installer",
        # ── Settings ────────────────────────────────────────────────
        "set_title":       "Settings",
        "set_lang":        "Language  /  اللغة",
        "set_theme":       "Colour Theme",
        "set_mode":        "Appearance",
        "set_about":       "About Studio Tools",
        "mode_dark":       "🌙  Dark",
        "mode_light":      "☀️  Light",
        "mode_system":     "🖥  System",
        "about_body": (
            "Studio Tools  v1.0\n\n"
            "Professional file conversion tools for designers.\n"
            "Rasterisation engine: Ghostscript (AGPL v3).\n\n"
            "Coming soon:\n"
            "  •  Image batch converter\n"
            "  •  Batch file renamer"
        ),
    },

    "ar": {
        # ── Shell ────────────────────────────────────────────────────
        "app_name":        "Studio Tools",
        "tagline":         "أدوات احترافية للمصممين",
        # ── Nav ─────────────────────────────────────────────────────
        "nav_vector":      "تصدير المتجهات",
        "nav_images":      "تحويل الصور",
        "nav_rename":      "تسمية الملفات",
        "nav_settings":    "الإعدادات",
        "coming_soon":     "قريباً",
        "coming_body":     "هذه الأداة لا تزال تحت التطوير.\nسنُطلقها قريباً، ترقّبوا التحديثات.",
        # ── Vector page ──────────────────────────────────────────────
        "vec_title":       "تصدير المتجهات",
        "vec_subtitle":    "حوِّل ملفات EPS و AI إلى PNG أو JPG — الملفات الأصلية لا تُمسّ",
        "s1_files":        "① الملفات",
        "s2_format":       "② نوع الصورة",
        "s3_quality":      "③ جودة التصدير",
        "s4_save":         "④ مكان الحفظ",
        "btn_add_files":   "📄  إضافة ملفات",
        "btn_add_folder":  "📂  إضافة مجلد",
        "btn_remove":      "✕  حذف الأخير",
        "btn_clear":       "🗑  مسح الكل",
        "n_files_0":       "لم تُضَف ملفات بعد",
        "n_files_n":       "{n} ملف جاهز للتحويل",
        # Radio label format in Arabic: "أعلى جودة، شفاف — PNG"
        # The Latin format code (PNG/JPG) comes AFTER the dash, closest to the circle
        # so when reading RTL:  ○ PNG — أعلى جودة
        "fmt_png":         "أعلى جودة، شفافة — PNG",
        "fmt_jpg":         "حجم أصغر، خلفية بيضاء — JPG",
        "fmt_png_hint":    "اختر PNG للحفاظ على الشفافية (مناسب للشعارات والأيقونات)",
        "fmt_jpg_hint":    "اختر JPG للحصول على ملفات أصغر حجماً",
        # Arabic label rule: colon at END of label text
        "png_bg_label":    "خلفية PNG:",
        "adv_bg_trans":    "شفافة",
        "adv_bg_white":    "بيضاء",
        "q_screen":        "شاشة\n72 DPI",
        "q_web":           "إنترنت\n150 DPI",
        "q_print":         "طباعة\n300 DPI",
        "q_hires":         "عالية الدقة\n600 DPI",
        "q_hint":          "300 DPI مثالي للطباعة.  72–150 كافٍ للشاشات والإنترنت.",
        # DPI input: the entry field goes BEFORE this label text (on the right in RTL)
        "q_custom_label":  "DPI مخصص أو أدخل:",
        "jpg_q_label":     "جودة JPG:",
        "jpg_q_hint":      "كلما زاد الرقم زادت الجودة وحجم الملف  (95 توازن ممتاز)",
        "pages_label":     "تصدير متعدد الصفحات:",
        "pages_check":     "صدِّر كل لوحة رسم كصورة منفصلة",
        "pages_hint":      "مفيد فقط لملفات AI التي تحتوي أكثر من لوحة",
        "suffix_label":    "لاحقة الاسم:",
        # Example: "مثال:" comes FIRST (on the right), then the LTR example text
        "suffix_hint":     "مثال:",
        "suffix_hint_ex":  "_web → logo_web.png",
        "save_beside":     "في نفس مجلد الملف الأصلي",
        "save_custom":     "في مجلد محدد:",
        "btn_browse":      "استعراض…",
        "btn_convert":     "▶  تحويل",
        "btn_cancel":      "✕  إلغاء",
        "btn_open":        "📂  فتح مجلد النتائج",
        "log_title":       "سجل العمليات",
        "status_ready":    "جاهز — أضف الملفات ثم اضغط تحويل",
        "status_done":     "✓  اكتمل — {ok} ملف تم تصديره،  {fail} فشل",
        "status_cancel":   "تم الإلغاء — {ok} تم،  {fail} فشل",
        "status_conv":     "جارٍ التحويل  {i} / {n}  ·  {name}",
        "log_added":       "✓  تمت إضافة {n} ملف",
        "log_no_eps":      "لم يُعثر على ملفات EPS أو AI في هذا المجلد",
        # ── Errors ──────────────────────────────────────────────────
        "err_no_files":    "الرجاء إضافة ملف EPS أو AI واحد على الأقل.",
        "err_dpi":         "يجب أن تكون قيمة DPI رقماً بين 1 و 6000.",
        "err_no_outdir":   "الرجاء اختيار مجلد للحفظ، أو اختر 'في نفس مجلد الملف الأصلي'.",
        "err_gs":          "برنامج Ghostscript غير مثبّت.\n\nأعد تشغيل المثبّت\nأو اضبط متغير البيئة GS_EXE.",
        # ── GS status ───────────────────────────────────────────────
        "gs_ok":           "✓  Ghostscript {ver}  (جاهز)",
        "gs_missing":      "⚠  Ghostscript غير مثبّت — أعد تشغيل المثبّت",
        # ── Settings ────────────────────────────────────────────────
        "set_title":       "الإعدادات",
        "set_lang":        "Language  /  اللغة",
        "set_theme":       "نمط الألوان",
        "set_mode":        "مظهر التطبيق",
        "set_about":       "عن التطبيق",
        "mode_dark":       "🌙  داكن",
        "mode_light":      "☀️  فاتح",
        "mode_system":     "🖥  حسب النظام",
        "about_body": (
            "Studio Tools  v1.0\n\n"
            "أدوات احترافية لتحويل الملفات، مصممة للمصممين.\n"
            ".Ghostscript (AGPL v3) محرك التحويل:\n\n"
            ":الأدوات القادمة\n"
            "  •  تحويل الصور بالجملة\n"
            "  •  إعادة تسمية الملفات بالجملة"
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
