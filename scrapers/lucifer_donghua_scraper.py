"""LuciferDonghua scraper — Chinese/Donghua anime from luciferdonghua.in."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, quote_plus

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, ScraperError


class LuciferDonghuaScraper(BaseScraper):
    """Scraper for LuciferDonghua donghua/anime streaming site.

    A WordPress-based site for Chinese animation (donghua).
    """

    BASE_URL = "https://luciferdonghua.in"
    NAME = "LuciferDonghua"
    CATEGORY = "anime"

    # ------------------------------------------------------------------ #
    #  Search                                                              #
    # ------------------------------------------------------------------ #
    def search(self, query: str, page: int = 1) -> list[dict[str, str]]:
        """Search LuciferDonghua for donghua/anime."""
        if not query or query.lower() == "popular":
            url = self.BASE_URL
        else:
            url = f"{self.BASE_URL}/page/{page}/"
            url = f"{self.BASE_URL}/?s={quote_plus(query)}"
            if page > 1:
                url = f"{self.BASE_URL}/page/{page}/?s={quote_plus(query)}"

        try:
            resp = self._get(url)
        except ScraperError:
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        results: list[dict[str, str]] = []

        # Parse article/item cards (WordPress theme)
        for item in soup.select(
            "article, .flw-item, .film_list-wrap .item, "
            ".listupd .bs, .bsx, .post-item, div.page-item-detail"
        ):
            link = item.select_one("a[href]")
            img = item.select_one("img")
            title_el = item.select_one(
                "h2 a, h3 a, .film-name a, .tt a, .entry-title a, a"
            )

            if not link:
                continue

            href = link.get("href", "")
            if not href or "luciferdonghua" not in href:
                continue

            title = ""
            if title_el and title_el != link:
                title = title_el.get_text(strip=True)
            elif link.get("title"):
                title = link.get("title", "")
            elif link.get_text(strip=True):
                title = link.get_text(strip=True)[:100]

            if not title or len(title) < 3:
                continue

            # Skip episode links, we want series/movie pages
            if re.search(r'episode-\d+', href.lower()):
                # Extract series URL by removing episode portion
                series_match = re.match(r'(https?://[^/]+/[^/]+/).*episode', href)
                if series_match:
                    href = series_match.group(1)

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
        """Get donghua detail page info."""
        try:
            resp = self._get(detail_url)
        except ScraperError:
            return {"title": "", "synopsis": "", "episodes": []}

        soup = BeautifulSoup(resp.text, "lxml")

        title = ""
        title_tag = soup.select_one("h1, h2.entry-title, .film-title, .anime-title")
        if title_tag:
            title = title_tag.get_text(strip=True)

        cover_url = ""
        img = soup.select_one(
            ".thumb img, .film-poster img, .anime-poster img, "
            "article img, .entry-content img"
        )
        if img:
            cover_url = img.get("src", "") or img.get("data-src", "")
            if cover_url and not cover_url.startswith("http"):
                cover_url = urljoin(self.BASE_URL, cover_url)

        synopsis = ""
        desc = soup.select_one(
            ".entry-content, .description, .synopsis, "
            ".film-description, [itemprop='description']"
        )
        if desc:
            # Get first paragraph
            p = desc.select_one("p")
            if p:
                synopsis = p.get_text(strip=True)
            else:
                synopsis = desc.get_text(strip=True)[:500]

        # Episode list
        episodes: list[dict[str, str]] = []
        seen = set()

        # Look for episode links
        for ep_link in soup.select(
            "a[href*='episode'], .episode-list a, .episodes a, "
            ".eplister a, ul.episodelist a, .episodios a"
        ):
            ep_url = ep_link.get("href", "")
            if not ep_url or ep_url in seen:
                continue
            if "luciferdonghua" not in ep_url:
                continue
            seen.add(ep_url)

            ep_title = ep_link.get_text(strip=True)
            if not ep_title:
                # Try to extract episode number from URL
                ep_match = re.search(r'episode-(\d+)', ep_url)
                ep_title = f"Episode {ep_match.group(1)}" if ep_match else f"Episode {len(episodes) + 1}"

            episodes.append({
                "title": ep_title,
                "url": urljoin(self.BASE_URL, ep_url),
            })

        # If we're on an episode page directly, add the current page
        if not episodes:
            # Check if this is an episode page with an iframe player
            iframe = soup.select_one("iframe[src]")
            if iframe:
                episodes.append({"title": "Watch", "url": detail_url})
            else:
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
        try:
            resp = self._get(episode_url)
        except ScraperError:
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        # Look for iframe embeds
        for iframe in soup.select("iframe[src]"):
            src = iframe.get("src", "")
            if src:
                if src.startswith("//"):
                    src = "https:" + src
                if "ad" not in src.lower() and "banner" not in src.lower():
                    return {
                        "url": src,
                        "headers": {"Referer": self.BASE_URL},
                        "type": "embed",
                    }

        # Look for video sources in script tags
        for script in soup.select("script"):
            text = script.string or ""
            # Look for video URLs in JavaScript
            m3u8_match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', text)
            if m3u8_match:
                return {
                    "url": m3u8_match.group(1),
                    "headers": {"Referer": self.BASE_URL},
                    "type": "direct",
                }
            mp4_match = re.search(r'(https?://[^\s"\']+\.mp4[^\s"\']*)', text)
            if mp4_match:
                return {
                    "url": mp4_match.group(1),
                    "headers": {"Referer": self.BASE_URL},
                    "type": "direct",
                }

        return {
            "url": episode_url,
            "headers": {"Referer": self.BASE_URL},
            "type": "embed",
        }
