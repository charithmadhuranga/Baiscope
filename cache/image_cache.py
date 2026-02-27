"""Disk-based image cache using SHA-256 keyed filenames."""

from __future__ import annotations

import hashlib
from pathlib import Path


class ImageCache:
    """Simple disk cache for downloaded images.

    Images are stored under ``~/.baiscope/cache/images/`` with filenames
    derived from the SHA-256 hash of the URL.
    """

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or Path.home() / ".baiscope" / "cache" / "images"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _key(url: str) -> str:
        """Return a filename-safe hash for the given URL."""
        return hashlib.sha256(url.encode()).hexdigest()

    def get(self, url: str) -> Path | None:
        """Return the cached file path if it exists, else ``None``."""
        path = self.cache_dir / self._key(url)
        return path if path.exists() else None

    def put(self, url: str, data: bytes) -> Path:
        """Write image data to cache and return the file path."""
        path = self.cache_dir / self._key(url)
        path.write_bytes(data)
        return path

    def clear(self) -> None:
        """Remove all cached files."""
        for file in self.cache_dir.iterdir():
            if file.is_file():
                file.unlink()
