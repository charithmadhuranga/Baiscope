"""Detail page — shows media info, synopsis, and episode list."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QThreadPool
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from cache.image_cache import ImageCache
from scrapers.base import BaseScraper
from ui.favorites_page import FavoritesPage
from workers.detail_worker import DetailWorker
from workers.image_worker import ImageWorker


class DetailPage(QWidget):
    """Displays detailed info for a media item and its episode list.

    Signals
    -------
    play_requested : str
        Emitted with the episode URL when the user clicks play.
    back_requested : signal
        Emitted when the user clicks the back button.
    """

    play_requested = Signal(str)
    back_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("DetailPage")
        self._image_cache = ImageCache()
        self._current_scraper: BaseScraper | None = None
        self._detail_worker: DetailWorker | None = None
        self._current_detail_url: str = ""
        self._current_cover_url: str = ""
        self._current_title: str = ""
        self._build_ui()
        self._apply_style()

    # ------------------------------------------------------------------ #
    #  Layout                                                              #
    # ------------------------------------------------------------------ #
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 12)
        root.setSpacing(16)

        # Top bar — back + fav
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        self.back_btn = QPushButton("← Back")
        self.back_btn.setObjectName("BackBtn")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.clicked.connect(self.back_requested.emit)
        top_bar.addWidget(self.back_btn)

        top_bar.addStretch()

        self.fav_btn = QPushButton("☆  Add to Favorites")
        self.fav_btn.setObjectName("FavBtn")
        self.fav_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fav_btn.clicked.connect(self._toggle_favorite)
        top_bar.addWidget(self.fav_btn)

        root.addLayout(top_bar)

        # Top section: cover + info
        top = QHBoxLayout()
        top.setSpacing(20)

        self.cover_label = QLabel()
        self.cover_label.setFixedSize(220, 320)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setScaledContents(True)
        self.cover_label.setObjectName("DetailCover")
        top.addWidget(self.cover_label)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)

        self.title_label = QLabel("")
        self.title_label.setObjectName("DetailTitle")
        self.title_label.setWordWrap(True)
        info_layout.addWidget(self.title_label)

        self.meta_label = QLabel("")
        self.meta_label.setObjectName("DetailMeta")
        info_layout.addWidget(self.meta_label)

        self.synopsis_label = QLabel("")
        self.synopsis_label.setObjectName("DetailSynopsis")
        self.synopsis_label.setWordWrap(True)
        info_layout.addWidget(self.synopsis_label, stretch=1)

        top.addLayout(info_layout, stretch=1)
        root.addLayout(top)

        # Episode list
        ep_header = QLabel("Episodes / Downloads")
        ep_header.setObjectName("EpHeader")
        root.addWidget(ep_header)

        self.episode_list = QListWidget()
        self.episode_list.setObjectName("EpisodeList")
        self.episode_list.itemDoubleClicked.connect(self._on_episode_click)
        root.addWidget(self.episode_list, stretch=1)

        # Status
        self.status_label = QLabel("")
        self.status_label.setObjectName("StatusLabel")
        root.addWidget(self.status_label)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            #DetailPage { background: transparent; }
            #BackBtn {
                background: rgba(139,92,246,0.15);
                border: 1px solid rgba(139,92,246,0.3);
                border-radius: 8px;
                color: #b794f6;
                padding: 6px 16px;
                font-size: 13px;
                font-weight: 600;
            }
            #BackBtn:hover { background: rgba(139,92,246,0.25); }
            #FavBtn {
                background: rgba(250,204,21,0.10);
                border: 1px solid rgba(250,204,21,0.3);
                border-radius: 8px;
                color: #facc15;
                padding: 6px 16px;
                font-size: 13px;
                font-weight: 600;
            }
            #FavBtn:hover { background: rgba(250,204,21,0.20); }
            #DetailCover {
                background: #12121a;
                border-radius: 12px;
                border: 1px solid rgba(255,255,255,0.06);
            }
            #DetailTitle {
                color: #ffffff;
                font-size: 24px;
                font-weight: 700;
            }
            #DetailMeta {
                color: #aaa;
                font-size: 13px;
            }
            #DetailSynopsis {
                color: #ccc;
                font-size: 13px;
                line-height: 1.6;
            }
            #EpHeader {
                color: #e0e0e0;
                font-size: 16px;
                font-weight: 600;
            }
            #EpisodeList {
                background: #1a1a2e;
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 10px;
                color: #e0e0e0;
                font-size: 13px;
                padding: 4px;
            }
            #EpisodeList::item {
                padding: 10px 12px;
                border-radius: 6px;
            }
            #EpisodeList::item:hover {
                background: rgba(139,92,246,0.15);
            }
            #EpisodeList::item:selected {
                background: rgba(139,92,246,0.3);
            }
            #StatusLabel {
                color: #888;
                font-size: 13px;
            }
            """
        )

    # ------------------------------------------------------------------ #
    #  Public — load a media item                                          #
    # ------------------------------------------------------------------ #
    def load(self, scraper: BaseScraper, detail_url: str) -> None:
        """Fetch details for the given URL using the specified scraper."""
        self._current_scraper = scraper
        self._current_detail_url = detail_url
        self._current_cover_url = ""
        self._current_title = ""
        self.title_label.setText("Loading…")
        self.synopsis_label.setText("")
        self.meta_label.setText("")
        self.episode_list.clear()
        self.cover_label.clear()
        self.status_label.setText("")
        self._update_fav_button()

        self._detail_worker = DetailWorker(scraper, detail_url, parent=self)
        self._detail_worker.detail_ready.connect(self._on_detail)
        self._detail_worker.error.connect(self._on_error)
        self._detail_worker.start()

    def _on_detail(self, detail: dict) -> None:
        self._current_title = detail.get("title", "Unknown")
        self._current_cover_url = detail.get("cover_url", "")
        self.title_label.setText(self._current_title)
        self.synopsis_label.setText(detail.get("synopsis", ""))

        meta_parts = []
        if detail.get("year"):
            meta_parts.append(str(detail["year"]))
        if detail.get("rating"):
            meta_parts.append(f"⭐ {detail['rating']}")
        if detail.get("genres"):
            meta_parts.append(", ".join(detail["genres"]))
        self.meta_label.setText("  •  ".join(meta_parts))

        # Cover image
        if self._current_cover_url:
            self._load_cover(self._current_cover_url)

        # Episodes
        for ep in detail.get("episodes", []):
            item = QListWidgetItem(ep.get("title", "Episode"))
            item.setData(Qt.ItemDataRole.UserRole, ep.get("url", ""))
            self.episode_list.addItem(item)

        ep_count = len(detail.get("episodes", []))
        self.status_label.setText(
            f"{ep_count} episode(s) — double-click to play"
            if ep_count
            else "No episodes found."
        )
        self._update_fav_button()

    def _on_error(self, msg: str) -> None:
        self.title_label.setText("Error")
        self.status_label.setText(f"⚠ {msg}")

    def _load_cover(self, url: str) -> None:
        worker = ImageWorker(url, self._image_cache)
        worker.signals.finished.connect(self._on_cover_loaded)
        QThreadPool.globalInstance().start(worker)

    def _on_cover_loaded(self, _url: str, path: str) -> None:
        px = QPixmap(path)
        if not px.isNull():
            self.cover_label.setPixmap(
                px.scaled(
                    220,
                    320,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

    def _on_episode_click(self, item: QListWidgetItem) -> None:
        url = item.data(Qt.ItemDataRole.UserRole)
        if url:
            self.play_requested.emit(url)

    # ------------------------------------------------------------------ #
    #  Favorites                                                           #
    # ------------------------------------------------------------------ #
    def _is_favorited(self) -> bool:
        items = FavoritesPage._load_favorites()
        return any(
            f.get("detail_url") == self._current_detail_url for f in items
        )

    def _update_fav_button(self) -> None:
        if self._is_favorited():
            self.fav_btn.setText("★  Remove from Favorites")
            self.fav_btn.setStyleSheet(
                """
                #FavBtn {
                    background: rgba(250,204,21,0.25);
                    border: 1px solid rgba(250,204,21,0.5);
                    border-radius: 8px;
                    color: #facc15;
                    padding: 6px 16px;
                    font-size: 13px;
                    font-weight: 600;
                }
                #FavBtn:hover { background: rgba(250,204,21,0.35); }
                """
            )
        else:
            self.fav_btn.setText("☆  Add to Favorites")
            self.fav_btn.setStyleSheet(
                """
                #FavBtn {
                    background: rgba(250,204,21,0.10);
                    border: 1px solid rgba(250,204,21,0.3);
                    border-radius: 8px;
                    color: #facc15;
                    padding: 6px 16px;
                    font-size: 13px;
                    font-weight: 600;
                }
                #FavBtn:hover { background: rgba(250,204,21,0.20); }
                """
            )

    def _toggle_favorite(self) -> None:
        if self._is_favorited():
            FavoritesPage.remove_favorite(self._current_detail_url)
        else:
            FavoritesPage.add_favorite(
                {
                    "title": self._current_title,
                    "cover_url": self._current_cover_url,
                    "detail_url": self._current_detail_url,
                }
            )
        self._update_fav_button()
