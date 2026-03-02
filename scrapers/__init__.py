"""Modular scraper engine for aggregating media content."""

from scrapers.base import BaseScraper
from scrapers.gogoanime import GogoAnimeScraper
from scrapers.yts import YTSScraper
from scrapers.dramacool import DramacoolScraper
from scrapers.vidsrc_anime import VidSrcAnimeScraper
from scrapers.movie_scraper import MovieScraper
from scrapers.drama_scraper import DramaScraper
from scrapers.movie2k_scraper import Movie2KScraper
from scrapers.solarmovie_scraper import SolarMovieScraper
from scrapers.freeonlinedrama_scraper import FreeOnlineDramaScraper
from scrapers.gogoanime_ba_scraper import GogoAnimeBaScraper
from scrapers.lucifer_donghua_scraper import LuciferDonghuaScraper
from scrapers.leet_scraper import LeetScraper
from scrapers.xmovies_scraper import XMoviesScraper

__all__ = [
    "BaseScraper",
    "GogoAnimeScraper",
    "YTSScraper",
    "DramacoolScraper",
    "VidSrcAnimeScraper",
    "MovieScraper",
    "DramaScraper",
    "Movie2KScraper",
    "SolarMovieScraper",
    "FreeOnlineDramaScraper",
    "GogoAnimeBaScraper",
    "LuciferDonghuaScraper",
    "LeetScraper",
    "XMoviesScraper",
]

# Maps site name (from DB) -> scraper class for dynamic instantiation.
SCRAPER_REGISTRY: dict[str, type[BaseScraper]] = {
    "Movie2K": Movie2KScraper,
    "SolarMovies": SolarMovieScraper,
    "FreeOnlineDrama": FreeOnlineDramaScraper,
    "GogoAnime": GogoAnimeBaScraper,
    "LuciferDonghua": LuciferDonghuaScraper,
    "1337x": LeetScraper,
    "XMovies": XMoviesScraper,
    "YTS": YTSScraper,
    "Dramacool": DramacoolScraper,
}
