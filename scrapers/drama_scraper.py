"""Drama scraper for Asian dramas using multiple sources."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, ScraperError


class DramaScraper(BaseScraper):
    """Scraper for Asian dramas using vidsrc API."""

    BASE_URL = "https://dramacool.bg"
    NAME = "Dramas"
    CATEGORY = "drama"

    STREAM_DOMAINS = [
        "vidsrc.cc",
        "vidsrc.me",
    ]

    def search(self, query: str, page: int = 1) -> list[dict[str, str]]:
        """Search for dramas using YTS-like approach with drama content."""
        
        results = []
        
        # Try using YTS with drama filter or just search movies
        try:
            # Search on YTS for movies (same as movie scraper but filtered)
            search_url = f"https://www.yts-official.top/browse-movies?keyword={query.replace(' ', '+')}&page={page}"
            resp = self._get(search_url)
            soup = BeautifulSoup(resp.text, "lxml")
            
            for wrap in soup.select(".browse-movie-wrap")[:20]:
                title_tag = wrap.select_one(".browse-movie-title")
                img_tag = wrap.select_one("img")
                link = wrap.select_one("a.browse-movie-link")
                
                if title_tag:
                    title = title_tag.text.strip()
                    href = link.get("href", "") if link else ""
                    cover = img_tag.get("src", "") if img_tag else ""
                    
                    # Extract IMDB from detail page link
                    imdb_code = ""
                    if "/movie/" in href:
                        imdb_code = href.split("/movie/")[-1].rstrip("/")
                    
                    if href:
                        results.append({
                            "title": title,
                            "cover_url": f"https://www.yts-official.top{cover}" if cover.startswith("/") else cover,
                            "detail_url": f"https://www.yts-official.top{href}" if href.startswith("/") else href,
                            "imdb_code": imdb_code,
                            "is_drama": "drama" in title.lower() or "korean" in title.lower() or "k-drama" in title.lower(),
                        })
        except Exception:
            pass
        
        return results

    def get_detail(self, detail_url: str) -> dict[str, Any]:
        """Get drama detail and generate streaming URLs."""
        try:
            resp = self._get(detail_url)
        except ScraperError:
            return {"title": "", "synopsis": "", "episodes": []}

        soup = BeautifulSoup(resp.text, "lxml")

        # Get title
        title = ""
        title_tag = soup.select_one("h1[itemprop='name']") or soup.select_one("div.hidden-xs h1")
        if title_tag:
            title = title_tag.text.strip()
            year_tag = soup.select_one("div.hidden-xs h2")
            if year_tag:
                title += f" ({year_tag.text.strip()})"

        # Get cover
        cover_url = ""
        img = soup.select_one("img[itemprop='image']")
        if img:
            cover_url = img.get("src", "")
            if cover_url.startswith("/"):
                cover_url = "https://www.yts-official.top" + cover_url

        # Get synopsis
        synopsis = ""
        syn_div = soup.select_one("#synopsis")
        if syn_div:
            p = syn_div.select_one("p")
            if p:
                synopsis = p.text.strip()

        # Get IMDB code
        imdb_code = ""
        for link in soup.select("a[href*='imdb.com/title/tt']"):
            href = link.get("href", "")
            if "title/tt" in href:
                imdb_code = href.split("title/")[-1].strip("/")
                break
        
        if not imdb_code:
            match = re.search(r'/movie/([a-z0-9-]+)', detail_url)
            if match:
                imdb_code = match.group(1)

        episodes = []
        
        # Generate streaming URLs for dramas
        if imdb_code:
            if not imdb_code.startswith("tt"):
                imdb_code = "tt" + imdb_code
            
            # Add streaming options for Season 1 (most dramas)
            for domain in self.STREAM_DOMAINS:
                for season in range(1, 3):  # Try first 2 seasons
                    episodes.append({
                        "title": f"Watch Season {season} ({domain})",
                        "url": f"https://{domain}/v3/embed/tv/{imdb_code}/{season}",
                    })

        return {
            "title": title,
            "cover_url": cover_url,
            "synopsis": synopsis,
            "episodes": episodes,
        }

    def get_stream_url(self, episode_url: str) -> dict[str, Any] | None:
        """Return the streaming URL with proper headers."""
        
        for domain in self.STREAM_DOMAINS:
            if domain in episode_url:
                return {
                    "url": episode_url,
                    "headers": {"Referer": f"https://{domain}/"}
                }
        
        return {
            "url": episode_url,
            "headers": {"Referer": "https://vidsrc.cc/"}
        }
