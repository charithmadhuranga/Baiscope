"""YTS scraper — searches and extracts movie content via the YTS API."""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, ScraperError

class YTSScraper(BaseScraper):
    """Scraper for YTS (YIFY Torrents) movie site.

    Uses HTML scraping for search and detail pages.
    """

    BASE_URL = "https://www.yts-official.top"
    API_URL = "https://www.yts-official.top/api/v2"
    NAME = "YTS"
    CATEGORY = "movie"

    VIDSRC_DOMAINS = ["vidsrc.me", "vidsrc-embed.ru", "vidsrc-embed.su"]
    VIDSRC_API_DOMAINS = ["api.vidsrc-embed.ru", "api.vidsrc-embed.su"]

    # ------------------------------------------------------------------ #
    #  Search                                                              #
    # ------------------------------------------------------------------ #
    def search(self, query: str, page: int = 1) -> list[dict[str, str]]:
        """Search YTS via HTML and return a list of result dicts."""
        if not query or query.lower() == "popular":
            url = f"{self.BASE_URL}/browse-movies"
            params = {"order_by": "rating", "page": page}
        else:
            url = f"{self.BASE_URL}/browse-movies"
            params = {"keyword": query, "order_by": "latest", "page": page}
        
        try:
            resp = self._get(url, params=params)
            soup = BeautifulSoup(resp.text, "lxml")
            
            results: list[dict[str, str]] = []
            for wrap in soup.select(".browse-movie-wrap"):
                title_tag = wrap.select_one(".browse-movie-title")
                year_tag = wrap.select_one(".browse-movie-year")
                img_tag = wrap.select_one("img")
                
                if title_tag:
                    title = title_tag.text.strip()
                    if year_tag:
                        title += f" ({year_tag.text.strip()})"
                    
                    link = wrap.select_one("a.browse-movie-link")
                    href = link.get("href", "") if link else ""
                    
                    cover_url = img_tag.get("src", "") if img_tag else ""
                    if cover_url and cover_url.startswith("/"):
                        cover_url = self.BASE_URL + cover_url
                    
                    results.append({
                        "title": title,
                        "cover_url": cover_url,
                        "detail_url": self.BASE_URL + href,
                    })
            return results
        except Exception:
            return []

    # ------------------------------------------------------------------ #
    #  Detail                                                              #
    # ------------------------------------------------------------------ #
    def get_detail(self, detail_url: str) -> dict[str, Any]:
        """Get movie detail from the YTS website directly."""
        try:
            resp = self._get(detail_url)
            soup = BeautifulSoup(resp.text, "lxml")
        except ScraperError:
            return {"title": "", "synopsis": "", "episodes": []}

        # Title
        title = ""
        title_tag = soup.select_one("h1[itemprop='name']") or soup.select_one("div.hidden-xs h1")
        if title_tag:
            title = title_tag.text.strip()
            year_tag = soup.select_one("div.hidden-xs h2")
            if year_tag:
                title += f" ({year_tag.text.strip()})"

        # Cover
        img = soup.select_one("img[itemprop='image']")
        cover_url = img.get("src", "") if img else ""
        if cover_url and cover_url.startswith("/"):
            cover_url = self.BASE_URL + cover_url

        # Synopsis
        synopsis = ""
        synopsis_div = soup.select_one("#synopsis")
        if synopsis_div:
            p = synopsis_div.select_one("p.hidden-xs") or synopsis_div.select_one("p")
            if p:
                synopsis = p.text.strip()

        # IMDb code
        imdb_code = ""
        imdb_a = soup.find("a", title="IMDb Rating")
        if imdb_a:
            href = imdb_a.get("href", "")
            if "title/tt" in href:
                imdb_code = "tt" + href.split("title/tt")[1].strip("/")
        
        if not imdb_code:
            import re
            sub = soup.find("a", href=re.compile("movie-imdb/tt"))
            if sub:
                href = sub.get("href", "")
                imdb_code = "tt" + href.split("movie-imdb/tt")[1].strip("/")

        episodes: list[dict[str, str]] = []

        if imdb_code:
            for domain in self.VIDSRC_DOMAINS:
                episodes.append({
                    "title": f"Stream ({domain})",
                    "url": f"https://{domain}/v2/embed/movie/{imdb_code}"
                })

        # Torrents
        # Look for buttons that have 'download-torrent' class
        torrent_links = soup.select("a.download-torrent[href*='/torrent/']")
        seen_urls = set()
        for a in torrent_links:
            url = a.get("href", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                if url.startswith("/"):
                    url = self.BASE_URL + url
                
                # Try to get quality from text or title
                text = a.text.strip() or a.get("title", "").split(" ")[-2] if " " in a.get("title", "") else "Download"
                text = text.replace("Download", "").strip() or "Torrent"
                
                episodes.append({
                    "title": f"Torrent: {text}",
                    "url": url,
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
        """Extract stream from vidsrc or return torrent as-is."""
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
