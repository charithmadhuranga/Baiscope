"""VidSrc Anime scraper — provides anime streaming via vidsrc API."""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, ScraperError


class VidSrcAnimeScraper(BaseScraper):
    """Scraper for anime using vidsrc.cc API.

    Uses the vidsrc API to search and stream anime content.
    """

    BASE_URL = "https://vidsrc.cc"
    NAME = "VidSrc Anime"
    CATEGORY = "anime"

    VIDSRC_API = "https://vidsrc.cc/api"
    VIDSRC_DOMAINS = ["vidsrc.cc", "vidsrc.me", "vidsrc.in", "vidsrc.pm", "vidsrc.xyz"]

    def search(self, query: str, page: int = 1) -> list[dict[str, str]]:
        """Search vidsrc for anime."""
        if not query or query.lower() == "popular":
            url = f"{self.BASE_URL}/v2/ajax/movie/filter"
            params = {
                "keyword": "anime",
                "page": page,
                "limit": 20,
                "type": "anime"
            }
            try:
                resp = self._get(url, params=params)
                soup = BeautifulSoup(resp.text, "lxml")
                
                results = []
                for item in soup.select("div.flw-item"):
                    title_tag = item.select_one("h3 a") or item.select_one(".film-name a")
                    img_tag = item.select_one("img")
                    
                    if title_tag:
                        title = title_tag.get_text(strip=True)
                        detail_url = title_tag.get("href", "")
                        if detail_url and not detail_url.startswith("http"):
                            detail_url = self.BASE_URL + detail_url
                        
                        cover_url = img_tag.get("data-src", img_tag.get("src", "")) if img_tag else ""
                        
                        results.append({
                            "title": title,
                            "cover_url": cover_url,
                            "detail_url": detail_url,
                        })
                return results
            except Exception:
                pass
            return []

        # Try searching by query
        url = f"{self.BASE_URL}/v2/ajax/movie/filter"
        params = {
            "keyword": query,
            "page": page,
            "limit": 20,
            "type": "anime"
        }
        
        try:
            resp = self._get(url, params=params)
            soup = BeautifulSoup(resp.text, "lxml")
            
            results = []
            for item in soup.select("div.flw-item"):
                title_tag = item.select_one("h3 a") or item.select_one(".film-name a")
                img_tag = item.select_one("img")
                
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    detail_url = title_tag.get("href", "")
                    if detail_url and not detail_url.startswith("http"):
                        detail_url = self.BASE_URL + detail_url
                    
                    cover_url = img_tag.get("data-src", img_tag.get("src", "")) if img_tag else ""
                    
                    results.append({
                        "title": title,
                        "cover_url": cover_url,
                        "detail_url": detail_url,
                    })
            return results
        except Exception:
            return []

    def get_detail(self, detail_url: str) -> dict[str, Any]:
        """Get anime detail from vidsrc."""
        try:
            resp = self._get(detail_url)
        except ScraperError:
            return {"title": "", "synopsis": "", "episodes": []}

        soup = BeautifulSoup(resp.text, "lxml")

        # Title
        title = ""
        title_tag = soup.select_one("h2.film-title") or soup.select_one("h1")
        if title_tag:
            title = title_tag.get_text(strip=True)

        # Cover
        cover_url = ""
        img_tag = soup.select_one("img.film-poster") or soup.select_one("div.film-poster img")
        if img_tag:
            cover_url = img_tag.get("src", img_tag.get("data-src", ""))

        # Synopsis
        synopsis = ""
        desc_tag = soup.select_one("div.film-description") or soup.select_one("div.description")
        if desc_tag:
            synopsis = desc_tag.get_text(strip=True)

        # Extract TMDB or IMDB ID from the URL or page
        imdb_id = ""
        tmdb_id = ""
        
        # From URL like /anime/12345
        match = re.search(r'/anime/(\d+)', detail_url)
        if match:
            tmdb_id = match.group(1)
        
        # From page
        for link in soup.select("a[href*='imdb.com/title/tt']"):
            href = link.get("href", "")
            if "title/tt" in href:
                imdb_id = href.split("title/")[-1].strip("/")
        
        # Look for data attributes
        for tag in soup.select("[data-tmdb-id]"):
            tmdb_id = tag.get("data-tmdb-id", "")
        for tag in soup.select("[data-imdb-id]"):
            imdb_id = tag.get("data-imdb-id", "")

        episodes: list[dict[str, str]] = []
        
        # Get season and episode count from the page
        seasons = soup.select("div.film-share div.post-score p")
        
        if tmdb_id or imdb_id:
            # If we have an ID, try to fetch seasons/episodes
            # For now, add a default episode link
            for domain in self.VIDSRC_DOMAINS:
                if tmdb_id:
                    episodes.append({
                        "title": f"Watch All Episodes ({domain})",
                        "url": f"https://{domain}/v2/embed/anime/{tmdb_id}"
                    })
                elif imdb_id:
                    episodes.append({
                        "title": f"Watch All Episodes ({domain})",
                        "url": f"https://{domain}/v2/embed/anime/{imdb_id}"
                    })

        return {
            "title": title,
            "cover_url": cover_url,
            "synopsis": synopsis,
            "episodes": episodes,
        }

    def get_stream_url(self, episode_url: str) -> dict[str, Any] | None:
        """Extract stream from vidsrc URL."""
        for domain in self.VIDSRC_DOMAINS:
            if domain in episode_url:
                return {
                    "url": episode_url,
                    "headers": {"Referer": f"https://{domain}/"}
                }
        
        if "vidsrc" in episode_url:
            return {
                "url": episode_url,
                "headers": {"Referer": "https://vidsrc.cc/"}
            }
        
        return {"url": episode_url, "headers": {}}
