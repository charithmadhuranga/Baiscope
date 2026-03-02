"""SQLite database for Baiscope media catalog and settings."""

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


DB_PATH = Path.home() / ".baiscope" / "baiscope.db"


def _get_db_path() -> Path:
    path = Path.home() / ".baiscope"
    path.mkdir(parents=True, exist_ok=True)
    return path / "baiscope.db"


@dataclass
class MediaItem:
    id: Optional[int] = None
    title: str = ""
    cover_url: str = ""
    detail_url: str = ""
    source: str = ""
    source_name: str = ""
    media_type: str = ""
    catalog_name: Optional[str] = None
    source_site: Optional[str] = None
    created_at: Optional[str] = None


class Database:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or _get_db_path()
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS media (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                cover_url TEXT,
                detail_url TEXT,
                source TEXT,
                source_name TEXT,
                media_type TEXT,
                catalog_name TEXT,
                source_site TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS catalogs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                url TEXT NOT NULL,
                scraper_class TEXT NOT NULL,
                category TEXT NOT NULL,
                is_adult INTEGER DEFAULT 0,
                is_enabled INTEGER DEFAULT 1,
                display_order INTEGER DEFAULT 0,
                icon TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Migration: add source_site column if missing
        try:
            conn.execute("SELECT source_site FROM media LIMIT 1")
        except sqlite3.OperationalError:
            conn.execute("ALTER TABLE media ADD COLUMN source_site TEXT")
        conn.commit()
        conn.close()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ------------------------------------------------------------------ #
    #  Media CRUD                                                          #
    # ------------------------------------------------------------------ #
    def add_media(
        self,
        title: str,
        cover_url: str,
        detail_url: str,
        source: str,
        source_name: str,
        media_type: str,
        catalog_name: Optional[str] = None,
        source_site: Optional[str] = None,
    ) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO media (title, cover_url, detail_url, source, source_name,
                               media_type, catalog_name, source_site)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                cover_url,
                detail_url,
                source,
                source_name,
                media_type,
                catalog_name,
                source_site,
            ),
        )
        conn.commit()
        media_id = cursor.lastrowid
        conn.close()
        return media_id

    def get_media_by_catalog(self, catalog_name: str) -> list[MediaItem]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM media WHERE catalog_name = ? ORDER BY created_at DESC",
            (catalog_name,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_media(row) for row in rows]

    def get_all_media(self) -> list[MediaItem]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM media ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_media(row) for row in rows]

    def get_media_by_type(self, media_type: str) -> list[MediaItem]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM media WHERE media_type = ? ORDER BY created_at DESC",
            (media_type,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_media(row) for row in rows]

    def delete_media(self, media_id: int) -> None:
        conn = self.get_connection()
        conn.execute("DELETE FROM media WHERE id = ?", (media_id,))
        conn.commit()
        conn.close()

    def search_media(self, query: str) -> list[MediaItem]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM media WHERE title LIKE ? ORDER BY created_at DESC",
            (f"%{query}%",),
        )
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_media(row) for row in rows]

    def _row_to_media(self, row: sqlite3.Row) -> MediaItem:
        return MediaItem(
            id=row["id"],
            title=row["title"],
            cover_url=row["cover_url"],
            detail_url=row["detail_url"],
            source=row["source"],
            source_name=row["source_name"],
            media_type=row["media_type"],
            catalog_name=row["catalog_name"],
            source_site=row["source_site"] if "source_site" in row.keys() else None,
            created_at=row["created_at"],
        )

    # ------------------------------------------------------------------ #
    #  Catalogs                                                            #
    # ------------------------------------------------------------------ #
    def create_catalog(self, name: str, description: str = "") -> Optional[int]:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO catalogs (name, description) VALUES (?, ?)",
                (name, description),
            )
            conn.commit()
            catalog_id = cursor.lastrowid
            conn.close()
            return catalog_id
        except sqlite3.IntegrityError:
            conn.close()
            return None

    def get_catalogs(self) -> list[dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM catalogs ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def delete_catalog(self, catalog_id: int) -> None:
        conn = self.get_connection()
        conn.execute("DELETE FROM catalogs WHERE id = ?", (catalog_id,))
        conn.execute(
            "UPDATE media SET catalog_name = NULL WHERE catalog_name = ?",
            (str(catalog_id),),
        )
        conn.commit()
        conn.close()

    # ------------------------------------------------------------------ #
    #  Settings                                                            #
    # ------------------------------------------------------------------ #
    def get_setting(self, key: str, default: Any = None) -> Any:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        if row is None:
            return default
        value = row["value"]
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            if value == "True":
                return True
            elif value == "False":
                return False
            return value

    def set_setting(self, key: str, value: Any) -> None:
        conn = self.get_connection()
        if isinstance(value, (dict, list, bool)):
            value = json.dumps(value)
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value)),
        )
        conn.commit()
        conn.close()

    def initialize_default_settings(self) -> None:
        defaults = {
            "show_adult": False,
            "show_xmovies": False,
            "theme": "dark",
            "video_quality": "auto",
            "default_catalog": "Favorites",
        }
        for key, value in defaults.items():
            if self.get_setting(key) is None:
                self.set_setting(key, value)

    # ------------------------------------------------------------------ #
    #  Sites registry                                                      #
    # ------------------------------------------------------------------ #
    def initialize_sites(self) -> None:
        """Seed the sites table with default streaming sources."""
        default_sites = [
            # Movies
            ("Movie2K", "https://movie2k.quest", "Movie2KScraper", "movie", 0, 1, 10, "🎬"),
            ("SolarMovies", "https://solarmoviesz.com", "SolarMovieScraper", "movie", 0, 1, 20, "☀️"),
            ("YTS", "https://www.yts-official.top", "YTSScraper", "movie", 0, 1, 30, "🎥"),
            # Drama
            ("FreeOnlineDrama", "https://freeonlineda.top", "FreeOnlineDramaScraper", "drama", 0, 1, 40, "📺"),
            ("Dramacool", "https://ww16.dramacool.bg", "DramacoolScraper", "drama", 0, 1, 50, "🎭"),
            # Anime
            ("GogoAnime", "https://ww16.gogoanime.co.ba", "GogoAnimeBaScraper", "anime", 0, 1, 60, "🔵"),
            ("LuciferDonghua", "https://luciferdonghua.in", "LuciferDonghuaScraper", "anime", 0, 1, 70, "🐉"),
            # Torrents
            ("1337x", "https://www.1337xx.to", "LeetScraper", "torrent", 0, 1, 80, "🧲"),
            # Adult (hidden by default)
            ("XMovies", "https://www.imdb.com", "XMoviesScraper", "adult", 1, 0, 90, "🔞"),
        ]
        conn = self.get_connection()
        for name, url, scraper_class, category, is_adult, is_enabled, order, icon in default_sites:
            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO sites
                        (name, url, scraper_class, category, is_adult, is_enabled, display_order, icon)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (name, url, scraper_class, category, is_adult, is_enabled, order, icon),
                )
            except sqlite3.IntegrityError:
                pass
        conn.commit()
        conn.close()

    def get_sites(self, include_adult: bool = False) -> list[dict[str, Any]]:
        """Return all sites, optionally filtering out adult ones."""
        conn = self.get_connection()
        cursor = conn.cursor()
        if include_adult:
            cursor.execute("SELECT * FROM sites ORDER BY display_order")
        else:
            cursor.execute(
                "SELECT * FROM sites WHERE is_adult = 0 ORDER BY display_order"
            )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_enabled_sites(self, include_adult: bool = False) -> list[dict[str, Any]]:
        """Return only enabled sites."""
        conn = self.get_connection()
        cursor = conn.cursor()
        if include_adult:
            cursor.execute(
                "SELECT * FROM sites WHERE is_enabled = 1 ORDER BY display_order"
            )
        else:
            cursor.execute(
                "SELECT * FROM sites WHERE is_enabled = 1 AND is_adult = 0 ORDER BY display_order"
            )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_sites_by_category(
        self, category: str, include_adult: bool = False
    ) -> list[dict[str, Any]]:
        """Return sites filtered by category."""
        conn = self.get_connection()
        cursor = conn.cursor()
        if include_adult:
            cursor.execute(
                "SELECT * FROM sites WHERE category = ? ORDER BY display_order",
                (category,),
            )
        else:
            cursor.execute(
                "SELECT * FROM sites WHERE category = ? AND is_adult = 0 ORDER BY display_order",
                (category,),
            )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def toggle_site(self, site_id: int, enabled: bool) -> None:
        """Enable or disable a site."""
        conn = self.get_connection()
        conn.execute(
            "UPDATE sites SET is_enabled = ? WHERE id = ?",
            (1 if enabled else 0, site_id),
        )
        conn.commit()
        conn.close()

    def get_site_by_name(self, name: str) -> Optional[dict[str, Any]]:
        """Return a single site by name."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sites WHERE name = ?", (name,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None


db = Database()
