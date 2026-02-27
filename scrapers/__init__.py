"""Modular scraper engine for aggregating media content."""

from scrapers.base import BaseScraper
from scrapers.gogoanime import GogoAnimeScraper
from scrapers.yts import YTSScraper
from scrapers.dramacool import DramacoolScraper
from scrapers.vidsrc_anime import VidSrcAnimeScraper
from scrapers.movie_scraper import MovieScraper
from scrapers.drama_scraper import DramaScraper

__all__ = [
    "BaseScraper", 
    "GogoAnimeScraper", 
    "YTSScraper", 
    "DramacoolScraper", 
    "VidSrcAnimeScraper",
    "MovieScraper",
    "DramaScraper",
]
