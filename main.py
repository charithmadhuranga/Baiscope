"""Baiscope — Media Streaming Application.

Entry point: launch the PySide6 main window.
"""

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main() -> None:
    """Initialize and run the Baiscope application."""
    # Suppress verbose Chromium logs
    # Disable TrackingProtection3pcd to allow 3rd party cookies for video embeds
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
        "--disable-logging "
        "--disable-features=TrackingProtection3pcd"
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Baiscope")
    app.setOrganizationName("Baiscope")

    # Use a modern default font based on OS to avoid font alias lookup delays
    font = app.font()
    if sys.platform == "darwin":
        font.setFamily(".AppleSystemUIFont")
    elif sys.platform == "win32":
        font.setFamily("Segoe UI")
    else:
        font.setFamily("Ubuntu")
    font.setPointSize(10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
