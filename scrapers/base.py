"""Base scraper class defining the interface for all media scrapers."""

from abc import ABC, abstractmethod
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class BaseScraper(ABC):
    """Abstract base class for all media scrapers.

    Provides a shared requests session with retry logic,
    common headers, and the interface every scraper must implement.
    """

    # Subclasses must set these
    BASE_URL: str = ""
    NAME: str = "base"
    CATEGORY: str = "general"  # anime | movie | drama

    def __init__(self, timeout: int = 15) -> None:
        self.timeout = timeout
        self.session = self._build_session()

    # ------------------------------------------------------------------ #
    #  Session factory                                                     #
    # ------------------------------------------------------------------ #
    def _build_session(self) -> requests.Session:
        """Create a requests session with retry + backoff."""
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        return session

    # ------------------------------------------------------------------ #
    #  Convenience HTTP helpers                                            #
    # ------------------------------------------------------------------ #
    def _get(self, url: str, **kwargs: Any) -> requests.Response:
        """GET with built-in timeout and error wrapping."""
        # Automatically add Referer if not present
        if "headers" not in kwargs:
            kwargs["headers"] = {}
        if "Referer" not in kwargs["headers"]:
            kwargs["headers"]["Referer"] = self.BASE_URL

        try:
            resp = self.session.get(url, timeout=self.timeout, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.ConnectionError as exc:
            raise ScraperError(f"[{self.NAME}] No internet or site down: {exc}") from exc
        except requests.HTTPError as exc:
            raise ScraperError(f"[{self.NAME}] HTTP error: {exc}") from exc
        except requests.Timeout as exc:
            raise ScraperError(f"[{self.NAME}] Request timed out: {exc}") from exc

    # ------------------------------------------------------------------ #
    #  Abstract interface                                                  #
    # ------------------------------------------------------------------ #
    @abstractmethod
    def search(self, query: str, page: int = 1) -> list[dict[str, str]]:
        """Search for media and return a list of result dicts.

        Each dict must have:
            - title  (str) : display title
            - cover_url (str) : URL to the cover/poster image
            - detail_url (str) : URL to the detail/episode page
        """

    @abstractmethod
    def get_detail(self, detail_url: str) -> dict[str, Any]:
        """Return detail info (synopsis, episodes, etc.) for a media item."""

    @abstractmethod
    def get_stream_url(self, episode_url: str) -> dict[str, Any] | None:
        """Extract playable video metadata: {"url": str, "headers": dict}."""


class ScraperError(Exception):
    """Raised when a scraper encounters a network or parsing error."""
