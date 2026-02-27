"""Image download worker — fetches and caches cover images on a QRunnable."""

from __future__ import annotations

import requests
from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from cache.image_cache import ImageCache


class _ImageSignals(QObject):
    """Signals emitted by ``ImageWorker``."""

    finished = Signal(str, str)  # (url, cached_path)
    error = Signal(str, str)    # (url, error_message)


class ImageWorker(QRunnable):
    """Download a single image and cache it to disk.

    Parameters
    ----------
    url : str
        The image URL to download.
    cache : ImageCache
        The shared image cache instance.
    """

    def __init__(self, url: str, cache: ImageCache, headers: dict | None = None) -> None:
        super().__init__()
        self.url = url
        self.cache = cache
        self.headers = headers or {}
        self.signals = _ImageSignals()
        self.setAutoDelete(True)

    @Slot()
    def run(self) -> None:  # noqa: D401
        """Download, cache, and emit the result."""
        if not self.url:
            self.signals.error.emit(self.url, "Empty URL")
            return

        # Check cache first
        cached = self.cache.get(self.url)
        if cached:
            self.signals.finished.emit(self.url, str(cached))
            return

        try:
            req_headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            }
            req_headers.update(self.headers)
            
            resp = requests.get(self.url, timeout=15, headers=req_headers)
            resp.raise_for_status()
            path = self.cache.put(self.url, resp.content)
            self.signals.finished.emit(self.url, str(path))
        except Exception as exc:  # noqa: BLE001
            self.signals.error.emit(self.url, str(exc))
