import re
from typing import Any
from urllib.parse import quote_plus, urljoin, urlparse

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, ScraperError


class DramacoolScraper(BaseScraper):
    """Scraper for Dramacool Asian drama streaming site."""

    BASE_URL = "https://ww16.dramacool.bg"
    NAME = "Dramacool"
    CATEGORY = "drama"

    VIDSRC_DOMAINS = ["vidsrc.cc", "vidsrc.me", "vidsrc.in", "vidsrc.pm", "vidsrc.xyz"]

    # ------------------------------------------------------------------ #
    #  Search                                                              #
    # ------------------------------------------------------------------ #
    def search(self, query: str, page: int = 1) -> list[dict[str, str]]:
        """Search Dramacool and return a list of result dicts."""
        if not query or query.lower() == "popular":
            url = f"{self.BASE_URL}/popular-drama?page={page}"
        else:
            query = query.replace(" ", "+")
            url = f"{self.BASE_URL}/search?keyword={query}&page={page}"
        
        try:
            resp = self._get(url)
        except ScraperError:
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        results: list[dict[str, str]] = []

        for item in soup.select("ul.switch-block.list-episode-item li a"):
            img_tag = item.select_one("img")
            title_tag = item.select_one("h3")

            title = title_tag.get_text(strip=True) if title_tag else ""
            detail_url = urljoin(self.BASE_URL, item.get("href", ""))
            cover_url = img_tag.get("data-original", img_tag.get("src", "")) if img_tag else ""
            if cover_url:
                cover_url = urljoin(self.BASE_URL, cover_url)

            if title:
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
        """Get drama detail page info (synopsis, episodes)."""
        try:
            resp = self._get(detail_url)
        except ScraperError:
            return {"title": "", "synopsis": "", "episodes": []}

        soup = BeautifulSoup(resp.text, "lxml")

        title_tag = soup.select_one("h1")
        title = title_tag.get_text(strip=True) if title_tag else ""

        synopsis = ""
        desc_div = soup.select_one("div.info p") or soup.select_one(
            "div.details div.info"
        )
        if desc_div:
            synopsis = desc_div.get_text(strip=True)

        cover_tag = soup.select_one("div.details img") or soup.select_one(
            "div.img img"
        )
        cover_url = cover_tag.get("src", "") if cover_tag else ""

        # Try to find TMDB ID or IMDB code for vidsrc streaming
        tmdb_id = ""
        imdb_code = ""
        
        # Look for data attributes or links containing TMDB/IMDB
        for link in soup.select("a[href*='themoviedb.org'], a[href*='imdb.com'], a[href*='tvdb']"):
            href = link.get("href", "")
            if "themoviedb.org/tv/" in href:
                tmdb_id = href.split("themoviedb.org/tv/")[-1].strip("/")
            elif "imdb.com/title/tt" in href:
                imdb_code = href.split("title/")[-1].strip("/")
        
        # Look for data-tmdb or data-imdb attributes
        for tag in soup.select("[data-tmdb]"):
            tmdb_id = tag.get("data-tmdb", "")
        for tag in soup.select("[data-imdb]"):
            imdb_code = tag.get("data-imdb", "")
        
        # Extract from JSON-LD or scripts
        page_text = resp.text
        if "tmdb.tv." in page_text:
            match = re.search(r'tmdb\.tv/(\d+)', page_text)
            if match:
                tmdb_id = match.group(1)
        if "imdb.com/title/tt" in page_text:
            match = re.search(r'imdb\.com/title/(tt\d+)', page_text)
            if match:
                imdb_code = match.group(1)

        episodes: list[dict[str, str]] = []
        
        # Add vidsrc streaming options if we found TMDB or IMDB
        if tmdb_id or imdb_code:
            # Find the episode number from the URL to create the correct vidsrc URL
            ep_match = re.search(r'episode-(\d+)', detail_url)
            current_ep = ep_match.group(1) if ep_match else "1"
            
            # Get season number if available
            season_match = re.search(r'season-(\d+)', detail_url)
            season = season_match.group(1) if season_match else "1"
            
            if tmdb_id:
                for domain in self.VIDSRC_DOMAINS:
                    episodes.append({
                        "title": f"Stream ({domain}) S{season}E{current_ep}",
                        "url": f"https://{domain}/v2/embed/tv/{tmdb_id}/{season}/{current_ep}"
                    })
            elif imdb_code:
                for domain in self.VIDSRC_DOMAINS:
                    episodes.append({
                        "title": f"Stream ({domain}) S{season}E{current_ep}",
                        "url": f"https://{domain}/v2/embed/tv/{imdb_code}/{season}/{current_ep}"
                    })

        # Add regular episode links
        for ep_link in soup.select("ul.all-episode li a"):
            ep_title_tag = ep_link.select_one("h3")
            ep_title = ep_title_tag.get_text(strip=True) if ep_title_tag else ""
            ep_url = urljoin(self.BASE_URL, ep_link.get("href", ""))
            if ep_title:
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
        """Extract playable video metadata from an episode page."""
        
        # Handle vidsrc URLs directly
        for domain in self.VIDSRC_DOMAINS:
            if domain in episode_url:
                return {
                    "url": episode_url,
                    "headers": {"Referer": f"https://{domain}/"}
                }
        
        try:
            resp = self._get(episode_url)
        except ScraperError:
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        embed_urls = []
        
        # Try to find server links
        for li in soup.select("div.anime_muti_link ul li") or soup.select("ul.list-server-items li"):
            a_tag = li.select_one("a")
            if a_tag:
                data_video = a_tag.get("data-video", "")
                if data_video:
                    if data_video.startswith("//"):
                        data_video = "https:" + data_video
                    embed_urls.append(data_video)

        # Try to find embedded video source in data-video attributes
        if not embed_urls:
            for tag in soup.select("[data-video]"):
                val = tag.get("data-video", "")
                if val:
                    if val.startswith("//"):
                        val = "https:" + val
                    embed_urls.append(val)

        # Fallback to iframe
        if not embed_urls:
            iframe = soup.select_one("div.watch_video iframe") or soup.select_one("iframe")
            if iframe:
                val = iframe.get("src", "")
                if val:
                    if val.startswith("//"):
                        val = "https:" + val
                    embed_urls.append(val)

        # Try to find and use stream servers
        stream_servers = ["streamsor.com", "dood.watch", "vidplay.site", "streamwish.com", "filemoon.sx", "vidguard.xyz"]
        
        for embed_url in embed_urls:
            # If it's a known streaming server, try to get the actual video URL
            if any(server in embed_url for server in stream_servers):
                try:
                    stream_resp = self._get(embed_url)
                    stream_soup = BeautifulSoup(stream_resp.text, "lxml")
                    
                    # Try to find the video source in the page
                    for video_tag in stream_soup.select("video source"):
                        video_src = video_tag.get("src", "")
                        if video_src:
                            if video_src.startswith("//"):
                                video_src = "https:" + video_src
                            return {
                                "url": video_src,
                                "headers": {"Referer": embed_url}
                            }
                    
                    # Try to find JS player that loads the video
                    for script in stream_soup.select("script"):
                        script_text = script.string or ""
                        # Look for .m3u8 URLs in the script
                        if ".m3u8" in script_text:
                            m3u8_matches = re.findall(r'["\']([^"\']+\.m3u8[^"\']*)["\']', script_text)
                            if m3u8_matches:
                                return {
                                    "url": m3u8_matches[0],
                                    "headers": {"Referer": embed_url}
                                }
                except Exception:
                    pass
            
            # Return embed URL with proper headers
            parsed_embed = urlparse(embed_url)
            embed_host = f"{parsed_embed.scheme}://{parsed_embed.netloc}"
            return {
                "url": embed_url,
                "headers": {
                    "Referer": episode_url,
                    "Origin": embed_host,
                },
            }

        return None
