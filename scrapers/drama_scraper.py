"""Drama scraper for Asian dramas using multiple streaming sources."""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, ScraperError


class DramaScraper(BaseScraper):
    """Scraper for TV shows/series using streaming sources."""

    BASE_URL = "https://www.imdb.com"
    NAME = "Dramas"
    CATEGORY = "drama"

    STREAM_SOURCES = [
        ("VidBinge", "https://www.vidbinge.to/embed/tv/"),
        ("StreamSrc", "https://streamsrc.cc/embed/series/"),
        ("SuperEmbed", "https://www.superembed.stream/embed/series/"),
        ("2Embed", "https://www.2embed.online/embed/tv/"),
        ("VikingEmbed", "https://vembed.stream/embed/tv/"),
        ("Cinemull", "https://cinemull.cc/embed/tv/"),
        ("AutoEmbed", "https://player.autoembed.cc/embed/tv/"),
    ]

    def search(self, query: str, page: int = 1) -> list[dict[str, str]]:
        """Search for TV shows using IMDB suggestion API."""

        results = []

        try:
            url = f"https://v2.sg.media-imdb.com/suggestion/{query[0].lower()}/{query.replace(' ', '%20')}.json"
            resp = self._get(url)
            data = resp.json()

            for item in data.get("d", [])[:15]:
                imdb_id = item.get("id", "")
                if not imdb_id.startswith("tt"):
                    continue

                qid = item.get("qid", "")
                if qid != "tvSeries" and qid != "tvMiniSeries":
                    continue

                title = item.get("l", "")
                cover = item.get("i", {}).get("imageUrl", "")

                if title and imdb_id:
                    results.append(
                        {
                            "title": title,
                            "cover_url": cover,
                            "detail_url": f"series/{imdb_id}",
                            "imdb_code": imdb_id,
                        }
                    )
        except Exception:
            pass

        return results

    def get_detail(self, detail_url: str) -> dict[str, Any]:
        """Get series detail and generate streaming URLs."""

        imdb_code = detail_url.replace("series/", "")
        if not imdb_code.startswith("tt"):
            imdb_code = "tt" + imdb_code

        title = ""
        cover_url = ""

        try:
            details_url = f"https://v2.sg.media-imdb.com/suggestion/{imdb_code[0].lower()}/{imdb_code}.json"
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
            title = f"Series {imdb_code}"

        episodes = []

        for name, base_url in self.STREAM_SOURCES:
            embed_url = f"{base_url}{imdb_code}"
            episodes.append(
                {
                    "title": f"Watch ({name})",
                    "url": embed_url,
                }
            )

        return {
            "title": title,
            "cover_url": cover_url,
            "synopsis": "",
            "episodes": episodes,
            "imdb_code": imdb_code,
        }

    def get_stream_url(self, episode_url: str) -> dict[str, Any] | None:
        """Return the streaming URL with proper headers."""

        for name, base_url in self.STREAM_SOURCES:
            if base_url.replace("https://", "").replace("www.", "").replace(
                "embed/", ""
            ).replace("series/", "") in episode_url.replace("https://", "").replace(
                "www.", ""
            ).replace("embed/", "").replace("series/", ""):
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
