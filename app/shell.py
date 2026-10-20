"""shell.py – Application shell: sidebar + page container."""

import os
import sys
import customtkinter as ctk

from app.core.prefs   import prefs
from app.core.strings import t

NAV = [
    ("vector",   "⟳",  "nav_vector"),
    ("images",   "🖼",  "nav_images"),
    ("rename",   "✏",  "nav_rename"),
    ("settings", "⚙",  "nav_settings"),
]

SIDEBAR_W = 220

# Map prefs key → theme JSON filename in app/assets/
THEME_FILES = {
    "blue":    "theme_blue.json",
    "purple":  "theme_purple.json",
    "teal":    "theme_teal.json",
}


def _theme_path(key: str) -> str:
    """Return absolute path to the theme JSON file."""
    base = getattr(sys, "_MEIPASS",
                   os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    fname = THEME_FILES.get(key, "theme_blue.json")
    return os.path.join(base, "app", "assets", fname)


def apply_theme(key: str) -> None:
    """Apply a colour theme by loading our custom JSON file."""
    path = _theme_path(key)
    if os.path.isfile(path):
        ctk.set_default_color_theme(path)
    else:
        ctk.set_default_color_theme("blue")   # fallback


class Shell(ctk.CTk):
    def __init__(self):
        super().__init__()

        apply_theme(prefs.get("theme", "blue"))
        ctk.set_appearance_mode(prefs.get("appearance", "dark"))

        self.title(t("app_name"))
        self.geometry("1100x730")
        self.minsize(900, 600)
        self.after(0, lambda: self.state("zoomed"))

        self._active_page = "vector"
        self._nav_btns: dict[str, ctk.CTkButton] = {}
        self._pages: dict[str, ctk.CTkFrame] = {}
        self._sidebar = None
        self._separator = None
        self._page_container = None

        self._build()

    # ── Build ──────────────────────────────────────────────────────────────

    def _build(self):
        self.grid_columnconfigure(0, weight=0, minsize=SIDEBAR_W)
        self.grid_columnconfigure(1, weight=0, minsize=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._sidebar = self._build_sidebar()
        self._sidebar.grid(row=0, column=0, sticky="nsew")

        self._separator = ctk.CTkFrame(self, width=1, corner_radius=0,
                                        fg_color=("gray78", "gray22"))
        self._separator.grid(row=0, column=1, sticky="nsew")

        self._page_container = ctk.CTkFrame(self, corner_radius=0,
                                             fg_color="transparent")
        self._page_container.grid(row=0, column=2, sticky="nsew")
        self._page_container.grid_rowconfigure(0, weight=1)
        self._page_container.grid_columnconfigure(0, weight=1)

        self._build_pages()
        self._show("vector")

    def _build_sidebar(self) -> ctk.CTkFrame:
        sb = ctk.CTkFrame(self, width=SIDEBAR_W, corner_radius=0)
        sb.grid_propagate(False)
        sb.grid_columnconfigure(0, weight=1)
        sb.grid_rowconfigure(len(NAV) + 2, weight=1)

        # Brand
        brand = ctk.CTkFrame(sb, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=14, pady=(26, 12))

        ctk.CTkLabel(brand, text="◈",
                     font=ctk.CTkFont("Segoe UI", 46, "bold")).pack()
        ctk.CTkLabel(brand, text=t("app_name"),
                     font=ctk.CTkFont("Segoe UI", 18, "bold")).pack(pady=(2, 0))
        ctk.CTkLabel(brand, text=t("tagline"),
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=("gray50", "gray55"),
                     wraplength=SIDEBAR_W - 28).pack(pady=(2, 0))

        ctk.CTkFrame(sb, height=1, fg_color=("gray78", "gray30"),
                     corner_radius=0).grid(row=1, column=0, sticky="ew",
                                           padx=12, pady=(4, 8))

        # Nav buttons — text fully visible in both modes
        for idx, (pid, icon, key) in enumerate(NAV):
            btn = ctk.CTkButton(
                sb,
                text=f"  {icon}  {t(key)}",
                anchor="w",
                height=50,
                corner_radius=10,
                fg_color="transparent",
                hover_color=("gray82", "gray28"),
                text_color=("gray15", "gray90"),
                font=ctk.CTkFont("Segoe UI", 13),
                command=lambda p=pid: self._show(p),
            )
            btn.grid(row=idx + 2, column=0, sticky="ew", padx=10, pady=2)
            self._nav_btns[pid] = btn

        ctk.CTkLabel(sb, text="v1.0",
                     font=ctk.CTkFont("Segoe UI", 9),
                     text_color=("gray55", "gray45"),
                     ).grid(row=len(NAV) + 3, column=0, sticky="s", pady=(0, 12))

        return sb

    def _build_pages(self):
        from app.pages.vector        import VectorPage
        from app.pages.image_convert import ImageConvertPage
        from app.pages.coming_soon   import ComingSoonPage
        from app.pages.settings      import SettingsPage

        self._pages["vector"]   = VectorPage(self._page_container, shell=self)
        self._pages["images"]   = ImageConvertPage(self._page_container)
        self._pages["rename"]   = ComingSoonPage(self._page_container, page_id="rename")
        self._pages["settings"] = SettingsPage(self._page_container,
                                                on_theme_change=self._on_theme)

        for page in self._pages.values():
            page.grid(row=0, column=0, sticky="nsew")

    def _show(self, pid: str):
        self._active_page = pid
        for page in self._pages.values():
            page.lower()
        self._pages[pid].tkraise()

        th = ctk.ThemeManager.theme
        accent    = th["CTkButton"]["fg_color"]
        accent_hv = th["CTkButton"]["hover_color"]
        # Accent text color from theme — always readable on accent background
        act_text  = th["CTkButton"]["text_color"]

        for p, btn in self._nav_btns.items():
            if p == pid:
                btn.configure(
                    fg_color=accent,
                    hover_color=accent_hv,
                    text_color=act_text)
            else:
                btn.configure(
                    fg_color="transparent",
                    hover_color=("gray82", "gray28"),
                    text_color=("gray15", "gray90"))

    def _on_theme(self, tid: str):
        apply_theme(tid)
        prefs["theme"] = tid
        prefs.save()
        self._rebuild()

    def _rebuild(self):
        active = self._active_page
        for w in (self._sidebar, self._separator, self._page_container):
            if w:
                w.destroy()
        self._nav_btns.clear()
        self._pages.clear()
        self._sidebar = self._separator = self._page_container = None
        self._build()
        self._show(active)

    def focus_window(self):
        try:
            self.deiconify()
            self.lift()
            self.focus_force()
            self.state("zoomed")
        except Exception:
            pass
