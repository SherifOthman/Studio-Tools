"""
shell.py  –  Application shell with sidebar navigation.

Language  → calls set_lang() then rebuilds ALL pages immediately.
Theme     → calls ctk.set_default_color_theme() then rebuilds pages.
Appearance → calls ctk.set_appearance_mode() – CTk handles redraws itself.
"""

import customtkinter as ctk

from app.core.prefs   import prefs
from app.core.strings import set_lang, t, lang as current_lang

# Navigation definition: (page_id, icon, title_key)
NAV = [
    ("vector",   "⟳",  "nav_vector"),
    ("images",   "🖼",  "nav_images"),
    ("rename",   "✏",  "nav_rename"),
    ("settings", "⚙",  "nav_settings"),
]

SIDEBAR_W = 210


class Shell(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Apply saved preferences before building any UI
        ctk.set_appearance_mode(prefs.get("appearance", "dark"))
        ctk.set_default_color_theme(prefs.get("theme", "blue"))
        set_lang(prefs["lang"])

        self.title(t("app_name"))
        self.geometry("1080x720")
        self.minsize(860, 580)

        self._active_page = "vector"
        self._nav_btns: dict[str, ctk.CTkButton] = {}
        self._pages: dict[str, ctk.CTkFrame] = {}

        self._build_layout()

    # ── Layout ────────────────────────────────────────────────────────────

    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._sidebar = self._build_sidebar()
        self._sidebar.grid(row=0, column=0, sticky="nsew")

        self._page_container = ctk.CTkFrame(
            self, corner_radius=0, fg_color="transparent"
        )
        self._page_container.grid(row=0, column=1, sticky="nsew")
        self._page_container.grid_rowconfigure(0, weight=1)
        self._page_container.grid_columnconfigure(0, weight=1)

        self._build_pages()
        self._show("vector")

    def _build_sidebar(self) -> ctk.CTkFrame:
        sb = ctk.CTkFrame(self, width=SIDEBAR_W, corner_radius=0)
        sb.grid_propagate(False)
        sb.grid_rowconfigure(len(NAV) + 2, weight=1)  # push version to bottom

        # Brand
        brand = ctk.CTkFrame(sb, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=12, pady=(24, 8))

        ctk.CTkLabel(
            brand, text="◈",
            font=ctk.CTkFont("Segoe UI", 32, "bold"),
        ).pack()
        self._sb_title = ctk.CTkLabel(
            brand, text=t("app_name"),
            font=ctk.CTkFont("Segoe UI", 14, "bold"),
        )
        self._sb_title.pack()
        self._sb_tagline = ctk.CTkLabel(
            brand, text=t("tagline"),
            font=ctk.CTkFont("Segoe UI", 9),
            text_color=("gray50","gray55"),
            wraplength=SIDEBAR_W - 24,
        )
        self._sb_tagline.pack()

        ctk.CTkFrame(sb, height=1, fg_color=("gray80","gray30"),
                     corner_radius=0).grid(row=1, column=0, sticky="ew",
                                           padx=14, pady=(4, 8))

        # Nav buttons
        for idx, (pid, icon, key) in enumerate(NAV):
            btn = ctk.CTkButton(
                sb,
                text=f"  {icon}  {t(key)}",
                anchor="w",
                height=46,
                corner_radius=8,
                fg_color="transparent",
                hover_color=("gray85","gray25"),
                font=ctk.CTkFont("Segoe UI", 13),
                command=lambda p=pid: self._show(p),
            )
            btn.grid(row=idx + 2, column=0, sticky="ew", padx=10, pady=2)
            self._nav_btns[pid] = btn

        # Version label at bottom
        ctk.CTkLabel(
            sb, text="v1.0",
            font=ctk.CTkFont("Segoe UI", 9),
            text_color=("gray60","gray45"),
        ).grid(row=len(NAV) + 3, column=0, sticky="s", pady=(0, 10))

        return sb

    def _build_pages(self):
        # Import here to allow the shell to apply theme/lang before pages build
        from app.pages.vector      import VectorPage
        from app.pages.coming_soon import ComingSoonPage
        from app.pages.settings    import SettingsPage

        self._pages["vector"]   = VectorPage(self._page_container)
        self._pages["images"]   = ComingSoonPage(self._page_container, page_id="images")
        self._pages["rename"]   = ComingSoonPage(self._page_container, page_id="rename")
        self._pages["settings"] = SettingsPage(
            self._page_container,
            on_lang_change=self._on_lang,
            on_theme_change=self._on_theme,
        )

        for page in self._pages.values():
            page.grid(row=0, column=0, sticky="nsew")

    def _show(self, pid: str):
        self._active_page = pid
        for p, frame in self._pages.items():
            if p == pid:
                frame.tkraise()
        self._highlight_nav(pid)

    def _highlight_nav(self, active: str):
        for pid, btn in self._nav_btns.items():
            if pid == active:
                # Use the theme's button fg_color for the active item
                btn.configure(
                    fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"],
                    text_color=("#ffffff", "#ffffff"),
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    hover_color=("gray85","gray25"),
                    text_color=ctk.ThemeManager.theme["CTkLabel"]["text_color"],
                )

    # ── Live change handlers ──────────────────────────────────────────────

    def _on_lang(self, code: str):
        set_lang(code)
        self._rebuild_pages()

    def _on_theme(self, tid: str):
        ctk.set_default_color_theme(tid)
        self._rebuild_pages()

    def _rebuild_pages(self):
        """Destroy and recreate all pages so language/theme applies instantly."""
        active = self._active_page
        for page in self._pages.values():
            page.destroy()
        self._pages.clear()
        self._nav_btns.clear()

        # Rebuild sidebar labels
        self._sb_title.configure(text=t("app_name"))
        self._sb_tagline.configure(text=t("tagline"))
        for idx, (pid, icon, key) in enumerate(NAV):
            btn = ctk.CTkButton(
                self._sidebar,
                text=f"  {icon}  {t(key)}",
                anchor="w",
                height=46,
                corner_radius=8,
                fg_color="transparent",
                hover_color=("gray85","gray25"),
                font=ctk.CTkFont("Segoe UI", 13),
                command=lambda p=pid: self._show(p),
            )
            btn.grid(row=idx + 2, column=0, sticky="ew", padx=10, pady=2)
            self._nav_btns[pid] = btn

        self._build_pages()
        self._show(active)
