from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, ScraperError


class GogoAnimeScraper(BaseScraper):
    """Scraper for GogoAnime anime streaming site."""

    BASE_URL = "https://anitaku.to"
    NAME = "GogoAnime"
    CATEGORY = "anime"

    ALTERNATIVE_DOMAINS = ["gogoanime.sk", "gogoanime.ee", "gogoanime.io"]

    # ------------------------------------------------------------------ #
    #  Search                                                              #
    # ------------------------------------------------------------------ #
    def search(self, query: str, page: int = 1) -> list[dict[str, str]]:
        """Search gogoanime for anime, or return popular if query is empty."""
        if not query or query.lower() == "popular":
            url = f"{self.BASE_URL}/popular.html?page={page}"
        else:
            url = f"{self.BASE_URL}/search.html?keyword={query}&page={page}"

        try:
            resp = self._get(url)
        except ScraperError:
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        results: list[dict[str, str]] = []

        for item in soup.select("ul.items li"):
            link_tag = item.select_one("p.name a")
            img_tag = item.select_one("div.img a img")
            if not link_tag:
                continue

            title = link_tag.get_text(strip=True)
            detail_url = urljoin(self.BASE_URL, link_tag.get("href", ""))
            cover_url = img_tag.get("src", "") if img_tag else ""
            if cover_url:
                cover_url = urljoin(self.BASE_URL, cover_url)

            results.append(
                {
                    "title": title,
                    "cover_url": cover_url,
                    "detail_url": detail_url,
                }
            )

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

        title_tag = soup.select_one("div.anime_info_body_bg h1")
        title = title_tag.get_text(strip=True) if title_tag else ""

        synopsis = ""
        for p_type in soup.select("p.type"):
            span = p_type.select_one("span")
            if span and "Plot Summary" in span.get_text():
                synopsis = (
                    p_type.get_text(strip=True)
                    .replace(span.get_text(strip=True), "")
                    .strip()
                )
                break

        cover_tag = soup.select_one("div.anime_info_body_bg img")
        cover_url = cover_tag.get("src", "") if cover_tag else ""

        # Episode list
        episodes: list[dict[str, str]] = []
        for ep_link in soup.select("#episode_related li a"):
            ep_num = ep_link.get("data-num", "")
            ep_title = (
                f"Episode {ep_num}"
                if ep_num
                else ep_link.select_one(".name").get_text(strip=True)
            )
            ep_url = urljoin(self.BASE_URL, ep_link.get("href", "").strip())
            episodes.append({"title": ep_title, "url": ep_url})

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
        """Extract playable video metadata from an episode page.

        Returns embed URLs for various streaming servers that work with WebEngine.
        """
        try:
            resp = self._get(episode_url)
        except ScraperError:
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        embed_urls = []

        for li in soup.select("div.anime_muti_link ul li"):
            a_tag = li.select_one("a")
            if a_tag:
                data_video = a_tag.get("data-video", "")
                if data_video:
                    if data_video.startswith("//"):
                        data_video = "https:" + data_video
                    embed_urls.append(data_video)

        if not embed_urls:
            for tag in soup.select("[data-video]"):
                val = tag.get("data-video", "")
                if val:
                    if val.startswith("//"):
                        val = "https:" + val
                    embed_urls.append(val)

        if not embed_urls:
            iframe = soup.select_one("div.play-video iframe")
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
