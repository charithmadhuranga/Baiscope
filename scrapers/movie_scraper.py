"""Movie scraper using multiple working streaming sources."""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, ScraperError


class MovieScraper(BaseScraper):
    """Scraper for movies using multiple streaming sources."""

    BASE_URL = "https://www.imdb.com"
    NAME = "Movies"
    CATEGORY = "movie"

    STREAM_SOURCES = [
        ("VidBinge", "https://www.vidbinge.to/embed/movie/"),
        ("StreamSrc", "https://streamsrc.cc/embed/movie/"),
        ("SuperEmbed", "https://www.superembed.stream/embed/movie/"),
        ("2Embed", "https://www.2embed.online/embed/movie/"),
        ("VikingEmbed", "https://vembed.stream/embed/movie/"),
        ("Cinemull", "https://cinemull.cc/embed/movie/"),
        ("AutoEmbed", "https://player.autoembed.cc/embed/movie/"),
    ]

    def search(self, query: str, page: int = 1) -> list[dict[str, str]]:
        """Search for movies using TMDB-like API or HTML scraping."""

        results = []

        search_urls = [
            f"https://v2.sg.media-imdb.com/suggestion/{query[0].lower()}/{query.replace(' ', '%20')}.json",
        ]

        for url in search_urls:
            try:
                resp = self._get(url)
                data = resp.json()

                for item in data.get("d", [])[:15]:
                    imdb_id = item.get("id", "")
                    if not imdb_id.startswith("tt"):
                        continue

                    title = item.get("l", "")
                    cover = item.get("i", {}).get("imageUrl", "")

                    if title and imdb_id:
                        results.append(
                            {
                                "title": title,
                                "cover_url": cover,
                                "detail_url": f"movie/{imdb_id}",
                                "imdb_code": imdb_id,
                            }
                        )
                break
            except Exception:
                continue

        return results

    def get_detail(self, detail_url: str) -> dict[str, Any]:
        """Get movie detail and generate streaming URLs."""

        imdb_code = detail_url.replace("movie/", "")
        if not imdb_code.startswith("tt"):
            imdb_code = "tt" + imdb_code

        title = ""
        cover_url = ""
        synopsis = ""

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
            title = f"Movie {imdb_code}"

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
            "synopsis": synopsis,
            "episodes": episodes,
            "imdb_code": imdb_code,
        }

    def get_stream_url(self, episode_url: str) -> dict[str, Any] | None:
        """Return the streaming URL with proper headers."""

        for name, base_url in self.STREAM_SOURCES:
            if base_url.replace("https://", "").replace(
                "www.", ""
            ) in episode_url.replace("https://", "").replace("www.", ""):
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
