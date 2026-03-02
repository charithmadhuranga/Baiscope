"""Movie2K scraper — searches and streams movies from movie2k.quest."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, quote_plus

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, ScraperError


class Movie2KScraper(BaseScraper):
    """Scraper for Movie2K movie streaming site."""

    BASE_URL = "https://movie2k.quest"
    NAME = "Movie2K"
    CATEGORY = "movie"

    # ------------------------------------------------------------------ #
    #  Search                                                              #
    # ------------------------------------------------------------------ #
    def search(self, query: str, page: int = 1) -> list[dict[str, str]]:
        """Search Movie2K for movies."""
        if not query or query.lower() == "popular":
            url = f"{self.BASE_URL}/movie/views"
            if page > 1:
                url += f"/{page}"
        else:
            url = f"{self.BASE_URL}/search/{quote_plus(query)}"
            if page > 1:
                url += f"/{page}"

        try:
            resp = self._get(url)
        except ScraperError:
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        results: list[dict[str, str]] = []

        # Movie2K uses card-based layout with links
        for item in soup.select("a[href*='/movie/'], a[href*='/watch-movie/']"):
            title_el = item.select_one("h2, .title, span")
            img_el = item.select_one("img")

            href = item.get("href", "")
            if not href or "/movie/" not in href and "/watch-movie/" not in href:
                continue

            title = ""
            if title_el:
                title = title_el.get_text(strip=True)
            elif item.get("title"):
                title = item.get("title", "").strip()
            elif item.get_text(strip=True):
                title = item.get_text(strip=True)[:80]

            if not title or len(title) < 2:
                continue

            cover_url = ""
            if img_el:
                cover_url = img_el.get("src", "") or img_el.get("data-src", "")
                if cover_url and not cover_url.startswith("http"):
                    cover_url = urljoin(self.BASE_URL, cover_url)

            detail_url = urljoin(self.BASE_URL, href)

            # Avoid duplicates
            if any(r["detail_url"] == detail_url for r in results):
                continue

            results.append({
                "title": title,
                "cover_url": cover_url,
                "detail_url": detail_url,
            })

        return results

    # ------------------------------------------------------------------ #
    #  Detail                                                              #
    # ------------------------------------------------------------------ #
    def get_detail(self, detail_url: str) -> dict[str, Any]:
        """Get movie detail from Movie2K."""
        try:
            resp = self._get(detail_url)
        except ScraperError:
            return {"title": "", "synopsis": "", "episodes": []}

        soup = BeautifulSoup(resp.text, "lxml")

        # Title
        title = ""
        title_tag = soup.select_one("h1, h2.title, .movie-title")
        if title_tag:
            title = title_tag.get_text(strip=True)

        # Cover
        cover_url = ""
        img = soup.select_one("img.poster, img[itemprop='image'], .movie-poster img")
        if img:
            cover_url = img.get("src", "") or img.get("data-src", "")
            if cover_url and not cover_url.startswith("http"):
                cover_url = urljoin(self.BASE_URL, cover_url)

        # Synopsis
        synopsis = ""
        for sel in [".description", ".synopsis", "p.overview", "[itemprop='description']"]:
            desc_tag = soup.select_one(sel)
            if desc_tag:
                synopsis = desc_tag.get_text(strip=True)
                break

        # Embed URLs / streaming servers
        episodes: list[dict[str, str]] = []
        seen = set()

        # Look for iframes with video embeds
        for iframe in soup.select("iframe[src]"):
            src = iframe.get("src", "")
            if src and src not in seen:
                if src.startswith("//"):
                    src = "https:" + src
                seen.add(src)
                episodes.append({
                    "title": f"Server {len(episodes) + 1}",
                    "url": src,
                })

        # Look for server links
        for link in soup.select("a[data-video], a[data-embed], .server-item a"):
            data_url = link.get("data-video", "") or link.get("data-embed", "") or link.get("href", "")
            if data_url and data_url not in seen:
                if data_url.startswith("//"):
                    data_url = "https:" + data_url
                seen.add(data_url)
                server_name = link.get_text(strip=True) or f"Server {len(episodes) + 1}"
                episodes.append({
                    "title": server_name,
                    "url": data_url,
                })

        # If no servers found, the detail URL itself might be a watch page
        if not episodes:
            episodes.append({
                "title": "Watch",
                "url": detail_url,
            })

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
        """Extract stream URL from Movie2K."""
        # If it's already an embed URL, return it for WebEngine
        if any(d in episode_url for d in ["embed", "player", "vidcloud", "streamtape"]):
            return {
                "url": episode_url,
                "headers": {"Referer": self.BASE_URL},
                "type": "embed",
            }

        # Try to extract embed from the watch page
        try:
            resp = self._get(episode_url)
            soup = BeautifulSoup(resp.text, "lxml")

            iframe = soup.select_one("iframe[src]")
            if iframe:
                src = iframe.get("src", "")
                if src.startswith("//"):
                    src = "https:" + src
                if src:
                    return {
                        "url": src,
                        "headers": {"Referer": self.BASE_URL},
                        "type": "embed",
                    }
        except ScraperError:
            pass

        return {
            "url": episode_url,
            "headers": {"Referer": self.BASE_URL},
            "type": "embed",
        }
