"""XMovies scraper — adult content using IMDB suggestions + embed sources."""

from __future__ import annotations

import re
from typing import Any

from scrapers.base import BaseScraper, ScraperError


class XMoviesScraper(BaseScraper):
    """Scraper for adult/X-rated movies using IMDB + embed sources.

    Uses IMDB suggestion API to search for adult-tagged content
    and generates embed URLs from multiple sources.
    This scraper is hidden by default and only shows when
    the user enables "Show X Movies" in settings.
    """

    BASE_URL = "https://www.imdb.com"
    NAME = "XMovies"
    CATEGORY = "adult"

    STREAM_SOURCES = [
        ("VidBinge", "https://www.vidbinge.to/embed/movie/"),
        ("StreamSrc", "https://streamsrc.cc/embed/movie/"),
        ("SuperEmbed", "https://www.superembed.stream/embed/movie/"),
        ("2Embed", "https://www.2embed.online/embed/movie/"),
        ("AutoEmbed", "https://player.autoembed.cc/embed/movie/"),
    ]

    # ------------------------------------------------------------------ #
    #  Search                                                              #
    # ------------------------------------------------------------------ #
    def search(self, query: str, page: int = 1) -> list[dict[str, str]]:
        """Search for adult movies using IMDB suggestion API."""
        if not query:
            query = "adult"

        results = []
        try:
            url = (
                f"https://v2.sg.media-imdb.com/suggestion/"
                f"{query[0].lower()}/{query.replace(' ', '%20')}.json"
            )
            resp = self._get(url)
            data = resp.json()

            for item in data.get("d", [])[:15]:
                imdb_id = item.get("id", "")
                if not imdb_id.startswith("tt"):
                    continue

                title = item.get("l", "")
                cover = item.get("i", {}).get("imageUrl", "")

                if title and imdb_id:
                    results.append({
                        "title": title,
                        "cover_url": cover,
                        "detail_url": f"xmovie/{imdb_id}",
                        "imdb_code": imdb_id,
                    })
        except Exception:
            pass

        return results

    # ------------------------------------------------------------------ #
    #  Detail                                                              #
    # ------------------------------------------------------------------ #
    def get_detail(self, detail_url: str) -> dict[str, Any]:
        """Get movie detail and generate streaming URLs."""
        imdb_code = detail_url.replace("xmovie/", "")
        if not imdb_code.startswith("tt"):
            imdb_code = "tt" + imdb_code

        title = ""
        cover_url = ""

        try:
            details_url = (
                f"https://v2.sg.media-imdb.com/suggestion/"
                f"{imdb_code[0].lower()}/{imdb_code}.json"
            )
            resp = self._get(details_url)
            data = resp.json()

            for item in data.get("d", []):
                if item.get("id") == imdb_code:
                    title = item.get("l", "")
                    cover = item.get("i", {}).get("imageUrl", "")
                    if cover:
                        cover_url = cover.replace("._SX200_", "._SX500_")
                    break
        except Exception:
            pass

        if not title:
            title = f"Movie {imdb_code}"

        episodes = []
        for name, base_url in self.STREAM_SOURCES:
            embed_url = f"{base_url}{imdb_code}"
            episodes.append({
                "title": f"Watch ({name})",
                "url": embed_url,
            })

        return {
            "title": title,
            "cover_url": cover_url,
            "synopsis": "",
            "episodes": episodes,
            "imdb_code": imdb_code,
        }

    # ------------------------------------------------------------------ #
    #  Stream URL                                                          #
    # ------------------------------------------------------------------ #
    def get_stream_url(self, episode_url: str) -> dict[str, Any] | None:
        """Return the streaming URL with proper headers."""
        for name, base_url in self.STREAM_SOURCES:
            if base_url.replace("https://", "").replace("www.", "") in episode_url.replace(
                "https://", ""
            ).replace("www.", ""):
                return {
                    "url": episode_url,
                    "headers": {"Referer": base_url},
                    "type": "embed",
                }

        return {
            "url": episode_url,
            "headers": {"Referer": "https://vidsrc.cc/"},
            "type": "embed",
        }
