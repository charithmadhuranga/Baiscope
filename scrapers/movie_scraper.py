"""Movie scraper using multiple working sources."""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, ScraperError


class MovieScraper(BaseScraper):
    """Scraper for movies using multiple streaming sources."""

    BASE_URL = "https://vidsrc.cc"
    NAME = "Movies"
    CATEGORY = "movie"

    STREAM_DOMAINS = [
        "vidsrc.cc",
        "vidsrc.me", 
        "multiembed.mov",
    ]

    def search(self, query: str, page: int = 1) -> list[dict[str, str]]:
        """Search for movies using TMDB-like API or HTML scraping."""
        
        # Try using a movie database site
        search_urls = [
            f"https://www.imdb.com/find?q={query}&s=tt",
        ]
        
        results = []
        
        # Use a simple search approach - scrape from YTS (still works for search)
        try:
            yts_url = f"https://www.yts-official.top/browse-movies?keyword={query}&page={page}"
            resp = self._get(yts_url)
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
                        })
        except Exception:
            pass
        
        return results

    def get_detail(self, detail_url: str) -> dict[str, Any]:
        """Get movie detail and generate streaming URLs."""
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
            # Try to extract from URL
            match = re.search(r'/movie/([a-z0-9-]+)', detail_url)
            if match:
                imdb_code = match.group(1)

        episodes = []
        
        # Generate streaming URLs for each domain
        if imdb_code:
            # Ensure imdb_code starts with tt
            if not imdb_code.startswith("tt"):
                imdb_code = "tt" + imdb_code
            
            for domain in self.STREAM_DOMAINS:
                if domain == "multiembed.mov":
                    # Multiembed format
                    episodes.append({
                        "title": f"Watch (multiembed)",
                        "url": f"https://multiembed.mov/?video_id={imdb_code}"
                    })
                else:
                    # vidsrc formats
                    episodes.append({
                        "title": f"Watch ({domain})",
                        "url": f"https://{domain}/v3/embed/movie/{imdb_code}"
                    })
                    episodes.append({
                        "title": f"Watch ({domain} v2)",
                        "url": f"https://{domain}/v2/embed/movie/{imdb_code}"
                    })

        return {
            "title": title,
            "cover_url": cover_url,
            "synopsis": synopsis,
            "episodes": episodes,
        }

    def get_stream_url(self, episode_url: str) -> dict[str, Any] | None:
        """Return the streaming URL with proper headers."""
        
        # Check which domain we're using
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
