"""Site Catalog page — displays streaming sites grouped by category."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from db import Database


class SiteCard(QFrame):
    """Clickable card representing a streaming site."""

    clicked = Signal(str)  # site name

    CARD_WIDTH = 220
    CARD_HEIGHT = 120

    def __init__(
        self, name: str, url: str, category: str, icon: str, parent=None
    ) -> None:
        super().__init__(parent)
        self.site_name = name
        self.setFixedSize(self.CARD_WIDTH, self.CARD_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("SiteCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        # Icon + Name row
        top = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 28px;")
        top.addWidget(icon_label)

        name_label = QLabel(name)
        name_label.setObjectName("SiteName")
        name_label.setWordWrap(True)
        top.addWidget(name_label, stretch=1)
        layout.addLayout(top)

        # Category badge
        badge = QLabel(category.upper())
        badge.setObjectName("CategoryBadge")
        badge.setFixedHeight(20)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        badge_color = {
            "movie": "#e74c3c",
            "drama": "#9b59b6",
            "anime": "#3498db",
            "torrent": "#27ae60",
            "adult": "#e67e22",
        }.get(category, "#95a5a6")
        badge.setStyleSheet(
            f"background: {badge_color}; color: white; border-radius: 4px; "
            f"font-size: 10px; font-weight: bold; padding: 2px 8px;"
        )
        layout.addWidget(badge)

        # URL
        url_label = QLabel(url.replace("https://", "").replace("http://", "")[:35])
        url_label.setObjectName("SiteUrl")
        layout.addWidget(url_label)

        layout.addStretch()
        self._apply_style()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            #SiteCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1e1e2e, stop:1 #2a2a3e);
                border: 1px solid #3a3a5a;
                border-radius: 12px;
            }
            #SiteCard:hover {
                border: 1px solid #7c3aed;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #252540, stop:1 #302050);
            }
            #SiteName {
                color: #e0e0e0;
                font-size: 15px;
                font-weight: 600;
            }
            #SiteUrl {
                color: #666;
                font-size: 11px;
            }
            """
        )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.site_name)
        super().mousePressEvent(event)


class SiteCatalogPage(QWidget):
    """Displays available streaming sites organized by category.

    Signals
    -------
    site_selected : str
        Emitted with the site name when a user clicks a site card.
    """

    site_selected = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.db = Database()
        self.setObjectName("SiteCatalogPage")
        self._build_ui()
        self._apply_style()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 12)
        root.setSpacing(16)

        header = QLabel("🌐 Streaming Sites")
        header.setObjectName("PageHeader")
        root.addWidget(header)

        self.status_label = QLabel("")
        self.status_label.setObjectName("StatusLabel")
        root.addWidget(self.status_label)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setObjectName("SitesScroll")
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setSpacing(20)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.addStretch()

        self.scroll.setWidget(self.content)
        root.addWidget(self.scroll, stretch=1)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            #SiteCatalogPage { background: transparent; }
            #PageHeader {
                color: #ffffff;
                font-size: 26px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }
            #StatusLabel { color: #888; font-size: 13px; }
            #SitesScroll { background: transparent; border: none; }
            #CategoryHeader {
                color: #ccc;
                font-size: 18px;
                font-weight: 600;
                padding-top: 8px;
            }
            """
        )

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.refresh()

    def refresh(self) -> None:
        """Reload site list from DB."""
        # Clear existing content
        while self.content_layout.count() > 1:
            item = self.content_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            sub = item.layout()
            if sub:
                while sub.count():
                    child = sub.takeAt(0)
                    cw = child.widget()
                    if cw:
                        cw.deleteLater()

        show_adult = self.db.get_setting("show_xmovies", False)
        sites = self.db.get_enabled_sites(include_adult=show_adult)

        if not sites:
            self.status_label.setText("No sites available.")
            return

        self.status_label.setText(f"{len(sites)} streaming site(s) available")

        # Group by category
        categories: dict[str, list[dict]] = {}
        category_order = ["movie", "drama", "anime", "torrent", "adult"]

        for site in sites:
            cat = site["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(site)

        # Display in order
        for cat in category_order:
            if cat not in categories:
                continue

            cat_label = QLabel(
                {
                    "movie": "🎬 Movies",
                    "drama": "📺 Drama",
                    "anime": "🔵 Anime",
                    "torrent": "🧲 Torrents",
                    "adult": "🔞 X Movies",
                }.get(cat, cat.title())
            )
            cat_label.setObjectName("CategoryHeader")
            idx = self.content_layout.count() - 1
            self.content_layout.insertWidget(idx, cat_label)

            grid = QGridLayout()
            grid.setSpacing(12)
            cols = max(1, (self.scroll.viewport().width() - 20) // (SiteCard.CARD_WIDTH + 16))

            for i, site in enumerate(categories[cat]):
                card = SiteCard(
                    name=site["name"],
                    url=site["url"],
                    category=site["category"],
                    icon=site["icon"],
                )
                card.clicked.connect(self.site_selected.emit)
                grid.addWidget(card, i // cols, i % cols)

            grid_widget = QWidget()
            grid_widget.setLayout(grid)
            idx = self.content_layout.count() - 1
            self.content_layout.insertWidget(idx, grid_widget)
