"""Custom Catalog page UI for Baiscope."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from db import Database
from ui.widgets.card import ClickableCard


class CatalogPage(QWidget):
    play_requested = Signal(str)

    def __init__(self, on_card_click=None, parent=None) -> None:
        super().__init__(parent)
        self.db = Database()
        self.on_card_click = on_card_click
        self._build_ui()
        self._load_catalogs()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        header = QHBoxLayout()

        self.title_label = QLabel("📁 My Catalogs")
        self.title_label.setStyleSheet(
            "font-size: 24px; font-weight: bold; color: #e0e0e0;"
        )
        header.addWidget(self.title_label)

        header.addStretch()

        self.catalog_combo = QComboBox()
        self.catalog_combo.setMinimumWidth(200)
        self.catalog_combo.currentIndexChanged.connect(self._on_catalog_changed)
        header.addWidget(QLabel("Catalog:"))
        header.addWidget(self.catalog_combo)

        self.add_current_btn = QPushButton("Add Current to Catalog")
        self.add_current_btn.setStyleSheet("""
            QPushButton {
                background: #7c3aed;
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #6d28d9;
            }
        """)
        self.add_current_btn.clicked.connect(self._add_current_to_catalog)
        header.addWidget(self.add_current_btn)

        layout.addLayout(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.cards_widget = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_widget)
        self.cards_layout.setSpacing(10)
        self.cards_layout.addStretch()

        self.scroll.setWidget(self.cards_widget)
        layout.addWidget(self.scroll)

    def _load_catalogs(self) -> None:
        self.catalog_combo.blockSignals(True)
        self.catalog_combo.clear()

        catalogs = self.db.get_catalogs()

        self.catalog_combo.addItem("All Media", "all")

        for cat in catalogs:
            self.catalog_combo.addItem(cat["name"], cat["id"])

        self.catalog_combo.addItem("Uncategorized", "uncategorized")

        self.catalog_combo.blockSignals(False)
        self._load_media()

    def _on_catalog_changed(self, index: int) -> None:
        self._load_media()

    def _load_media(self) -> None:
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        catalog_id = self.catalog_combo.currentData()

        if catalog_id == "all":
            media_items = self.db.get_all_media()
        elif catalog_id == "uncategorized":
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM media WHERE catalog_name IS NULL ORDER BY created_at DESC"
            )
            rows = cursor.fetchall()
            conn.close()

            media_items = [self.db._row_to_media(row) for row in rows]
        else:
            catalog_name = self.catalog_combo.currentText()
            media_items = self.db.get_media_by_catalog(catalog_name)

        if not media_items:
            empty_label = QLabel(
                "No media in this catalog yet.\nBrowse and add content to your catalogs!"
            )
            empty_label.setStyleSheet(
                "color: #666; font-size: 14px; text-align: center;"
            )
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.cards_layout.insertWidget(0, empty_label)
        else:
            for item in media_items:
                card = ClickableCard(
                    title=item.title,
                    cover_url=item.cover_url,
                    detail_url=item.detail_url,
                )
                card.clicked.connect(
                    lambda url=item.detail_url: self._on_card_click(url)
                )

                card_container = QWidget()
                card_container_layout = QHBoxLayout(card_container)
                card_container_layout.setContentsMargins(0, 0, 0, 0)
                card_container_layout.addWidget(card)

                remove_btn = QPushButton("✕")
                remove_btn.setFixedSize(30, 30)
                remove_btn.setStyleSheet("""
                    QPushButton {
                        background: #c0392b;
                        color: white;
                        border-radius: 15px;
                    }
                    QPushButton:hover {
                        background: #e74c3c;
                    }
                """)
                media_id = item.id
                if media_id is not None:
                    remove_btn.clicked.connect(
                        lambda checked, mid=media_id: self._remove_media(mid)
                    )
                card_container_layout.addWidget(remove_btn)

                self.cards_layout.insertWidget(
                    self.cards_layout.count() - 1, card_container
                )

    def _on_card_click(self, detail_url: str) -> None:
        if self.on_card_click:
            self.on_card_click(detail_url)

    def _remove_media(self, media_id: int) -> None:
        self.db.delete_media(media_id)
        self._load_media()

    def _add_current_to_catalog(self) -> None:
        main_window = self.window()
        if hasattr(main_window, "detail_page"):
            detail_data = main_window.detail_page.get_current_media()
            if detail_data:
                catalog_name = self.catalog_combo.currentText()
                if catalog_name in ("all", "Uncategorized"):
                    QMessageBox.warning(
                        self, "Select Catalog", "Please select a valid catalog first"
                    )
                    return

                self.db.add_media(
                    title=detail_data.get("title", ""),
                    cover_url=detail_data.get("cover_url", ""),
                    detail_url=detail_data.get("detail_url", ""),
                    source=detail_data.get("source", ""),
                    source_name=detail_data.get("source_name", ""),
                    media_type=detail_data.get("media_type", ""),
                    catalog_name=catalog_name,
                )

                QMessageBox.information(
                    self, "Added", f"Added to '{catalog_name}' catalog!"
                )
                self._load_media()
            else:
                QMessageBox.information(
                    self,
                    "No Media",
                    "Open a media detail page first to add it to catalog",
                )

    def refresh(self) -> None:
        self._load_catalogs()
