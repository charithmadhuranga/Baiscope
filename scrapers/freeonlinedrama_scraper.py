"""FreeOnlineDrama scraper — dramas from moviestv.my (backing freeonlineda.top)."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, quote_plus

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, ScraperError


class FreeOnlineDramaScraper(BaseScraper):
    """Scraper for FreeOnlineDrama / moviestv.my drama site.

    freeonlineda.top is an iframe wrapper around moviestv.my which
    is the actual data source.
    """

    BASE_URL = "https://moviestv.my"
    NAME = "FreeOnlineDrama"
    CATEGORY = "drama"

    # ------------------------------------------------------------------ #
    #  Search                                                              #
    # ------------------------------------------------------------------ #
    def search(self, query: str, page: int = 1) -> list[dict[str, str]]:
        """Search for dramas on moviestv.my."""
        if not query or query.lower() == "popular":
            url = f"{self.BASE_URL}"
        else:
            url = f"{self.BASE_URL}/search?q={quote_plus(query)}"

        try:
            resp = self._get(url)
        except ScraperError:
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        results: list[dict[str, str]] = []

        # Try various movie/drama card selectors
        for item in soup.select(".movie-card, .film-item, .item, .post, article"):
            link = item.select_one("a[href]")
            img = item.select_one("img")
            title_el = item.select_one("h2, h3, .title, .name, a")

            if not link:
                continue

            href = link.get("href", "")
            if not href:
                continue

            title = ""
            if title_el:
                title = title_el.get_text(strip=True)
            elif link.get("title"):
                title = link.get("title", "")

            if not title:
                continue

            cover_url = ""
            if img:
                cover_url = (
                    img.get("src", "")
                    or img.get("data-src", "")
                    or img.get("data-lazy-src", "")
                )
                if cover_url and not cover_url.startswith("http"):
                    cover_url = urljoin(self.BASE_URL, cover_url)

            detail_url = urljoin(self.BASE_URL, href)

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
        """Get drama detail from moviestv.my."""
        try:
            resp = self._get(detail_url)
        except ScraperError:
            return {"title": "", "synopsis": "", "episodes": []}

        soup = BeautifulSoup(resp.text, "lxml")

        title = ""
        title_tag = soup.select_one("h1, h2.title, .movie-title")
        if title_tag:
            title = title_tag.get_text(strip=True)

        cover_url = ""
        img = soup.select_one("img.poster, .movie-poster img, img[itemprop='image']")
        if img:
            cover_url = img.get("src", "") or img.get("data-src", "")
            if cover_url and not cover_url.startswith("http"):
                cover_url = urljoin(self.BASE_URL, cover_url)

        synopsis = ""
        desc = soup.select_one(".description, .synopsis, .overview, [itemprop='description']")
        if desc:
            synopsis = desc.get_text(strip=True)

        episodes: list[dict[str, str]] = []
        seen = set()

        # Look for episode links
        for ep in soup.select("a[href*='episode'], .episode-item a, .ep-list a"):
            ep_url = ep.get("href", "")
            ep_title = ep.get_text(strip=True)
            if ep_url and ep_url not in seen:
                seen.add(ep_url)
                episodes.append({
                    "title": ep_title or f"Episode {len(episodes) + 1}",
                    "url": urljoin(self.BASE_URL, ep_url),
                })

        # Look for embed iframes
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

        if not episodes:
            episodes.append({"title": "Watch", "url": detail_url})

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
        """Extract stream URL from episode page."""
        if any(d in episode_url for d in ["embed", "player", "vidcloud"]):
            return {
                "url": episode_url,
                "headers": {"Referer": self.BASE_URL},
                "type": "embed",
            }

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
