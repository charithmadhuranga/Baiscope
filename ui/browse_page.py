"""Browse page — category browsing (Anime / Movies / Series)."""

from __future__ import annotations

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from cache.image_cache import ImageCache
from scrapers.base import BaseScraper
from ui.widgets.card import ClickableCard
from workers.image_worker import ImageWorker
from workers.search_worker import SearchWorker


class BrowsePage(QWidget):
    """Displays trending/popular content for a given category scraper."""

    def __init__(
        self,
        title: str,
        scraper: BaseScraper | None,
        on_card_click,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._title = title
        self._scraper = scraper
        self._on_card_click = on_card_click
        self._image_cache = ImageCache()
        self._cards: list[ClickableCard] = []
        self._card_url_map: dict[str, ClickableCard] = {}
        self._loaded = False
        self._current_page = 1
        self._is_loading = False
        self._worker: SearchWorker | None = None
        self._current_results: list[dict[str, str]] = []

        self.setObjectName("BrowsePage")
        self._build_ui()
        self._apply_style()

    def set_scraper(
        self, scraper: BaseScraper, title: str = "", category: str = ""
    ) -> None:
        """Switch the page to a new scraper/site dynamically."""
        self._scraper = scraper
        if title:
            self._title = title
            # Update header label
            for child in self.findChildren(QLabel, "PageHeader"):
                child.setText(title)
        self._loaded = False
        self._clear_grid()
        self._fetch_trending()


    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 12)
        root.setSpacing(16)

        header = QLabel(self._title)
        header.setObjectName("PageHeader")
        root.addWidget(header)

        self.status_label = QLabel("Loading…")
        self.status_label.setObjectName("StatusLabel")
        root.addWidget(self.status_label)

        # Refresh button
        self.refresh_btn = QPushButton("↻  Refresh")
        self.refresh_btn.setObjectName("RefreshBtn")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self._fetch_trending)
        self.refresh_btn.setVisible(False)
        root.addWidget(self.refresh_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setObjectName("ResultsScroll")
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.verticalScrollBar().valueChanged.connect(self._on_scroll)

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll.setWidget(self.grid_container)

        root.addWidget(self.scroll, stretch=1)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            #BrowsePage { background: transparent; }
            #PageHeader {
                color: #ffffff;
                font-size: 26px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }
            #StatusLabel {
                color: #888;
                font-size: 13px;
            }
            #ResultsScroll {
                background: transparent;
                border: none;
            }
            #RefreshBtn {
                background: rgba(139,92,246,0.12);
                border: 1px solid rgba(139,92,246,0.25);
                border-radius: 8px;
                color: #b794f6;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: 600;
            }
            #RefreshBtn:hover { background: rgba(139,92,246,0.22); }
            """
        )

    # ------------------------------------------------------------------ #
    #  Resize — reflow grid                                                #
    # ------------------------------------------------------------------ #
    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._current_results:
            self._reflow_grid()

    def _reflow_grid(self) -> None:
        cols = self._calc_columns()
        for idx, card in enumerate(self._cards):
            self.grid_layout.removeWidget(card)
            self.grid_layout.addWidget(card, idx // cols, idx % cols)

    def _calc_columns(self) -> int:
        return max(1, self.scroll.viewport().width() // (ClickableCard.CARD_WIDTH + 20))

    # ------------------------------------------------------------------ #
    #  Lazy load on first show                                             #
    # ------------------------------------------------------------------ #
    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if not self._loaded:
            self._loaded = True
            self._fetch_trending()

    def _fetch_trending(self, page: int = 1) -> None:
        if self._is_loading:
            return

        self._is_loading = True
        self._current_page = page

        if page == 1:
            self._clear_grid()
            self.status_label.setText("🔍 Loading popular titles…")
        else:
            self.status_label.setText(f"🔍 Loading page {page}…")

        self.refresh_btn.setVisible(False)

        # Use a search query that tends to return popular content
        queries = {
            "anime": "popular",
            "movie": "2024",
            "drama": "popular",
        }
        query = queries.get(self._scraper.CATEGORY, "popular")
        self._worker = SearchWorker(self._scraper, query, page=page)
        self._worker.results_ready.connect(self._on_results)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_scroll(self, value: int) -> None:
        scrollbar = self.scroll.verticalScrollBar()
        if value == scrollbar.maximum() and not self._is_loading and value > 0:
            self._fetch_trending(page=self._current_page + 1)

    def _on_results(self, results: list[dict[str, str]]) -> None:
        self._is_loading = False

        if not results and self._current_page == 1:
            self.status_label.setText(
                "No content available. The site may be unreachable."
            )
            self.refresh_btn.setVisible(True)
            return
        elif not results:
            self.status_label.setText(
                f"{len(self._current_results)} titles loaded (No more content)"
            )
            return

        is_new = self._current_page == 1

        if is_new:
            self._current_results = results
        else:
            self._current_results.extend(results)

        self.status_label.setText(f"{len(self._current_results)} titles")
        self.refresh_btn.setVisible(True)
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

            if cover:
                self._load_image(cover)

    def _on_error(self, msg: str) -> None:
        self._is_loading = False
        self.status_label.setText(f"⚠ {msg}")
        self.refresh_btn.setVisible(True)

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #
    def _clear_grid(self) -> None:
        self._card_url_map.clear()
        self._current_results.clear()
        for card in self._cards:
            self.grid_layout.removeWidget(card)
            card.setParent(None)
            card.deleteLater()
        self._cards.clear()

    def _load_image(self, url: str) -> None:
        headers = {"Referer": self._scraper.BASE_URL}
        worker = ImageWorker(url, self._image_cache, headers=headers)
        worker.signals.finished.connect(self._on_image_loaded)
        QThreadPool.globalInstance().start(worker)

    def _on_image_loaded(self, url: str, path: str) -> None:
        card = self._card_url_map.get(url)
        if card:
            px = QPixmap(path)
            if not px.isNull():
                card.set_pixmap(px)

    def set_adult_visible(self, visible: bool) -> None:
        """Show or hide adult content."""
        for card in self._cards:
            card.setVisible(visible)
        if not visible:
            self.status_label.setText("Adult content hidden (enable in Settings)")
        elif self._current_results:
            self.status_label.setText(f"{len(self._current_results)} titles")
