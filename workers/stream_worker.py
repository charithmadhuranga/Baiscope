"""Stream URL worker — extracts playable stream URL on a background QThread."""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from scrapers.base import BaseScraper, ScraperError


class StreamWorker(QThread):
    """Extracts a stream URL off the main thread.

    Signals
    -------
    stream_ready : str
        Emitted with the playable URL when extraction completes.
    error : str
        Emitted with an error message on failure.
    """

    stream_ready = Signal(object)  # dict metadata or str URL
    error = Signal(str)

    def __init__(
        self,
        scraper: BaseScraper,
        episode_url: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.scraper = scraper
        self.episode_url = episode_url

    def run(self) -> None:  # noqa: D401
        """Execute the stream URL extraction in the background."""
        try:
            # Result is now a dict: {"url": str, "headers": dict}
            result = self.scraper.get_stream_url(self.episode_url)
            if result:
                self.stream_ready.emit(result)
            else:
                self.error.emit("Could not extract a playable stream URL.")
        except ScraperError as exc:
            self.error.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.error.emit(f"Unexpected error: {exc}")
