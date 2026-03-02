"""Search page — search bar + site source selector + results grid."""

from __future__ import annotations

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from cache.image_cache import ImageCache
from db import Database
from scrapers import SCRAPER_REGISTRY
from scrapers.base import BaseScraper
from ui.widgets.card import ClickableCard
from workers.image_worker import ImageWorker
from workers.search_worker import SearchWorker


class SearchPage(QWidget):
    """Page with a search bar, source site selector, and card-grid results.

    The user must select a streaming source before searching.
    """

    def __init__(self, on_card_click, parent=None) -> None:
        super().__init__(parent)
        self._on_card_click = on_card_click
        self.setObjectName("SearchPage")

        self.db = Database()
        self._image_cache = ImageCache()
        self._cards: list[ClickableCard] = []
        self._workers: list[SearchWorker] = []
        self._card_url_map: dict[str, ClickableCard] = {}
        self._current_results: list[dict[str, str]] = []
        self._pending = 0
        self._current_page = 1
        self._is_loading = False
        self._all_results: list[dict[str, str]] = []

        self._build_ui()
        self._apply_style()

    # ------------------------------------------------------------------ #
    #  Layout                                                              #
    # ------------------------------------------------------------------ #
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 12)
        root.setSpacing(16)

        # Header
        header = QLabel("🔍 Search")
        header.setObjectName("PageHeader")
        root.addWidget(header)

        # Search bar row
        bar_row = QHBoxLayout()
        bar_row.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search for anime, movies, series…")
        self.search_input.setObjectName("SearchInput")
        self.search_input.setMinimumHeight(42)
        self.search_input.returnPressed.connect(self._do_search)
        bar_row.addWidget(self.search_input, stretch=1)

        # Source site selector (replaces old category dropdown)
        self.source_combo = QComboBox()
        self.source_combo.setObjectName("CategoryCombo")
        self.source_combo.setMinimumHeight(42)
        self.source_combo.setMinimumWidth(160)
        self._populate_sources()
        bar_row.addWidget(self.source_combo)

        self.search_btn = QPushButton("Search")
        self.search_btn.setObjectName("SearchBtn")
        self.search_btn.setMinimumHeight(42)
        self.search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_btn.clicked.connect(self._do_search)
        bar_row.addWidget(self.search_btn)

        root.addLayout(bar_row)

        # Status
        self.status_label = QLabel("Select a source and enter a search query")
        self.status_label.setObjectName("StatusLabel")
        root.addWidget(self.status_label)

        # Scroll area with grid
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setObjectName("ResultsScroll")
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll.verticalScrollBar().valueChanged.connect(self._on_scroll)

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll.setWidget(self.grid_container)

        root.addWidget(self.scroll, stretch=1)

    def _populate_sources(self) -> None:
        """Populate the source combo with enabled sites from DB."""
        self.source_combo.clear()
        self.source_combo.addItem("All Sources")

        show_adult = self.db.get_setting("show_xmovies", False)
        sites = self.db.get_enabled_sites(include_adult=show_adult)

        for site in sites:
            icon = site.get("icon", "")
            name = site["name"]
            display = f"{icon} {name}" if icon else name
            self.source_combo.addItem(display, userData=name)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        # Refresh source list each time the page is shown
        current = self.source_combo.currentData()
        self._populate_sources()
        # Try to restore previous selection
        if current:
            for i in range(self.source_combo.count()):
                if self.source_combo.itemData(i) == current:
                    self.source_combo.setCurrentIndex(i)
                    break

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            #SearchPage {
                background: transparent;
            }
            #PageHeader {
                color: #ffffff;
                font-size: 26px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }
            #SearchInput {
                background: #1e1e2e;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px;
                color: #e0e0e0;
                padding: 0 16px;
                font-size: 14px;
            }
            #SearchInput:focus {
                border: 1px solid rgba(139,92,246,0.6);
            }
            #CategoryCombo {
                background: #1e1e2e;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px;
                color: #e0e0e0;
                padding: 0 14px;
                font-size: 13px;
                min-width: 100px;
            }
            #CategoryCombo QAbstractItemView {
                background: #1e1e2e;
                color: #e0e0e0;
                selection-background-color: rgba(139,92,246,0.3);
            }
            #CategoryCombo::drop-down {
                border: none;
                padding-right: 8px;
            }
            #SearchBtn {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #8b5cf6, stop:1 #6d28d9
                );
                border: none;
                border-radius: 10px;
                color: #fff;
                font-weight: 600;
                padding: 0 22px;
                font-size: 14px;
            }
            #SearchBtn:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #9d6eff, stop:1 #7c3aed
                );
            }
            #SearchBtn:disabled {
                background: #333;
                color: #666;
            }
            #StatusLabel {
                color: #888;
                font-size: 13px;
            }
            #ResultsScroll {
                background: transparent;
                border: none;
            }
            """
        )

    # ------------------------------------------------------------------ #
    #  Resize handling — reflow grid                                        #
    # ------------------------------------------------------------------ #
    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._current_results:
            self._reflow_grid()

    def _reflow_grid(self) -> None:
        """Re-arrange existing cards based on the current width."""
        cols = self._calc_columns()
        for idx, card in enumerate(self._cards):
            self.grid_layout.removeWidget(card)
            self.grid_layout.addWidget(card, idx // cols, idx % cols)

    def _calc_columns(self) -> int:
        return max(1, self.scroll.viewport().width() // (ClickableCard.CARD_WIDTH + 20))

    # ------------------------------------------------------------------ #
    #  Search logic                                                        #
    # ------------------------------------------------------------------ #
    def _do_search(self, page: int = 1) -> None:
        if self._is_loading and page == 1:
            return

        # Ensure it's called properly via signal (which passes False/True sometimes)
        if not isinstance(page, int):
            page = 1

        query = self.search_input.text().strip()
        if not query:
            return

        self._is_loading = True
        self._current_page = page

        self.search_btn.setEnabled(False)
        self.search_btn.setText("Searching…")

        if page == 1:
            self.status_label.setText("🔍 Searching…")
            self._clear_grid()
            self._current_results.clear()
            self._all_results.clear()
        else:
            self.status_label.setText(f"🔍 Searching page {page}…")

        # Get selected source
        selected_site = self.source_combo.currentData()
        scrapers_to_use: list[BaseScraper] = []

        if selected_site is None:
            # "All Sources" — search across all enabled sites
            show_adult = self.db.get_setting("show_xmovies", False)
            sites = self.db.get_enabled_sites(include_adult=show_adult)
            for site in sites:
                cls = SCRAPER_REGISTRY.get(site["name"])
                if cls:
                    scrapers_to_use.append(cls())
        else:
            cls = SCRAPER_REGISTRY.get(selected_site)
            if cls:
                scrapers_to_use = [cls()]

        if not scrapers_to_use:
            self._is_loading = False
            self.search_btn.setEnabled(True)
            self.search_btn.setText("Search")
            self.status_label.setText("No scrapers available for selected source.")
            return

        self._pending = len(scrapers_to_use)

        for scraper in scrapers_to_use:
            worker = SearchWorker(scraper, query, page=page)
            worker.results_ready.connect(self._on_results)
            worker.error.connect(self._on_error)
            worker.finished.connect(lambda w=worker: self._worker_done(w))
            self._workers.append(worker)
            worker.start()

    def _on_scroll(self, value: int) -> None:
        scrollbar = self.scroll.verticalScrollBar()
        if value == scrollbar.maximum() and not self._is_loading and self._current_results and value > 0:
            self._do_search(page=self._current_page + 1)

    def _on_results(self, results: list[dict[str, str]]) -> None:
        self._all_results.extend(results)

    def _on_error(self, msg: str) -> None:
        pass  # Handle in worker_done instead of updating status directly if multisearching

    def _worker_done(self, worker) -> None:
        self._pending -= 1
        if worker in self._workers:
            self._workers.remove(worker)
        if self._pending <= 0:
            self._is_loading = False
            self.search_btn.setEnabled(True)
            self.search_btn.setText("Search")
            self._populate_grid(self._all_results)
            self._all_results.clear()  # clear for next page append

    def _clear_grid(self) -> None:
        self._card_url_map.clear()
        for card in self._cards:
            self.grid_layout.removeWidget(card)
            card.setParent(None)
            card.deleteLater()
        self._cards.clear()

    def _populate_grid(self, results: list[dict[str, str]]) -> None:
        if not results and self._current_page == 1:
            self.status_label.setText("No results found.")
            return
        elif not results:
            self.status_label.setText(f"Found {len(self._current_results)} results (No more content)")
            return

        if self._current_page == 1:
            self._current_results = results
        else:
            self._current_results.extend(results)

        self.status_label.setText(f"Found {len(self._current_results)} results")
        cols = self._calc_columns()

        start_idx = len(self._cards)
        for i, item in enumerate(results):
            idx = start_idx + i
            card = ClickableCard(
                title=item["title"],
                cover_url=item.get("cover_url", ""),
                detail_url=item.get("detail_url", ""),
            )
            card.clicked.connect(self._on_card_click)
            self._cards.append(card)
            cover = item.get("cover_url", "")
            if cover:
                self._card_url_map[cover] = card

            self.grid_layout.addWidget(card, idx // cols, idx % cols)

            # Kick off async image download
            if cover:
                self._load_image(cover)

    def _load_image(self, url: str) -> None:
        # Generic url as referer helps with CDNs
        headers = {"Referer": url}
        worker = ImageWorker(url, self._image_cache, headers=headers)
        worker.signals.finished.connect(self._on_image_loaded)
        QThreadPool.globalInstance().start(worker)

    def _on_image_loaded(self, url: str, path: str) -> None:
        card = self._card_url_map.get(url)
        if card:
            px = QPixmap(path)
            if not px.isNull():
                card.set_pixmap(px)
