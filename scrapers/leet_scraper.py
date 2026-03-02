"""1337x torrent scraper — searches torrents from 1337x.to."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, quote_plus

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, ScraperError


class LeetScraper(BaseScraper):
    """Scraper for 1337x torrent site.

    Searches for movie/TV/anime torrents and extracts magnet links
    for streaming via TorrentStreamer.
    """

    BASE_URL = "https://www.1337xx.to"
    NAME = "1337x"
    CATEGORY = "torrent"

    # ------------------------------------------------------------------ #
    #  Search                                                              #
    # ------------------------------------------------------------------ #
    def search(self, query: str, page: int = 1) -> list[dict[str, str]]:
        """Search 1337x for torrents."""
        if not query or query.lower() == "popular":
            url = f"{self.BASE_URL}/popular-movies-week"
        else:
            url = f"{self.BASE_URL}/search/{quote_plus(query)}/{page}/"

        try:
            resp = self._get(url)
        except ScraperError:
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        results: list[dict[str, str]] = []

        # Parse torrent list
        for row in soup.select("table.table-list tbody tr, .table-list-wrap tr"):
            name_cell = row.select_one("td.coll-1 a:nth-of-type(2), td.name a[href*='/torrent/']")
            if not name_cell:
                # Try alternative selector
                name_cell = row.select_one("a[href*='/torrent/']")
            if not name_cell:
                continue

            title = name_cell.get_text(strip=True)
            href = name_cell.get("href", "")
            if not title or not href:
                continue

            detail_url = urljoin(self.BASE_URL, href)

            # Try to get seeders/size info
            seeds_cell = row.select_one("td.coll-2, td:nth-of-type(3)")
            size_cell = row.select_one("td.coll-4, td:nth-of-type(5)")

            seeds = seeds_cell.get_text(strip=True) if seeds_cell else ""
            size = size_cell.get_text(strip=True) if size_cell else ""

            display_title = title
            if size:
                display_title += f" [{size}]"
            if seeds:
                display_title += f" (S:{seeds})"

            results.append({
                "title": display_title,
                "cover_url": "",  # Torrents don't have covers
                "detail_url": detail_url,
            })

        return results

    # ------------------------------------------------------------------ #
    #  Detail                                                              #
    # ------------------------------------------------------------------ #
    def get_detail(self, detail_url: str) -> dict[str, Any]:
        """Get torrent detail page — extract magnet link."""
        try:
            resp = self._get(detail_url)
        except ScraperError:
            return {"title": "", "synopsis": "", "episodes": []}

        soup = BeautifulSoup(resp.text, "lxml")

        # Title
        title = ""
        title_tag = soup.select_one("h1, .box-info-heading h1")
        if title_tag:
            title = title_tag.get_text(strip=True)

        # Synopsis/info
        synopsis = ""
        info_list = soup.select(".torrent-detail-page .list li, .clearfix ul li")
        info_parts = []
        for li in info_list[:8]:
            text = li.get_text(strip=True)
            if text:
                info_parts.append(text)
        synopsis = " | ".join(info_parts)

        # Cover image (some torrents have poster images)
        cover_url = ""
        img = soup.select_one(".torrent-image img, .torrent-poster img")
        if img:
            cover_url = img.get("src", "") or img.get("data-src", "")

        episodes: list[dict[str, str]] = []

        # Extract magnet link
        magnet_link = soup.select_one("a[href^='magnet:']")
        if magnet_link:
            magnet_url = magnet_link.get("href", "")
            if magnet_url:
                episodes.append({
                    "title": "🧲 Stream (Magnet)",
                    "url": magnet_url,
                })

        # Extract .torrent download links
        for a_tag in soup.select("a[href*='.torrent']"):
            torrent_url = a_tag.get("href", "")
            if torrent_url and not torrent_url.startswith("magnet:"):
                if not torrent_url.startswith("http"):
                    torrent_url = urljoin(self.BASE_URL, torrent_url)
                text = a_tag.get_text(strip=True) or "Torrent File"
                episodes.append({
                    "title": f"📥 {text}",
                    "url": torrent_url,
                })

        if not episodes:
            episodes.append({"title": "View Torrent", "url": detail_url})

        return {
            "title": title,
            "cover_url": cover_url,
            "synopsis": synopsis,
            "episodes": episodes,
        }

    # ------------------------------------------------------------------ #
    #  Stream URL                                                          #
    # ------------------------------------------------------------------ #
    def get_stream_url(self, episode_url: str) -> dict[str, Any] | None:
        """Return magnet link or torrent URL for streaming."""
        if episode_url.startswith("magnet:"):
            return {
                "url": episode_url,
                "headers": {},
                "type": "torrent",
            }

        if ".torrent" in episode_url:
            return {
                "url": episode_url,
                "headers": {"Referer": self.BASE_URL},
                "type": "torrent",
            }

        # If it's a detail page, try to extract the magnet
        try:
            resp = self._get(episode_url)
            soup = BeautifulSoup(resp.text, "lxml")

            magnet = soup.select_one("a[href^='magnet:']")
            if magnet:
                return {
                    "url": magnet.get("href", ""),
                    "headers": {},
                    "type": "torrent",
                }
        except ScraperError:
            pass

        return None
