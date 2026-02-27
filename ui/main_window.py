"""MainWindow — primary application window wiring pages and navigation."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QWidget,
)

from scrapers import GogoAnimeScraper, YTSScraper, DramacoolScraper, VidSrcAnimeScraper, MovieScraper, DramaScraper
from scrapers.base import BaseScraper
from ui.browse_page import BrowsePage
from ui.detail_page import DetailPage
from ui.favorites_page import FavoritesPage
from ui.player_page import PlayerPage
from ui.search_page import SearchPage
from ui.widgets.nav_bar import NavBar
from workers.stream_worker import StreamWorker


class MainWindow(QMainWindow):
    """Top-level application window.

    Layout:
        [NavBar] | [StackedWidget of pages]
    """

    PAGE_SEARCH = 0
    PAGE_ANIME = 1
    PAGE_MOVIES = 2
    PAGE_SERIES = 3
    PAGE_FAVORITES = 4
    PAGE_DETAIL = 5
    PAGE_PLAYER = 6

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Baiscope — Media Streaming")
        self.setMinimumSize(1080, 700)
        self.resize(1280, 800)

        # Scrapers (shared instances for detail resolution)
        self._scrapers: dict[str, BaseScraper] = {
            "anime": GogoAnimeScraper(),
            "anime_vidsrc": VidSrcAnimeScraper(),
            "movie": MovieScraper(),
            "drama": DramaScraper(),
        }
        self._last_scraper_category: str = "anime"
        self._stream_worker: StreamWorker | None = None

        self._build_ui()
        self._apply_global_style()

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
        layout.addWidget(self.nav_bar)

        # Stacked pages
        self.stack = QStackedWidget()
        self.stack.setObjectName("PageStack")

        # 0 — Search
        self.search_page = SearchPage(on_card_click=self._open_detail)
        self.stack.addWidget(self.search_page)

        # 1 — Anime browse
        self.anime_page = BrowsePage(
            "Anime 🎌",
            self._scrapers["anime"],
            on_card_click=self._open_detail_anime,
        )
        self.stack.addWidget(self.anime_page)

        # 2 — Movies browse
        self.movies_page = BrowsePage(
            "Movies 🎬",
            self._scrapers["movie"],
            on_card_click=self._open_detail_movie,
        )
        self.stack.addWidget(self.movies_page)

        # 3 — Series browse
        self.series_page = BrowsePage(
            "Series 📺",
            self._scrapers["drama"],
            on_card_click=self._open_detail_drama,
        )
        self.stack.addWidget(self.series_page)

        # 4 — Favorites
        self.favorites_page = FavoritesPage(on_card_click=self._open_detail)
        self.stack.addWidget(self.favorites_page)

        # 5 — Detail
        self.detail_page = DetailPage()
        self.detail_page.play_requested.connect(self._play_episode)
        self.detail_page.back_requested.connect(self._back_from_detail)
        self.stack.addWidget(self.detail_page)

        # 6 — Player
        self.player_page = PlayerPage()
        self.player_page.back_requested.connect(self._back_from_player)
        self.stack.addWidget(self.player_page)

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
        # Guard: don't navigate beyond the normal pages
        if 0 <= index <= self.PAGE_FAVORITES:
            self.stack.setCurrentIndex(index)

    def _previous_page_index(self) -> int:
        """Best-guess of which page to go back to."""
        idx = self.stack.currentIndex()
        if idx in (self.PAGE_DETAIL, self.PAGE_PLAYER):
            # Go back to whatever nav button is checked
            for i, btn in enumerate(self.nav_bar.buttons):
                if btn.isChecked():
                    return i
            return self.PAGE_SEARCH
        return self.PAGE_SEARCH

    # ------------------------------------------------------------------ #
    #  Detail page routing                                                 #
    # ------------------------------------------------------------------ #
    def _open_detail(self, detail_url: str) -> None:
        """Open the detail page using a heuristic to pick the right scraper."""
        scraper = self._guess_scraper(detail_url)
        self.detail_page.load(scraper, detail_url)
        self.stack.setCurrentIndex(self.PAGE_DETAIL)

    def _open_detail_anime(self, detail_url: str) -> None:
        self._last_scraper_category = "anime"
        self.detail_page.load(self._scrapers["anime"], detail_url)
        self.stack.setCurrentIndex(self.PAGE_DETAIL)

    def _open_detail_movie(self, detail_url: str) -> None:
        self._last_scraper_category = "movie"
        self.detail_page.load(self._scrapers["movie"], detail_url)
        self.stack.setCurrentIndex(self.PAGE_DETAIL)

    def _open_detail_drama(self, detail_url: str) -> None:
        self._last_scraper_category = "drama"
        self.detail_page.load(self._scrapers["drama"], detail_url)
        self.stack.setCurrentIndex(self.PAGE_DETAIL)

    def _guess_scraper(self, url: str) -> BaseScraper:
        """Pick the right scraper based on the URL domain or last known category."""
        url_lower = url.lower()
        if "gogoanime" in url_lower or "anitaku" in url_lower:
            return self._scrapers["anime"]
        if "yts" in url_lower:
            return self._scrapers["movie"]
        if "dramacool" in url_lower:
            return self._scrapers["drama"]
        return self._scrapers.get(
            self._last_scraper_category, self._scrapers["anime"]
        )

    # ------------------------------------------------------------------ #
    #  Playback (async stream extraction)                                  #
    # ------------------------------------------------------------------ #
    def _play_episode(self, episode_url: str) -> None:
        """Extract stream URL asynchronously and open the player page."""
        scraper = self._scrapers.get(
            self._last_scraper_category, self._scrapers["anime"]
        )
        self.detail_page.status_label.setText("⏳ Extracting stream URL…")

        self._stream_worker = StreamWorker(scraper, episode_url, parent=self)
        self._stream_worker.stream_ready.connect(self._on_stream_ready)
        self._stream_worker.error.connect(self._on_stream_error)
        self._stream_worker.start()

    def _on_stream_ready(self, stream_data: dict | str) -> None:
        self.detail_page.status_label.setText("")
        # stream_data might be a dict {"url": str, "headers": dict}
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
