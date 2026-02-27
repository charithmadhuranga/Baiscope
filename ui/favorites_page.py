"""Favorites page — shows user-saved media items (persisted to disk)."""

from __future__ import annotations

import json
from pathlib import Path

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
from ui.widgets.card import ClickableCard
from workers.image_worker import ImageWorker


FAVORITES_PATH = Path.home() / ".baiscope" / "favorites.json"


class FavoritesPage(QWidget):
    """Displays user-favorited media items loaded from disk."""

    def __init__(self, on_card_click, parent=None) -> None:
        super().__init__(parent)
        self._on_card_click = on_card_click
        self._image_cache = ImageCache()
        self._cards: list[ClickableCard] = []
        self._card_url_map: dict[str, ClickableCard] = {}
        self._current_items: list[dict] = []
        self.setObjectName("FavoritesPage")
        self._build_ui()
        self._apply_style()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 12)
        root.setSpacing(16)

        header = QLabel("Favorites ⭐")
        header.setObjectName("PageHeader")
        root.addWidget(header)

        self.status_label = QLabel("")
        self.status_label.setObjectName("StatusLabel")
        root.addWidget(self.status_label)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setObjectName("ResultsScroll")
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll.setWidget(self.grid_container)

        root.addWidget(self.scroll, stretch=1)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            #FavoritesPage { background: transparent; }
            #PageHeader {
                color: #ffffff;
                font-size: 26px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }
            #StatusLabel { color: #888; font-size: 13px; }
            #ResultsScroll { background: transparent; border: none; }
            """
        )

    # ------------------------------------------------------------------ #
    #  Resize — reflow grid                                                #
    # ------------------------------------------------------------------ #
    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._current_items:
            self._reflow_grid()

    def _reflow_grid(self) -> None:
        cols = max(
            1, self.scroll.viewport().width() // (ClickableCard.CARD_WIDTH + 20)
        )
        for idx, card in enumerate(self._cards):
            self.grid_layout.removeWidget(card)
            self.grid_layout.addWidget(card, idx // cols, idx % cols)

    # ------------------------------------------------------------------ #
    #  Load / Save                                                         #
    # ------------------------------------------------------------------ #
    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.refresh()

    def refresh(self) -> None:
        """Reload favorites from disk."""
        self._clear_grid()
        items = self._load_favorites()
        self._current_items = items

        if not items:
            self.status_label.setText(
                "No favorites yet. Click ☆ on a detail page to add one."
            )
            return

        self.status_label.setText(f"{len(items)} favorite(s)")
        cols = max(
            1, self.scroll.viewport().width() // (ClickableCard.CARD_WIDTH + 20)
        )
        for idx, item in enumerate(items):
            card = ClickableCard(
                title=item.get("title", ""),
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

    def _clear_grid(self) -> None:
        self._card_url_map.clear()
        self._current_items.clear()
        for card in self._cards:
            self.grid_layout.removeWidget(card)
            card.setParent(None)
            card.deleteLater()
        self._cards.clear()

    @staticmethod
    def _load_favorites() -> list[dict]:
        if not FAVORITES_PATH.exists():
            return []
        try:
            return json.loads(FAVORITES_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            return []

    @staticmethod
    def add_favorite(item: dict) -> None:
        """Add a media item to favorites."""
        items = FavoritesPage._load_favorites()
        # Avoid duplicates
        if any(f.get("detail_url") == item.get("detail_url") for f in items):
            return
        items.append(item)
        FAVORITES_PATH.parent.mkdir(parents=True, exist_ok=True)
        FAVORITES_PATH.write_text(json.dumps(items, indent=2))

    @staticmethod
    def remove_favorite(detail_url: str) -> None:
        """Remove a media item from favorites."""
        items = FavoritesPage._load_favorites()
        items = [f for f in items if f.get("detail_url") != detail_url]
        FAVORITES_PATH.parent.mkdir(parents=True, exist_ok=True)
        FAVORITES_PATH.write_text(json.dumps(items, indent=2))

    # ------------------------------------------------------------------ #
    #  Image loading                                                       #
    # ------------------------------------------------------------------ #
    def _load_image(self, url: str) -> None:
        worker = ImageWorker(url, self._image_cache)
        worker.signals.finished.connect(self._on_image_loaded)
        QThreadPool.globalInstance().start(worker)

    def _on_image_loaded(self, url: str, path: str) -> None:
        card = self._card_url_map.get(url)
        if card:
            px = QPixmap(path)
            if not px.isNull():
                card.set_pixmap(px)
