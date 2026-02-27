"""Search worker — runs scraper.search() on a background QThread."""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from scrapers.base import BaseScraper, ScraperError


class SearchWorker(QThread):
    """Runs a scraper search query off the main thread.

    Signals
    -------
    results_ready : list[dict]
        Emitted with the search results when the query completes.
    error : str
        Emitted with an error message if the search fails.
    """

    results_ready = Signal(list)
    error = Signal(str)

    def __init__(
        self,
        scraper: BaseScraper,
        query: str,
        page: int = 1,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.scraper = scraper
        self.query = query
        self.page = page

    def run(self) -> None:  # noqa: D401
        """Execute the search in the background."""
        try:
            results = self.scraper.search(self.query, page=self.page)
            self.results_ready.emit(results)
        except ScraperError as exc:
            self.error.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.error.emit(f"Unexpected error: {exc}")
