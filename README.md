<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776ab?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/PySide6-Qt6-41cd52?style=for-the-badge&logo=qt&logoColor=white" />
  <img src="https://img.shields.io/badge/VLC-Player-ff8800?style=for-the-badge&logo=vlcmediaplayer&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" />
</p>

# 🎥 Baiscope

**A desktop media streaming aggregator** that brings anime, movies, dramas, donghua, and torrents from multiple streaming sites into one sleek native app with an integrated video player.

---

## ✨ Features

- **🌐 Multi-Source Streaming** — Browse and search across 9+ streaming sites from a single app
- **🎬 Movies** — Movie2K, SolarMovies, YTS
- **📺 Drama** — FreeOnlineDrama, Dramacool
- **🔵 Anime & Donghua** — GogoAnime, LuciferDonghua
- **🧲 Torrent Streaming** — Stream torrents directly from 1337x via magnet links (no full download needed)
- **📁 Custom Catalogs** — Create personal collections mixing content from any source
- **⭐ Favorites** — Save and manage your favorite media
- **🔍 Smart Search** — Search a specific site or across all sources at once
- **🏷️ Auto-Tagging** — Content automatically tagged as movie/drama/anime based on its source
- **🔞 Adult Content Control** — Hidden by default, togglable in Settings
- **🎮 Dual Player** — VLC for direct streams, Qt WebEngine for embed players
- **🌙 Dark Theme** — Premium dark UI with glassmorphism and smooth animations

---

## 📸 Screenshots

> *Launch the app to see the UI — `uv run python main.py`*

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **uv** (recommended) or pip
- **VLC Media Player** installed on your system

### Install & Run

```bash
# Clone the repo
git clone https://github.com/charithmadhuranga/Baiscope.git
cd Baiscope

# Install dependencies with uv
uv sync

# Run the app
uv run python main.py
```

### Alternative (pip)

```bash
pip install -e .
baiscope
```

---

## 🌐 Supported Sources

| Site | Category | URL |
|------|----------|-----|
| 🎬 Movie2K | Movies | `movie2k.quest` |
| ☀️ SolarMovies | Movies / TV | `solarmoviesz.com` |
| 🎥 YTS | Movies / Torrents | `yts-official.top` |
| 📺 FreeOnlineDrama | Drama | `freeonlineda.top` |
| 🎭 Dramacool | Asian Drama | `dramacool.bg` |
| 🔵 GogoAnime | Anime | `gogoanime.co.ba` |
| 🐉 LuciferDonghua | Donghua | `luciferdonghua.in` |
| 🧲 1337x | Torrents | `1337xx.to` |
| 🔞 XMovies | Adult | Hidden by default |

---

## 🏗️ Architecture

```
Baiscope/
├── main.py                  # Entry point
├── db.py                    # SQLite database (media, catalogs, settings, sites)
├── scrapers/
│   ├── base.py              # Abstract BaseScraper with retry logic
│   ├── movie2k_scraper.py   # Movie2K
│   ├── solarmovie_scraper.py # SolarMovies
│   ├── freeonlinedrama_scraper.py  # FreeOnlineDrama
│   ├── gogoanime_ba_scraper.py     # GogoAnime
│   ├── lucifer_donghua_scraper.py  # LuciferDonghua
│   ├── leet_scraper.py      # 1337x torrents
│   ├── xmovies_scraper.py   # Adult content
│   ├── yts.py               # YTS movies
│   ├── dramacool.py          # Dramacool
│   ├── stream_extractor.py  # yt-dlp stream URL extraction
│   └── torrent_streamer.py  # libtorrent streaming
├── ui/
│   ├── main_window.py       # App window with site-based routing
│   ├── site_catalog_page.py # Sites grid grouped by category
│   ├── search_page.py       # Search with source selector
│   ├── browse_page.py       # Browse content from a selected site
│   ├── detail_page.py       # Media detail with source badge
│   ├── player_page.py       # VLC + WebEngine dual player
│   ├── favorites_page.py    # Saved favorites
│   ├── catalog_page.py      # Custom catalogs
│   ├── settings_page.py     # Settings with X Movies toggle
│   └── widgets/
│       ├── card.py           # ClickableCard widget
│       └── nav_bar.py        # Sidebar navigation
├── workers/                  # Background QThread workers
├── cache/                    # Disk-based image cache
└── pyproject.toml
```

---

## 🔧 How It Works

1. **Sites Registry** — All streaming sources are registered in a SQLite `sites` table with category, URL, and enable/disable state
2. **Scraper Registry** — `SCRAPER_REGISTRY` maps site names to scraper classes for dynamic instantiation
3. **Browse** — Click a site → `BrowsePage` loads popular content using that site's scraper
4. **Search** — Select a source (or "All Sources") → search runs against selected scraper(s)
5. **Play** — Episode URL → `StreamExtractor` (yt-dlp) extracts direct URL → VLC plays it; or embed URL → WebEngine
6. **Torrents** — Magnet links from 1337x → `TorrentStreamer` (libtorrent) → streams to VLC
7. **Auto-Tag** — Media saved to catalogs is automatically tagged (movie/drama/anime) based on source

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `pyside6` | Qt6 GUI framework |
| `requests` | HTTP requests |
| `beautifulsoup4` + `lxml` | HTML parsing |
| `yt-dlp` | Stream URL extraction |
| `python-vlc` | VLC media player bindings |
| `libtorrent` | Torrent streaming (optional) |

---

## ⚙️ Settings

| Setting | Description |
|---------|-------------|
| **Show X Movies** | Reveals adult streaming sources (hidden by default) |
| **Per-site toggles** | Enable/disable individual streaming sites |
| **Custom Catalogs** | Create, manage, and delete personal collections |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing`)
5. Open a Pull Request

---

## ⚠️ Disclaimer

This application is intended for **educational purposes only**. The developers do not host, store, or distribute any copyrighted content. All media is sourced from third-party websites. Users are responsible for complying with their local laws regarding streaming and downloading content.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
