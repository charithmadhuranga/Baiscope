"""Stream URL extractor using yt-dlp for reliable video extraction."""

from __future__ import annotations

import re
from typing import Any, Optional

import yt_dlp


class StreamExtractor:
    """Extracts playable video URLs from streaming sites using yt-dlp.

    yt-dlp can extract direct video URLs (m3u8, mp4) from many streaming sites
    including embed players that other methods cannot handle.
    """

    YT_DLP_OPTS = {
        "quiet": True,
        "no_warnings": True,
        "format": "best",
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        },
    }

    EMBED_DOMAINS = [
        "vidsrc.cc",
        "vidsrc.me",
        "vidsrc.to",
        "multiembed.mov",
        "2embed.ru",
        "embed.sflix",
        "streamsor.com",
        "dood.watch",
        "dood.la",
        "vidplay.site",
        "streamwish.com",
        "filemoon.sx",
        "streamtape.com",
        "mixdrop.co",
        "upstream.to",
        "voe.sx",
    ]

    def __init__(self, timeout: int = 60) -> None:
        self.timeout = timeout

    def extract_stream_url(self, url: str) -> Optional[dict[str, Any]]:
        """Extract playable video URL from a streaming page.

        Args:
            url: The streaming page URL (embed page or direct video URL)

        Returns:
            dict with 'url', 'headers', and 'type' ('direct' or 'embed') if successful
            None if extraction failed
        """
        if not url:
            return None

        url = url.strip()
        if url.startswith("//"):
            url = "https:" + url

        if self._is_embed_url(url):
            return self._try_embed_extraction(url)

        return self._extract_direct_url(url)

    def _is_embed_url(self, url: str) -> bool:
        """Check if URL is from a known embed domain."""
        url_lower = url.lower()
        return any(domain in url_lower for domain in self.EMBED_DOMAINS)

    def _extract_direct_url(self, url: str) -> Optional[dict[str, Any]]:
        """Try to extract direct video URL using yt-dlp."""
        opts = dict(self.YT_DLP_OPTS)
        opts["timeout"] = self.timeout

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)

                if info:
                    # Get the best video URL
                    if info.get("url"):
                        return {
                            "url": info["url"],
                            "headers": {
                                "Referer": url,
                                "User-Agent": opts["http_headers"]["User-Agent"],
                            },
                            "type": "direct",
                            "title": info.get("title", ""),
                        }
        except Exception as e:
            print(f"yt-dlp extraction failed: {e}")

        return None

    def _try_embed_extraction(self, url: str) -> Optional[dict[str, Any]]:
        """Try to extract from embed URL, fallback to returning embed URL for WebEngine."""
        # First try yt-dlp on the embed URL
        opts = dict(self.YT_DLP_OPTS)
        opts["timeout"] = self.timeout

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)

                if info and info.get("url"):
                    return {
                        "url": info["url"],
                        "headers": {
                            "Referer": url,
                            "User-Agent": opts["http_headers"]["User-Agent"],
                        },
                        "type": "direct",
                        "title": info.get("title", ""),
                    }
        except Exception as e:
            print(f"yt-dlp embed extraction failed: {e}")

        # Fallback: return embed URL for WebEngine playback
        return {
            "url": url,
            "headers": {"Referer": "https://" + self._extract_domain(url) + "/"},
            "type": "embed",
        }

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        match = re.search(r"https?://([^/]+)", url)
        return match.group(1) if match else ""

    @staticmethod
    def get_best_stream_url(url: str) -> Optional[str]:
        """Convenience function to get just the best stream URL."""
        extractor = StreamExtractor()
        result = extractor.extract_stream_url(url)
        return result["url"] if result else None


def extract_stream(url: str) -> Optional[dict[str, Any]]:
    """Convenience function to extract stream URL."""
    extractor = StreamExtractor()
    return extractor.extract_stream_url(url)
