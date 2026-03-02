"""SolarMovies scraper — movies and TV from solarmoviesz.com."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, quote_plus

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, ScraperError


class SolarMovieScraper(BaseScraper):
    """Scraper for SolarMovies streaming site."""

    BASE_URL = "https://solarmoviesz.com"
    NAME = "SolarMovies"
    CATEGORY = "movie"

    # ------------------------------------------------------------------ #
    #  Search                                                              #
    # ------------------------------------------------------------------ #
    def search(self, query: str, page: int = 1) -> list[dict[str, str]]:
        """Search SolarMovies for movies and TV shows."""
        if not query or query.lower() == "popular":
            url = f"{self.BASE_URL}/movies.html"
        else:
            url = f"{self.BASE_URL}/search.html?keyword={quote_plus(query)}"

        try:
            resp = self._get(url)
        except ScraperError:
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        results: list[dict[str, str]] = []

        # SolarMovies uses film cards
        for item in soup.select(".flw-item, .film_list-wrap .film-poster-wrap, .item"):
            link = item.select_one("a")
            img = item.select_one("img")
            title_el = item.select_one(".film-name a, h3 a, .title a, a")

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
                    img.get("data-src", "")
                    or img.get("src", "")
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
        """Get movie/show detail from SolarMovies."""
        try:
            resp = self._get(detail_url)
        except ScraperError:
            return {"title": "", "synopsis": "", "episodes": []}

        soup = BeautifulSoup(resp.text, "lxml")

        title = ""
        title_tag = soup.select_one("h2.heading-name, h1, .film-title")
        if title_tag:
            title = title_tag.get_text(strip=True)

        cover_url = ""
        img = soup.select_one(".film-poster img, img.film-poster-img")
        if img:
            cover_url = img.get("src", "") or img.get("data-src", "")
            if cover_url and not cover_url.startswith("http"):
                cover_url = urljoin(self.BASE_URL, cover_url)

        synopsis = ""
        desc = soup.select_one(".description, .film-description, .overview")
        if desc:
            synopsis = desc.get_text(strip=True)

        episodes: list[dict[str, str]] = []
        seen = set()

        # Servers / embed sources
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

        for link in soup.select("[data-video], .server-item a, a[data-embed]"):
            data_url = (
                link.get("data-video", "")
                or link.get("data-embed", "")
                or link.get("href", "")
            )
            if data_url and data_url not in seen:
                if data_url.startswith("//"):
                    data_url = "https:" + data_url
                seen.add(data_url)
                server_name = link.get_text(strip=True) or f"Server {len(episodes) + 1}"
                episodes.append({
                    "title": server_name,
                    "url": data_url,
                })

        # Episode list for TV shows
        for ep_link in soup.select(".ep-item a, .episodes-list a"):
            ep_url = ep_link.get("href", "")
            ep_title = ep_link.get_text(strip=True)
            if ep_url and ep_url not in seen:
                seen.add(ep_url)
                episodes.append({
                    "title": ep_title or f"Episode {len(episodes) + 1}",
                    "url": urljoin(self.BASE_URL, ep_url),
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
        """Extract stream URL from SolarMovies."""
        if any(d in episode_url for d in ["embed", "player", "vidcloud", "rabbitstream"]):
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
