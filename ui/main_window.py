"""MainWindow — primary application window wiring pages and navigation."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QWidget,
)

from db import Database
from scrapers import SCRAPER_REGISTRY
from scrapers.base import BaseScraper
from ui.browse_page import BrowsePage
from ui.catalog_page import CatalogPage
from ui.detail_page import DetailPage
from ui.favorites_page import FavoritesPage
from ui.player_page import PlayerPage
from ui.search_page import SearchPage
from ui.settings_page import SettingsPage
from ui.site_catalog_page import SiteCatalogPage
from ui.widgets.nav_bar import NavBar
from workers.stream_worker import StreamWorker


class MainWindow(QMainWindow):
    """Top-level application window.

    Layout:
        [NavBar] | [StackedWidget of pages]
    """

    PAGE_SEARCH = 0
    PAGE_SITES = 1
    PAGE_FAVORITES = 2
    PAGE_CATALOGS = 3
    PAGE_DETAIL = 4
    PAGE_PLAYER = 5
    PAGE_SETTINGS = 6
    PAGE_BROWSE = 7  # Dynamic browse page inserted on site selection

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Baiscope — Media Streaming")
        self.setMinimumSize(1080, 700)
        self.resize(1280, 800)

        self.db = Database()
        self.db.initialize_default_settings()
        self.db.initialize_sites()

        # Cache scraper instances by site name
        self._scraper_cache: dict[str, BaseScraper] = {}
        self._current_scraper: BaseScraper | None = None
        self._current_site_name: str = ""
        self._stream_worker: StreamWorker | None = None

        self._build_ui()
        self._apply_global_style()

    # ------------------------------------------------------------------ #
    #  Scraper factory                                                     #
    # ------------------------------------------------------------------ #
    def _get_scraper(self, site_name: str) -> BaseScraper | None:
        """Get or create a scraper instance for the given site."""
        if site_name in self._scraper_cache:
            return self._scraper_cache[site_name]

        scraper_cls = SCRAPER_REGISTRY.get(site_name)
        if scraper_cls:
            instance = scraper_cls()
            self._scraper_cache[site_name] = instance
            return instance

        # Fallback: try to find by scraper_class in DB
        site = self.db.get_site_by_name(site_name)
        if site:
            cls_name = site["scraper_class"]
            for name, cls in SCRAPER_REGISTRY.items():
                if cls.__name__ == cls_name:
                    instance = cls()
                    self._scraper_cache[site_name] = instance
                    return instance

        return None

    # ------------------------------------------------------------------ #
    #  Build UI                                                            #
    # ------------------------------------------------------------------ #
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Sidebar navigation
        self.nav_bar = NavBar()
        self.nav_bar.page_changed.connect(self._on_nav)

        # Connect settings button
        self.nav_bar.settings_btn.clicked.connect(self._open_settings)

        layout.addWidget(self.nav_bar)

        # Stacked pages
        self.stack = QStackedWidget()
        self.stack.setObjectName("PageStack")

        # 0 — Search (now with source site selector)
        self.search_page = SearchPage(on_card_click=self._open_detail)
        self.stack.addWidget(self.search_page)

        # 1 — Sites catalog
        self.sites_page = SiteCatalogPage()
        self.sites_page.site_selected.connect(self._on_site_selected)
        self.stack.addWidget(self.sites_page)

        # 2 — Favorites
        self.favorites_page = FavoritesPage(on_card_click=self._open_detail)
        self.stack.addWidget(self.favorites_page)

        # 3 — Catalogs
        self.catalog_page = CatalogPage(on_card_click=self._open_detail)
        self.stack.addWidget(self.catalog_page)

        # 4 — Detail
        self.detail_page = DetailPage()
        self.detail_page.play_requested.connect(self._play_episode)
        self.detail_page.back_requested.connect(self._back_from_detail)
        self.stack.addWidget(self.detail_page)

        # 5 — Player
        self.player_page = PlayerPage()
        self.player_page.back_requested.connect(self._back_from_player)
        self.stack.addWidget(self.player_page)

        # 6 — Settings
        self.settings_page = SettingsPage()
        self.settings_page.settings_changed.connect(self._on_settings_changed)
        self.stack.addWidget(self.settings_page)

        # 7 — Dynamic browse page (created on site selection)
        self.browse_page = BrowsePage(
            "Browse",
            None,
            on_card_click=self._open_detail_from_browse,
        )
        self.stack.addWidget(self.browse_page)

        layout.addWidget(self.stack, stretch=1)

    # ------------------------------------------------------------------ #
    #  Global dark theme                                                   #
    # ------------------------------------------------------------------ #
    def _apply_global_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: #12121a;
            }
            #PageStack {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #12121a,
                    stop:1 #1a1a2e
                );
            }
            QScrollBar:vertical {
                background: #151520;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(139,92,246,0.3);
                min-height: 30px;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                height: 0px;
            }
            QToolTip {
                background: #1e1e2e;
                color: #e0e0e0;
                border: 1px solid rgba(139,92,246,0.3);
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 12px;
            }
            """
        )

    # ------------------------------------------------------------------ #
    #  Navigation                                                          #
    # ------------------------------------------------------------------ #
    def _on_nav(self, index: int) -> None:
        if 0 <= index <= self.PAGE_CATALOGS:
            self.stack.setCurrentIndex(index)

    def _open_settings(self) -> None:
        self.stack.setCurrentIndex(self.PAGE_SETTINGS)
        for btn in self.nav_bar.buttons:
            btn.setChecked(False)

    def _on_settings_changed(self) -> None:
        # Refresh sites page when settings change (e.g. adult toggle)
        self.sites_page.refresh()

    def _on_site_selected(self, site_name: str) -> None:
        """User clicked a site in the catalog — open browse page for it."""
        scraper = self._get_scraper(site_name)
        if not scraper:
            return

        self._current_scraper = scraper
        self._current_site_name = site_name

        site = self.db.get_site_by_name(site_name)
        icon = site.get("icon", "🌐") if site else "🌐"
        category = site.get("category", "") if site else ""

        self.browse_page.set_scraper(
            scraper,
            title=f"{icon} {site_name}",
            category=category,
        )
        self.stack.setCurrentIndex(self.PAGE_BROWSE)

    def _previous_page_index(self) -> int:
        """Best-guess of which page to go back to."""
        idx = self.stack.currentIndex()
        if idx == self.PAGE_BROWSE:
            return self.PAGE_SITES
        if idx in (self.PAGE_DETAIL, self.PAGE_PLAYER):
            for i, btn in enumerate(self.nav_bar.buttons):
                if btn.isChecked():
                    return i
            return self.PAGE_SITES
        return self.PAGE_SEARCH

    # ------------------------------------------------------------------ #
    #  Detail page routing                                                 #
    # ------------------------------------------------------------------ #
    def _open_detail(self, detail_url: str) -> None:
        """Open the detail page using the current or guessed scraper."""
        scraper = self._current_scraper or self._guess_scraper(detail_url)
        self._current_scraper = scraper
        self.detail_page.load(scraper, detail_url, source_site=self._current_site_name)
        self.stack.setCurrentIndex(self.PAGE_DETAIL)

    def _open_detail_from_browse(self, detail_url: str) -> None:
        """Open detail from the browse page (scraper is already known)."""
        scraper = self._current_scraper or self._guess_scraper(detail_url)
        self.detail_page.load(scraper, detail_url, source_site=self._current_site_name)
        self.stack.setCurrentIndex(self.PAGE_DETAIL)

    def _guess_scraper(self, url: str) -> BaseScraper:
        """Pick the right scraper based on URL domain patterns."""
        url_lower = url.lower()
        mappings = {
            "gogoanime": "GogoAnime",
            "anitaku": "GogoAnime",
            "movie2k": "Movie2K",
            "solarmovie": "SolarMovies",
            "moviestv": "FreeOnlineDrama",
            "freeonline": "FreeOnlineDrama",
            "luciferdonghua": "LuciferDonghua",
            "1337x": "1337x",
            "yts": "YTS",
            "dramacool": "Dramacool",
            "xmovie": "XMovies",
        }
        for pattern, site_name in mappings.items():
            if pattern in url_lower:
                scraper = self._get_scraper(site_name)
                if scraper:
                    self._current_site_name = site_name
                    return scraper

        # Fallback to first available
        if self._current_scraper:
            return self._current_scraper
        return self._get_scraper("GogoAnime") or list(SCRAPER_REGISTRY.values())[0]()

    # ------------------------------------------------------------------ #
    #  Playback (async stream extraction)                                  #
    # ------------------------------------------------------------------ #
    def _play_episode(self, episode_url: str) -> None:
        """Extract stream URL asynchronously and open the player page."""
        scraper = self._current_scraper or self._guess_scraper(episode_url)
        self.detail_page.status_label.setText("⏳ Extracting stream URL…")

        # Check if this is a torrent URL
        if episode_url.startswith("magnet:") or ".torrent" in episode_url:
            self._on_stream_ready({
                "url": episode_url,
                "headers": {},
                "type": "torrent",
            })
            return

        self._stream_worker = StreamWorker(scraper, episode_url, parent=self)
        self._stream_worker.stream_ready.connect(self._on_stream_ready)
        self._stream_worker.error.connect(self._on_stream_error)
        self._stream_worker.start()

    def _on_stream_ready(self, stream_data: dict | str) -> None:
        self.detail_page.status_label.setText("")
        self.player_page.play(stream_data, title="Now Playing")
        self.stack.setCurrentIndex(self.PAGE_PLAYER)

    def _on_stream_error(self, msg: str) -> None:
        self.detail_page.status_label.setText(f"⚠ {msg}")

    # ------------------------------------------------------------------ #
    #  Back navigation                                                     #
    # ------------------------------------------------------------------ #
    def _back_from_detail(self) -> None:
        self.stack.setCurrentIndex(self._previous_page_index())

    def _back_from_player(self) -> None:
        self.stack.setCurrentIndex(self.PAGE_DETAIL)
