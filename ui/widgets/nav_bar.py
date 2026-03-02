"""NavBar — vertical icon-based sidebar navigation."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QPushButton,
    QVBoxLayout,
    QLabel,
    QSpacerItem,
    QSizePolicy,
)


class NavButton(QPushButton):
    """A sidebar navigation button with emoji icon and tooltip."""

    def __init__(self, icon_text: str, tooltip: str, parent=None) -> None:
        super().__init__(icon_text, parent)
        self.setToolTip(tooltip)
        self.setFixedSize(52, 52)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self.setObjectName("NavButton")


class NavBar(QFrame):
    """Vertical sidebar navigation with icon buttons.

    Signals
    -------
    page_changed : int
        Emitted with the page index when a nav button is clicked.
    """

    page_changed = Signal(int)

    NAV_ITEMS = [
        ("🔍", "Search"),
        ("🌐", "Sites"),
        ("⭐", "Favorites"),
        ("📁", "Catalogs"),
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("NavBar")
        self.setFixedWidth(72)
        self.buttons: list[NavButton] = []
        self._build_ui()
        self._apply_style()

        # Select first button by default
        if self.buttons:
            self.buttons[0].setChecked(True)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 16, 10, 16)
        layout.setSpacing(6)

        # App logo / brand
        brand = QLabel("🎥")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand.setStyleSheet("font-size: 28px; padding-bottom: 8px;")
        layout.addWidget(brand)

        # Nav buttons
        for idx, (icon, tooltip) in enumerate(self.NAV_ITEMS):
            btn = NavButton(icon, tooltip)
            btn.clicked.connect(lambda checked, i=idx: self._on_click(i))
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
            self.buttons.append(btn)

        layout.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

        # Settings button at bottom
        self.settings_btn = NavButton("⚙️", "Settings")
        self.settings_btn.setCheckable(False)
        layout.addWidget(self.settings_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            #NavBar {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a2e,
                    stop:1 #16162a
                );
                border-right: 1px solid rgba(255, 255, 255, 0.06);
            }
            #NavButton {
                background: transparent;
                border: none;
                border-radius: 14px;
                font-size: 22px;
                color: #888;
            }
            #NavButton:hover {
                background: rgba(139, 92, 246, 0.15);
            }
            #NavButton:checked {
                background: rgba(139, 92, 246, 0.3);
                border: 1px solid rgba(139, 92, 246, 0.5);
            }
            """
        )

    def _on_click(self, index: int) -> None:
        for i, btn in enumerate(self.buttons):
            btn.setChecked(i == index)
        self.page_changed.emit(index)
