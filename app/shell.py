"""
shell.py  –  Application shell: sidebar + page container.

RTL rules applied (Material Design 3 / Apple HIG):
  • Sidebar is on the RIGHT when Arabic, LEFT when English.
  • A 1-px separator line visually divides sidebar from content.
  • Nav button text anchors to the reading-start edge.
  • All page rebuilds happen instantly on lang/theme change.
"""

import customtkinter as ctk

from app.core.prefs   import prefs
from app.core.strings import set_lang, t, is_rtl

NAV = [
    ("vector",   "⟳",  "nav_vector"),
    ("images",   "🖼",  "nav_images"),
    ("rename",   "✏",  "nav_rename"),
    ("settings", "⚙",  "nav_settings"),
]

SIDEBAR_W = 230   # wider sidebar so text isn't cramped


class Shell(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode(prefs.get("appearance", "dark"))
        ctk.set_default_color_theme(prefs.get("theme", "blue"))
        set_lang(prefs["lang"])

        self.title(t("app_name"))
        self.geometry("1100x730")
        self.minsize(900, 600)
        # Open maximised
        self.after(0, lambda: self.state("zoomed"))

        self._active_page = "vector"
        self._nav_btns: dict[str, ctk.CTkButton] = {}
        self._pages: dict[str, ctk.CTkFrame] = {}
        self._sidebar: ctk.CTkFrame | None = None
        self._separator: ctk.CTkFrame | None = None
        self._page_container: ctk.CTkFrame | None = None

        self._build_layout()

    # ── Build ─────────────────────────────────────────────────────────────

    def _build_layout(self):
        # Reset grid
        for c in range(4):
            self.grid_columnconfigure(c, weight=0, minsize=0)
        self.grid_rowconfigure(0, weight=1)

        rtl = is_rtl()
        # Sidebar column
        sb_col  = 1 if rtl else 0
        sep_col = 2 if rtl else 1   # 1-px separator column
        ct_col  = 0 if rtl else 2   # content

        self.grid_columnconfigure(sb_col,  weight=0, minsize=SIDEBAR_W)
        self.grid_columnconfigure(sep_col, weight=0, minsize=1)
        self.grid_columnconfigure(ct_col,  weight=1)

        # Sidebar
        self._sidebar = self._build_sidebar()
        self._sidebar.grid(row=0, column=sb_col, sticky="nsew")

        # Separator line between sidebar and content
        self._separator = ctk.CTkFrame(
            self, width=1, corner_radius=0,
            fg_color=("gray80", "gray25"),
        )
        self._separator.grid(row=0, column=sep_col, sticky="nsew")

        # Page container
        self._page_container = ctk.CTkFrame(
            self, corner_radius=0, fg_color="transparent",
        )
        self._page_container.grid(row=0, column=ct_col, sticky="nsew")
        self._page_container.grid_rowconfigure(0, weight=1)
        self._page_container.grid_columnconfigure(0, weight=1)

        self._build_pages()
        self._show("vector")

    def _build_sidebar(self) -> ctk.CTkFrame:
        rtl = is_rtl()
        sb = ctk.CTkFrame(self, width=SIDEBAR_W, corner_radius=0)
        sb.grid_propagate(False)
        sb.grid_columnconfigure(0, weight=1)
        sb.grid_rowconfigure(len(NAV) + 2, weight=1)   # push version to bottom

        # ── Brand ────────────────────────────────────────────────────────
        brand = ctk.CTkFrame(sb, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=14, pady=(26, 12))

        ctk.CTkLabel(
            brand, text="◈",
            font=ctk.CTkFont("Segoe UI", 46, "bold"),
        ).pack()

        self._sb_title = ctk.CTkLabel(
            brand, text=t("app_name"),
            font=ctk.CTkFont("Segoe UI", 18, "bold"),
        )
        self._sb_title.pack(pady=(2, 0))

        self._sb_tagline = ctk.CTkLabel(
            brand, text=t("tagline"),
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=("gray50", "gray55"),
            wraplength=SIDEBAR_W - 28,
        )
        self._sb_tagline.pack(pady=(2, 0))

        # Separator under brand
        ctk.CTkFrame(
            sb, height=1, fg_color=("gray80", "gray30"), corner_radius=0,
        ).grid(row=1, column=0, sticky="ew", padx=12, pady=(4, 8))

        # ── Nav buttons ──────────────────────────────────────────────────
        for idx, (pid, icon, key) in enumerate(NAV):
            btn = ctk.CTkButton(
                sb,
                text=f"  {icon}  {t(key)}",
                anchor="e" if rtl else "w",
                height=50,
                corner_radius=10,
                fg_color="transparent",
                hover_color=("gray85", "gray25"),
                font=ctk.CTkFont("Segoe UI", 13),
                command=lambda p=pid: self._show(p),
            )
            btn.grid(row=idx + 2, column=0, sticky="ew", padx=10, pady=2)
            self._nav_btns[pid] = btn

        # Version label at bottom
        ctk.CTkLabel(
            sb, text="v1.0",
            font=ctk.CTkFont("Segoe UI", 9),
            text_color=("gray60", "gray45"),
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
                    text_color=("white", "white"),
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    hover_color=("gray85", "gray25"),
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
        """Bring the window to the front (called on notification click)."""
        try:
            self.deiconify()
            self.lift()
            self.focus_force()
            self.state("zoomed")
        except Exception:
            pass

    def _full_rebuild(self):
        """Destroy everything and rebuild so lang/theme applies instantly."""
        active = self._active_page
        if self._sidebar:
            self._sidebar.destroy()
        if self._separator:
            self._separator.destroy()
        if self._page_container:
            self._page_container.destroy()
        self._nav_btns.clear()
        self._pages.clear()
        self._build_layout()
        self._show(active)
