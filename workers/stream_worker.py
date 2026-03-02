"""Stream URL worker — extracts playable stream URL on a background QThread."""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from scrapers.base import BaseScraper, ScraperError
from scrapers.stream_extractor import StreamExtractor


class StreamWorker(QThread):
    """Extracts a stream URL off the main thread.

    Uses yt-dlp for reliable extraction of direct video URLs from
    streaming sites and embed players.

    Signals
    -------
    stream_ready : dict
        Emitted with the playable URL metadata when extraction completes.
        Dict contains: {"url": str, "headers": dict, "type": str}
    error : str
        Emitted with an error message on failure.
    """

    stream_ready = Signal(object)  # dict metadata
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
        self._extractor = StreamExtractor()

    def run(self) -> None:
        """Execute the stream URL extraction in the background."""
        try:
            # First try the scraper's get_stream_url method
            result = self.scraper.get_stream_url(self.episode_url)

            if result:
                url = result.get("url", "")
                headers = result.get("headers", {})

                if url:
                    # Use StreamExtractor to get a playable URL
                    # This will try to extract direct URL via yt-dlp
                    # or return embed URL for WebEngine playback
                    extracted = self._extractor.extract_stream_url(url)

                    if extracted:
                        # Merge headers from scraper with extracted headers
                        merged_headers = {**headers, **extracted.get("headers", {})}
                        extracted["headers"] = merged_headers
                        self.stream_ready.emit(extracted)
                        return

                    # If no extraction, return original URL for WebEngine
                    self.stream_ready.emit(result)
                    return

            self.error.emit("Could not extract a playable stream URL.")

        except ScraperError as exc:
            self.error.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.error.emit(f"Unexpected error: {exc}")
