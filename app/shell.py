"""
shell.py  –  Application shell with sidebar navigation.

Language  → calls set_lang() then rebuilds ALL pages AND the sidebar immediately.
Theme     → calls ctk.set_default_color_theme() then rebuilds pages.
Appearance → calls ctk.set_appearance_mode() — CTk handles that itself.

RTL support:
  - Sidebar is placed on the RIGHT when Arabic is active.
  - All page content anchors/pack sides switch via is_rtl() helpers in each page.
"""

import customtkinter as ctk

from app.core.prefs   import prefs
from app.core.strings import set_lang, t, is_rtl

# Navigation: (page_id, icon, title_key)
NAV = [
    ("vector",   "⟳",  "nav_vector"),
    ("images",   "🖼",  "nav_images"),
    ("rename",   "✏",  "nav_rename"),
    ("settings", "⚙",  "nav_settings"),
]

SIDEBAR_W = 220


class Shell(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode(prefs.get("appearance", "dark"))
        ctk.set_default_color_theme(prefs.get("theme", "blue"))
        set_lang(prefs["lang"])

        self.title(t("app_name"))
        self.geometry("1100x730")
        self.minsize(880, 580)
        self.after(0, lambda: self.state("zoomed"))   # open maximised

        self._active_page = "vector"
        self._nav_btns: dict[str, ctk.CTkButton] = {}
        self._pages: dict[str, ctk.CTkFrame] = {}
        self._sidebar: ctk.CTkFrame | None = None
        self._page_container: ctk.CTkFrame | None = None

        self._build_layout()

    # ── Layout ───────────────────────────────────────────────────────────

    def _build_layout(self):
        # Clear existing grid config
        for col in range(4):
            self.grid_columnconfigure(col, weight=0)
        self.grid_rowconfigure(0, weight=1)

        rtl = is_rtl()
        sidebar_col  = 1 if rtl else 0
        content_col  = 0 if rtl else 1

        self.grid_columnconfigure(content_col, weight=1)
        self.grid_columnconfigure(sidebar_col, weight=0, minsize=SIDEBAR_W)

        self._sidebar = self._build_sidebar()
        self._sidebar.grid(row=0, column=sidebar_col, sticky="nsew")

        self._page_container = ctk.CTkFrame(
            self, corner_radius=0, fg_color="transparent",
        )
        self._page_container.grid(row=0, column=content_col, sticky="nsew")
        self._page_container.grid_rowconfigure(0, weight=1)
        self._page_container.grid_columnconfigure(0, weight=1)

        self._build_pages()
        self._show("vector")

    def _build_sidebar(self) -> ctk.CTkFrame:
        sb = ctk.CTkFrame(self, width=SIDEBAR_W, corner_radius=0)
        sb.grid_propagate(False)
        sb.grid_columnconfigure(0, weight=1)
        # row weights: brand=0, sep=0, nav buttons..., spacer=big, version=0
        sb.grid_rowconfigure(len(NAV) + 2, weight=1)

        # ── Brand / logo ─────────────────────────────────────────────────
        brand = ctk.CTkFrame(sb, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=16, pady=(28, 12))

        ctk.CTkLabel(
            brand, text="◈",
            font=ctk.CTkFont("Segoe UI", 42, "bold"),
        ).pack()

        self._sb_title = ctk.CTkLabel(
            brand, text=t("app_name"),
            font=ctk.CTkFont("Segoe UI", 17, "bold"),
        )
        self._sb_title.pack(pady=(2, 0))

        self._sb_tagline = ctk.CTkLabel(
            brand, text=t("tagline"),
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=("gray50","gray55"),
            wraplength=SIDEBAR_W - 32,
        )
        self._sb_tagline.pack(pady=(2, 0))

        # Separator
        ctk.CTkFrame(
            sb, height=1, fg_color=("gray80","gray30"), corner_radius=0,
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(4, 10))

        # Nav buttons
        for idx, (pid, icon, key) in enumerate(NAV):
            btn = ctk.CTkButton(
                sb,
                text=f"  {icon}  {t(key)}",
                anchor="e" if is_rtl() else "w",
                height=48,
                corner_radius=10,
                fg_color="transparent",
                hover_color=("gray85","gray25"),
                font=ctk.CTkFont("Segoe UI", 13),
                command=lambda p=pid: self._show(p),
            )
            btn.grid(row=idx + 2, column=0, sticky="ew", padx=10, pady=2)
            self._nav_btns[pid] = btn

        # Version label pinned to bottom
        ctk.CTkLabel(
            sb, text="v1.0",
            font=ctk.CTkFont("Segoe UI", 9),
            text_color=("gray60","gray45"),
        ).grid(row=len(NAV) + 3, column=0, sticky="s", pady=(0, 12))

        return sb

    def _build_pages(self):
        from app.pages.vector      import VectorPage
        from app.pages.coming_soon import ComingSoonPage
        from app.pages.settings    import SettingsPage

        self._pages["vector"]   = VectorPage(self._page_container, shell=self)
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
        for page in self._pages.values():
            page.lower()
        self._pages[pid].tkraise()
        self._highlight_nav(pid)

    def _highlight_nav(self, active: str):
        for pid, btn in self._nav_btns.items():
            if pid == active:
                btn.configure(
                    fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"],
                    text_color=("white","white"),
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
        self._full_rebuild()

    def _on_theme(self, tid: str):
        ctk.set_default_color_theme(tid)
        self._full_rebuild()

    def focus_window(self):
        """Bring this window to the front — called when user clicks a notification."""
        try:
            self.deiconify()         # restore if minimised
            self.lift()              # raise above other windows
            self.focus_force()       # grab keyboard focus
            self.state("zoomed")     # ensure maximised
        except Exception:
            pass

    def _full_rebuild(self):
        """
        Completely tear down sidebar + pages and rebuild from scratch.
        This guarantees every string, anchor, and pack-side is re-evaluated
        with the new language / theme.
        """
        active = self._active_page

        # Destroy old sidebar and container
        if self._sidebar:
            self._sidebar.destroy()
        if self._page_container:
            self._page_container.destroy()

        self._nav_btns.clear()
        self._pages.clear()

        # Reset grid weights before rebuild
        self.grid_columnconfigure(0, weight=0, minsize=0)
        self.grid_columnconfigure(1, weight=0, minsize=0)

        self._build_layout()
        self._show(active)
