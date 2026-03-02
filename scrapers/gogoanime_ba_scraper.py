"""GogoAnime .co.ba scraper — anime from ww16.gogoanime.co.ba."""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin, quote_plus

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, ScraperError


class GogoAnimeBaScraper(BaseScraper):
    """Scraper for GogoAnime .co.ba anime streaming site."""

    BASE_URL = "https://ww16.gogoanime.co.ba"
    NAME = "GogoAnime"
    CATEGORY = "anime"

    # ------------------------------------------------------------------ #
    #  Search                                                              #
    # ------------------------------------------------------------------ #
    def search(self, query: str, page: int = 1) -> list[dict[str, str]]:
        """Search gogoanime.co.ba for anime."""
        if not query or query.lower() == "popular":
            url = f"{self.BASE_URL}/anime/"
            params = {"status": "", "type": "", "order": "popular", "page": str(page)}
        else:
            url = f"{self.BASE_URL}/anime/"
            params = {
                "keyword": query,
                "status": "",
                "type": "",
                "order": "default",
                "page": str(page),
            }

        try:
            resp = self._get(url, params=params)
        except ScraperError:
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        results: list[dict[str, str]] = []

        # Parse anime list items
        for item in soup.select(".film_list-wrap .flw-item, .items .item, li.video-block"):
            link = item.select_one("a[href]")
            img = item.select_one("img")
            title_el = item.select_one(".film-name a, h3 a, .name a, a")

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
        """Get anime detail page info (synopsis, episodes)."""
        try:
            resp = self._get(detail_url)
        except ScraperError:
            return {"title": "", "synopsis": "", "episodes": []}

        soup = BeautifulSoup(resp.text, "lxml")

        title = ""
        title_tag = soup.select_one("h1, h2.film-title, .anime-title, .film-name")
        if title_tag:
            title = title_tag.get_text(strip=True)

        cover_url = ""
        img = soup.select_one(
            ".film-poster img, img.film-poster-img, .anime_info_body_bg img, .anime-poster img"
        )
        if img:
            cover_url = img.get("src", "") or img.get("data-src", "")
            if cover_url and not cover_url.startswith("http"):
                cover_url = urljoin(self.BASE_URL, cover_url)

        synopsis = ""
        desc = soup.select_one(".film-description, .description, .synopsis, .overview")
        if desc:
            synopsis = desc.get_text(strip=True)

        # Episode list
        episodes: list[dict[str, str]] = []
        seen = set()

        for ep_link in soup.select(
            ".ep-item a, .episodes-list a, #episode_related li a, "
            "a[href*='episode'], .server-list a"
        ):
            ep_url = ep_link.get("href", "")
            if not ep_url or ep_url in seen:
                continue
            seen.add(ep_url)

            ep_title = ep_link.get_text(strip=True)
            ep_num = ep_link.get("data-num", "")
            if ep_num and not ep_title:
                ep_title = f"Episode {ep_num}"
            elif not ep_title:
                ep_title = f"Episode {len(episodes) + 1}"

            episodes.append({
                "title": ep_title,
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
        """Extract playable video metadata from an episode page."""
        try:
            resp = self._get(episode_url)
        except ScraperError:
            return None

        soup = BeautifulSoup(resp.text, "lxml")
        embed_urls: list[str] = []

        # Try server links
        for li in soup.select("div.anime_muti_link ul li, .server-item"):
            a_tag = li.select_one("a")
            if a_tag:
                data_video = a_tag.get("data-video", "")
                if data_video:
                    if data_video.startswith("//"):
                        data_video = "https:" + data_video
                    embed_urls.append(data_video)

        # Fallback to data-video attributes
        if not embed_urls:
            for tag in soup.select("[data-video]"):
                val = tag.get("data-video", "")
                if val:
                    if val.startswith("//"):
                        val = "https:" + val
                    embed_urls.append(val)

        # Fallback to iframe
        if not embed_urls:
            iframe = soup.select_one("iframe[src]")
            if iframe:
                val = iframe.get("src", "")
                if val:
                    if val.startswith("//"):
                        val = "https:" + val
                    embed_urls.append(val)

        if embed_urls:
            return {
                "url": embed_urls[0],
                "headers": {"Referer": self.BASE_URL},
                "type": "embed",
            }

        return None
