"""Settings page UI for Baiscope."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from db import Database


class SettingsPage(QWidget):
    settings_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.db = Database()
        self.db.initialize_default_settings()
        self.setObjectName("SettingsPage")
        self._site_toggles: list[tuple[int, QCheckBox]] = []
        self._build_ui()
        self._apply_style()
        self._load_settings()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("SettingsScroll")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(20)

        title = QLabel("⚙️ Settings")
        title.setObjectName("PageHeader")
        scroll_layout.addWidget(title)

        # ── Content settings ─────────────────────────────────────────── #
        content_group = QGroupBox("Content")
        content_group.setObjectName("SettingsGroup")
        content_layout = QVBoxLayout()

        self.show_xmovies_check = QCheckBox("🔞 Show X Movies (adult content)")
        self.show_xmovies_check.setToolTip(
            "Toggle visibility of adult/X-rated sources in Sites and Search"
        )
        self.show_xmovies_check.stateChanged.connect(self._on_xmovies_changed)
        content_layout.addWidget(self.show_xmovies_check)

        content_group.setLayout(content_layout)
        scroll_layout.addWidget(content_group)

        # ── Sources ──────────────────────────────────────────────────── #
        self.sources_group = QGroupBox("Streaming Sources")
        self.sources_group.setObjectName("SettingsGroup")
        self.sources_layout = QVBoxLayout()

        sources_info = QLabel("Enable or disable individual streaming sites")
        sources_info.setObjectName("SubLabel")
        self.sources_layout.addWidget(sources_info)

        self.sites_container = QVBoxLayout()
        self.sources_layout.addLayout(self.sites_container)

        self.sources_group.setLayout(self.sources_layout)
        scroll_layout.addWidget(self.sources_group)

        # ── Catalogs ─────────────────────────────────────────────────── #
        catalog_group = QGroupBox("Custom Catalogs")
        catalog_group.setObjectName("SettingsGroup")
        catalog_layout = QVBoxLayout()

        catalog_form = QFormLayout()
        self.catalog_name_input = QLineEdit()
        self.catalog_name_input.setPlaceholderText("Enter catalog name")
        self.catalog_name_input.setObjectName("CatalogInput")
        catalog_form.addRow("Create New Catalog:", self.catalog_name_input)

        catalog_buttons = QHBoxLayout()
        create_btn = QPushButton("Create")
        create_btn.setObjectName("CreateBtn")
        create_btn.clicked.connect(self._create_catalog)
        catalog_buttons.addWidget(create_btn)

        catalog_layout.addLayout(catalog_form)
        catalog_layout.addLayout(catalog_buttons)

        self.catalogs_label = QLabel("Your Catalogs:")
        self.catalogs_label.setObjectName("SubLabel")
        self.catalogs_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        catalog_layout.addWidget(self.catalogs_label)

        self.catalogs_list = QVBoxLayout()
        catalog_layout.addLayout(self.catalogs_list)

        catalog_group.setLayout(catalog_layout)
        scroll_layout.addWidget(catalog_group)

        # ── About ────────────────────────────────────────────────────── #
        about_group = QGroupBox("About")
        about_group.setObjectName("SettingsGroup")
        about_layout = QVBoxLayout()
        about_text = QLabel(
            "Baiscope v2.0\nMedia Streaming Application\n\n"
            "🎬 Movies  •  📺 Drama  •  🔵 Anime  •  🧲 Torrents"
        )
        about_text.setObjectName("SubLabel")
        about_layout.addWidget(about_text)
        about_group.setLayout(about_layout)
        scroll_layout.addWidget(about_group)

        scroll_layout.addStretch()

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            #SettingsPage { background: transparent; }
            #PageHeader {
                color: #ffffff;
                font-size: 26px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }
            #SettingsGroup {
                background: #1a1a2e;
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 12px;
                color: #e0e0e0;
                font-size: 14px;
                font-weight: 600;
                padding: 12px;
                margin-top: 8px;
            }
            #SettingsGroup::title {
                color: #b794f6;
                font-weight: 700;
            }
            #SubLabel { color: #888; font-size: 12px; }
            #SettingsScroll { background: transparent; border: none; }
            QCheckBox {
                color: #e0e0e0;
                font-size: 13px;
                spacing: 8px;
                padding: 6px 0;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #555;
                border-radius: 4px;
                background: transparent;
            }
            QCheckBox::indicator:checked {
                background: #8b5cf6;
                border-color: #8b5cf6;
            }
            #CatalogInput {
                background: #12121a;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px;
                color: #e0e0e0;
                padding: 6px 12px;
                font-size: 13px;
            }
            #CreateBtn {
                background: rgba(139,92,246,0.2);
                border: 1px solid rgba(139,92,246,0.3);
                border-radius: 8px;
                color: #b794f6;
                padding: 6px 16px;
                font-weight: 600;
            }
            #CreateBtn:hover { background: rgba(139,92,246,0.3); }
            QPushButton {
                font-size: 12px;
            }
            """
        )

    # ------------------------------------------------------------------ #
    #  Show on page show                                                   #
    # ------------------------------------------------------------------ #
    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._load_settings()

    def _load_settings(self) -> None:
        self.show_xmovies_check.blockSignals(True)
        self.show_xmovies_check.setChecked(self.db.get_setting("show_xmovies", False))
        self.show_xmovies_check.blockSignals(False)
        self._refresh_sites()
        self._refresh_catalogs()

    # ------------------------------------------------------------------ #
    #  X Movies toggle                                                     #
    # ------------------------------------------------------------------ #
    def _on_xmovies_changed(self, state: int) -> None:
        enabled = state > 0
        self.db.set_setting("show_xmovies", enabled)
        # Also enable/disable the adult site
        site = self.db.get_site_by_name("XMovies")
        if site:
            self.db.toggle_site(site["id"], enabled)
        self._refresh_sites()
        self.settings_changed.emit()

    # ------------------------------------------------------------------ #
    #  Sites list                                                          #
    # ------------------------------------------------------------------ #
    def _refresh_sites(self) -> None:
        self._site_toggles.clear()
        while self.sites_container.count():
            item = self.sites_container.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        show_adult = self.db.get_setting("show_xmovies", False)
        sites = self.db.get_sites(include_adult=show_adult)

        for site in sites:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(4, 2, 4, 2)

            icon = site.get("icon", "")
            category = site.get("category", "")
            badge_color = {
                "movie": "#e74c3c",
                "drama": "#9b59b6",
                "anime": "#3498db",
                "torrent": "#27ae60",
                "adult": "#e67e22",
            }.get(category, "#95a5a6")

            badge = QLabel(f"{icon} {site['name']}")
            badge.setStyleSheet(
                f"color: #e0e0e0; font-size: 13px; background: {badge_color}; "
                f"border-radius: 4px; padding: 2px 8px; font-weight: 600;"
            )
            row_layout.addWidget(badge)

            url_label = QLabel(site["url"].replace("https://", "")[:30])
            url_label.setStyleSheet("color: #666; font-size: 11px;")
            row_layout.addWidget(url_label)

            row_layout.addStretch()

            toggle = QCheckBox("Enabled")
            toggle.setChecked(bool(site["is_enabled"]))
            site_id = site["id"]
            toggle.stateChanged.connect(
                lambda state, sid=site_id: self._toggle_site(sid, state > 0)
            )
            row_layout.addWidget(toggle)
            self._site_toggles.append((site_id, toggle))

            self.sites_container.addWidget(row)

    def _toggle_site(self, site_id: int, enabled: bool) -> None:
        self.db.toggle_site(site_id, enabled)
        self.settings_changed.emit()

    # ------------------------------------------------------------------ #
    #  Catalogs                                                            #
    # ------------------------------------------------------------------ #
    def _create_catalog(self) -> None:
        name = self.catalog_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a catalog name")
            return

        try:
            self.db.create_catalog(name, "")
            self.catalog_name_input.clear()
            self._refresh_catalogs()
            QMessageBox.information(self, "Success", f"Catalog '{name}' created!")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to create catalog: {e}")

    def _refresh_catalogs(self) -> None:
        while self.catalogs_list.count():
            item = self.catalogs_list.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        catalogs = self.db.get_catalogs()
        for cat in catalogs:
            cat_widget = QWidget()
            cat_layout = QHBoxLayout(cat_widget)
            cat_layout.setContentsMargins(0, 0, 0, 0)

            name_label = QLabel(f"📁 {cat['name']}")
            name_label.setStyleSheet("color: #e0e0e0;")
            cat_layout.addWidget(name_label)

            cat_layout.addStretch()

            delete_btn = QPushButton("Delete")
            delete_btn.setStyleSheet(
                "background: #c0392b; color: white; padding: 4px 8px; "
                "border-radius: 4px;"
            )
            catalog_id = cat["id"]
            catalog_name = cat["name"]
            delete_btn.clicked.connect(
                lambda checked=False,
                cid=catalog_id,
                cname=catalog_name: self._delete_catalog(cid, cname)
            )
            cat_layout.addWidget(delete_btn)

            self.catalogs_list.addWidget(cat_widget)

    def _delete_catalog(self, catalog_id: int, catalog_name: str) -> None:
        reply = QMessageBox.question(
            self,
            "Delete Catalog",
            f"Delete catalog '{catalog_name}'? Items will be moved to uncategorized.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_catalog(catalog_id)
            self._refresh_catalogs()
