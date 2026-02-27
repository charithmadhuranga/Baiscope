"""ClickableCard — a poster widget that shows a cover image and title."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
    QGraphicsDropShadowEffect,
)


class ClickableCard(QFrame):
    """A card widget displaying a media poster image and title.

    Emits ``clicked(detail_url)`` when the user clicks on it.
    """

    clicked = Signal(str)  # detail_url

    CARD_WIDTH = 185
    CARD_HEIGHT = 310
    IMAGE_HEIGHT = 260

    def __init__(
        self,
        title: str,
        cover_url: str,
        detail_url: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.detail_url = detail_url
        self.cover_url = cover_url
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(self.CARD_WIDTH, self.CARD_HEIGHT)
        self.setObjectName("ClickableCard")
        self._build_ui(title)
        self._apply_style()

    # ------------------------------------------------------------------ #
    #  Layout                                                              #
    # ------------------------------------------------------------------ #
    def _build_ui(self, title: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Cover image
        self.image_label = QLabel()
        self.image_label.setFixedSize(self.CARD_WIDTH, self.IMAGE_HEIGHT)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setScaledContents(True)
        self.image_label.setObjectName("CardImage")
        layout.addWidget(self.image_label)

        # Title
        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        self.title_label.setFixedHeight(self.CARD_HEIGHT - self.IMAGE_HEIGHT)
        self.title_label.setObjectName("CardTitle")
        layout.addWidget(self.title_label)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            #ClickableCard {
                background: #1e1e2e;
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.06);
            }
            #ClickableCard:hover {
                border: 1px solid rgba(139, 92, 246, 0.5);
                background: #252540;
            }
            #CardImage {
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                background: #12121a;
            }
            #CardTitle {
                color: #e0e0e0;
                font-size: 12px;
                font-weight: 500;
                padding: 6px 8px;
            }
            """
        )
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 4)
        shadow.setColor(Qt.GlobalColor.black)
        self.setGraphicsEffect(shadow)

    # ------------------------------------------------------------------ #
    #  Public helpers                                                      #
    # ------------------------------------------------------------------ #
    def set_pixmap(self, pixmap: QPixmap) -> None:
        """Set the cover image pixmap."""
        self.image_label.setPixmap(
            pixmap.scaled(
                self.CARD_WIDTH,
                self.IMAGE_HEIGHT,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    # ------------------------------------------------------------------ #
    #  Events                                                              #
    # ------------------------------------------------------------------ #
    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.detail_url)
        super().mousePressEvent(event)
