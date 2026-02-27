"""Detail worker — fetches detail info on a background QThread."""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from scrapers.base import BaseScraper, ScraperError


class DetailWorker(QThread):
    """Fetches media detail info off the main thread.

    Signals
    -------
    detail_ready : dict
        Emitted with the detail dict when the fetch completes.
    error : str
        Emitted with an error message on failure.
    """

    detail_ready = Signal(dict)
    error = Signal(str)

    def __init__(
        self,
        scraper: BaseScraper,
        detail_url: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.scraper = scraper
        self.detail_url = detail_url

    def run(self) -> None:  # noqa: D401
        """Execute the detail fetch in the background."""
        try:
            detail = self.scraper.get_detail(self.detail_url)
            self.detail_ready.emit(detail)
        except ScraperError as exc:
            self.error.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.error.emit(f"Unexpected error: {exc}")
