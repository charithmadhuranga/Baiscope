"""Player page — embedded VLC video player in a PySide6 widget."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

# python-vlc is optional — graceful fallback
try:
    import vlc  # type: ignore[import-untyped]

    HAS_VLC = True
except (ImportError, OSError):
    HAS_VLC = False

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False


def _fmt_time(ms: int) -> str:
    """Format milliseconds as MM:SS."""
    if ms < 0:
        ms = 0
    total_seconds = ms // 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"



from PySide6.QtWebEngineCore import QWebEnginePage

class LoggingPage(QWebEnginePage):
    """Custom WebEnginePage to intercept and print JS console logs."""
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        # Print all JS console messages to terminal for debugging
        print(f"js[{level}]: {message} (line {lineNumber} in {sourceID})")


class PlayerPage(QWidget):
    """Embedded VLC media player page.

    Falls back to a placeholder label when VLC is not available.

    Signals
    -------
    back_requested : signal
        Emitted when the user clicks back.
    """

    back_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("PlayerPage")

        self._vlc_instance = None
        self._media_player = None
        self._is_seeking = False
        self._current_url = ""  # Store current URL for browser fallback

        self._build_ui()
        self._apply_style()

        if HAS_VLC:
            self._init_vlc()

        # Position poll timer
        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._update_position)

    # ------------------------------------------------------------------ #
    #  Layout                                                              #
    # ------------------------------------------------------------------ #
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Top bar
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(16, 10, 16, 10)

        self.back_btn = QPushButton("← Back")
        self.back_btn.setObjectName("PlayerBackBtn")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.clicked.connect(self._on_back)
        top_bar.addWidget(self.back_btn)

        self.now_playing = QLabel("Nothing playing")
        self.now_playing.setObjectName("NowPlaying")
        top_bar.addWidget(self.now_playing, stretch=1)

        root.addLayout(top_bar)

        # Video surface
        from PySide6.QtWidgets import QStackedWidget
        self.video_stack = QStackedWidget()
        
        self.video_frame = QFrame()
        self.video_frame.setObjectName("VideoFrame")
        self.video_frame.setMinimumSize(640, 360)
        self.video_stack.addWidget(self.video_frame)

        if HAS_WEBENGINE:
            self.webview = QWebEngineView()
            
            # Attach custom LoggingPage to print JS errors to terminal
            self.logging_page = LoggingPage(self.webview)
            self.webview.setPage(self.logging_page)
            
            # Configure Profile to prevent ERR_BLOCKED_BY_CLIENT
            profile = self.webview.page().profile()
            
            # Allow all cookies (essential for embedded JWPlayers)
            from PySide6.QtWebEngineCore import QWebEngineProfile
            profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)
            
            # Disable generic Tracking Prevention if it exists (Qt 6.7+)
            if hasattr(profile, "setTrackingPreventionEnabled"):
                profile.setTrackingPreventionEnabled(False)
            
            self.webview.settings().setAttribute(
                self.webview.settings().WebAttribute.PlaybackRequiresUserGesture, False
            )
            self.video_stack.addWidget(self.webview)

        root.addWidget(self.video_stack, stretch=1)

        # Fallback label (shown when player is unavailable)
        fallback_container = QWidget()
        fallback_layout = QVBoxLayout(fallback_container)
        fallback_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.fallback_label = QLabel(
            "Unable to play this stream.\n\n"
            "Please try using the external player option below."
        )
        self.fallback_label.setObjectName("FallbackLabel")
        self.fallback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fallback_layout.addWidget(self.fallback_label)
        
        # Open in Browser button
        self.open_browser_btn = QPushButton("🌐 Open in Browser")
        self.open_browser_btn.setObjectName("OpenBrowserBtn")
        self.open_browser_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_browser_btn.clicked.connect(self._open_in_browser)
        self.open_browser_btn.setVisible(False)
        fallback_layout.addWidget(self.open_browser_btn)
        
        fallback_container.setVisible(False)
        root.addWidget(fallback_container)
        self.fallback_container = fallback_container

        # Controls row
        self.controls_widget = QWidget()
        controls = QHBoxLayout(self.controls_widget)
        controls.setContentsMargins(16, 8, 16, 12)
        controls.setSpacing(10)

        self.play_btn = QPushButton("▶")
        self.play_btn.setObjectName("CtrlBtn")
        self.play_btn.setFixedSize(40, 40)
        self.play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_btn.clicked.connect(self._toggle_play)
        controls.addWidget(self.play_btn)

        self.stop_btn = QPushButton("⏹")
        self.stop_btn.setObjectName("CtrlBtn")
        self.stop_btn.setFixedSize(40, 40)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.clicked.connect(self._stop)
        controls.addWidget(self.stop_btn)

        self.time_label = QLabel("00:00")
        self.time_label.setObjectName("TimeLabel")
        self.time_label.setFixedWidth(50)
        controls.addWidget(self.time_label)

        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setObjectName("SeekSlider")
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.sliderPressed.connect(self._on_seek_start)
        self.seek_slider.sliderReleased.connect(self._on_seek_end)
        self.seek_slider.sliderMoved.connect(self._seek)
        controls.addWidget(self.seek_slider, stretch=1)

        self.duration_label = QLabel("00:00")
        self.duration_label.setObjectName("TimeLabel")
        self.duration_label.setFixedWidth(50)
        controls.addWidget(self.duration_label)

        vol_icon = QLabel("🔊")
        vol_icon.setStyleSheet("font-size: 16px;")
        controls.addWidget(vol_icon)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setObjectName("VolumeSlider")
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.valueChanged.connect(self._set_volume)
        controls.addWidget(self.volume_slider)

        root.addWidget(self.controls_widget)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            #PlayerPage { background: #0d0d14; }
            #PlayerBackBtn {
                background: rgba(139,92,246,0.15);
                border: 1px solid rgba(139,92,246,0.3);
                border-radius: 8px;
                color: #b794f6;
                padding: 6px 16px;
                font-size: 13px;
                font-weight: 600;
            }
            #PlayerBackBtn:hover { background: rgba(139,92,246,0.25); }
            #NowPlaying {
                color: #aaa;
                font-size: 14px;
                padding-left: 12px;
            }
            #VideoFrame {
                background: #000;
                border: none;
            }
            #CtrlBtn {
                background: #1e1e2e;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px;
                color: #e0e0e0;
                font-size: 16px;
            }
            #CtrlBtn:hover { background: rgba(139,92,246,0.2); }
            #TimeLabel {
                color: #aaa;
                font-size: 12px;
            }
            #SeekSlider, #VolumeSlider {
                height: 6px;
            }
            QSlider::groove:horizontal {
                background: #2a2a3e;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #8b5cf6;
                width: 14px;
                height: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #8b5cf6, stop:1 #6d28d9
                );
                border-radius: 3px;
            }
            #FallbackLabel {
            #    color: #888;
            #    font-size: 16px;
            #}
            #OpenBrowserBtn {
                background: rgba(59, 130, 246, 0.2);
                border: 1px solid rgba(59, 130, 246, 0.5);
                border-radius: 8px;
                color: #60a5fa;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
                margin-top: 16px;
            }
            #OpenBrowserBtn:hover { background: rgba(59, 130, 246, 0.3); }
            """
        )

    # ------------------------------------------------------------------ #
    #  VLC integration                                                     #
    # ------------------------------------------------------------------ #
    def _init_vlc(self) -> None:
        args = ["--no-xlib"] if sys.platform != "darwin" else []
        self._vlc_instance = vlc.Instance(*args)
        self._media_player = self._vlc_instance.media_player_new()

        # Embed VLC into the QFrame
        if sys.platform == "darwin":
            self._media_player.set_nsobject(int(self.video_frame.winId()))
        elif sys.platform == "win32":
            self._media_player.set_hwnd(int(self.video_frame.winId()))
        else:
            self._media_player.set_xwindow(int(self.video_frame.winId()))

        self._media_player.audio_set_volume(80)

    def _try_webengine(self, url: str, headers: dict) -> bool:
        """Try to play URL in WebEngine."""
        if not HAS_WEBENGINE:
            return False
        
        try:
            self.fallback_container.setVisible(False)
            self.video_stack.setVisible(True)
            self.video_stack.setCurrentWidget(self.webview)
            self.controls_widget.setVisible(False)
            
            # Clear cache
            self.webview.page().profile().clearHttpCache()
            
            # Configure settings
            settings = self.webview.settings()
            settings.setAttribute(settings.WebAttribute.JavascriptEnabled, True)
            settings.setAttribute(settings.WebAttribute.PluginsEnabled, True)
            settings.setAttribute(settings.WebAttribute.JavascriptCanOpenWindows, True)
            settings.setAttribute(settings.WebAttribute.AllowRunningInsecureContent, True)
            settings.setAttribute(settings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
            settings.setAttribute(settings.WebAttribute.AllowWindowActivationFromJavaScript, True)
            settings.setAttribute(settings.WebAttribute.FullScreenSupportEnabled, True)
            settings.setAttribute(settings.WebAttribute.WebGLEnabled, True)
            
            from PySide6.QtCore import QUrl
            
            # Try direct URL loading with proper headers
            # Use data URL approach for better compatibility
            html_content = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Player</title>
                <style>
                    * {{ margin: 0; padding: 0; }}
                    html, body {{ width: 100%; height: 100%; background: #000; }}
                    iframe {{ width: 100%; height: 100%; border: none; }}
                </style>
            </head>
            <body>
                <iframe src="{url}" allowfullscreen></iframe>
            </body>
            </html>
            '''
            
            self.webview.setHtml(html_content, baseUrl=QUrl("about:blank"))
            return True
            
        except Exception as e:
            print(f"WebEngine failed: {e}")
            return False

    def _play_with_vlc(self, url: str, headers: dict) -> bool:
        """Try to play URL with VLC."""
        if not HAS_VLC or not self._media_player:
            return False
        
        try:
            self.fallback_container.setVisible(False)
            self.video_stack.setVisible(True)
            self.video_stack.setCurrentWidget(self.video_frame)
            self.controls_widget.setVisible(True)
            
            # Prepare VLC options
            options = []
            if headers.get("Referer"):
                options.append(f":http-referrer={headers['Referer']}")
            if headers.get("User-Agent"):
                options.append(f":http-user-agent={headers['User-Agent']}")
            else:
                options.append(
                    ":http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )

            media = self._vlc_instance.media_new(url, *options)
            self._media_player.set_media(media)
            self._media_player.play()
            
            if hasattr(self, 'play_btn'):
                self.play_btn.setText("⏸")
            self._timer.start()
            return True
            
        except Exception as e:
            print(f"VLC failed: {e}")
            return False

    def _stream_torrent(self, url: str) -> None:
        """Stream torrent using libtorrent."""
        try:
            from scrapers.torrent_streamer import TorrentStreamer
            
            self._show_fallback("Starting torrent stream...\n\nThis may take a moment to connect to peers...")
            
            # Start torrent in background thread
            def start_torrent():
                streamer = TorrentStreamer()
                if streamer.add_torrent(url, timeout=60):
                    # Wait for file to be ready
                    while not streamer.get_stream_url():
                        status = streamer.get_status()
                        if status.get("error"):
                            break
                        import time
                        time.sleep(2)
                    
                    # Get the file path and play
                    stream_path = streamer.get_stream_url()
                    if stream_path:
                        # Play the file
                        from PySide6.QtCore import QMetaObject, Qt
                        QMetaObject.invokeMethod(
                            self,
                            lambda: self._play_with_vlc(stream_path, {}),
                            Qt.QueuedConnection
                        )
                streamer.stop()
            
            import threading
            thread = threading.Thread(target=start_torrent, daemon=True)
            thread.start()
            
        except ImportError:
            self._show_fallback("Torrent streaming requires libtorrent.\n\nOpening in browser...")
            self._open_in_browser()
        except Exception as e:
            self._show_fallback(f"Torrent error: {str(e)[:50]}...\n\nOpening in browser...")
            self._open_in_browser()

    def play(self, source: str | dict, title: str = "") -> None:
        """Play the given stream source (URL or metadata dict)."""
        self._stop()

        url = ""
        headers = {}
        
        if isinstance(source, dict):
            url = source.get("url", "")
            headers = source.get("headers", {})
        else:
            url = source

        # Store URL for browser fallback
        self._current_url = url
        self.now_playing.setText(title or url)

        # Handle Torrents - try streaming with libtorrent first
        if url.endswith(".torrent") or url.startswith("magnet:"):
            self._stream_torrent(url)
            return

        # Direct video files - play with VLC
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.m3u8']
        if any(url.lower().endswith(ext) for ext in video_extensions):
            self._play_with_vlc(url, headers)
            return

        # Try WebEngine for embed URLs
        if self._try_webengine(url, headers):
            return
        
        # Try VLC for direct streams
        if self._play_with_vlc(url, headers):
            return
        
        # Last resort - open in browser
        self._show_fallback(
            "Unable to play embedded.\n\n"
            "Click below to open in browser."
        )
        self._open_in_browser()

    def _toggle_play(self) -> None:
        if not self._media_player:
            return
        if self._media_player.is_playing():
            self._media_player.pause()
            self.play_btn.setText("▶")
            self._timer.stop()
        else:
            self._media_player.play()
            self.play_btn.setText("⏸")
            self._timer.start()

    def _stop(self) -> None:
        if self._media_player:
            self._media_player.stop()
        if HAS_WEBENGINE and hasattr(self, "webview"):
            from PySide6.QtCore import QUrl
            self.webview.setUrl(QUrl("about:blank"))
        if hasattr(self, "play_btn"):
            self.play_btn.setText("▶")
            self._timer.stop()
            self.seek_slider.setValue(0)
            self.time_label.setText("00:00")
            self.duration_label.setText("00:00")

    def _on_seek_start(self) -> None:
        self._is_seeking = True

    def _on_seek_end(self) -> None:
        self._is_seeking = False
        self._seek(self.seek_slider.value())

    def _seek(self, position: int) -> None:
        if self._media_player:
            self._media_player.set_position(position / 1000.0)

    def _set_volume(self, value: int) -> None:
        if self._media_player:
            self._media_player.audio_set_volume(value)

    def _show_fallback(self, message: str) -> None:
        """Show fallback with message and browser button if URL available."""
        self.video_stack.setVisible(False)
        self.fallback_container.setVisible(True)
        self.fallback_label.setText(message)
        # Always show browser button when we have a URL
        if self._current_url:
            self.open_browser_btn.setVisible(True)
            self.open_browser_btn.setText("🌐 Open in Browser")
        else:
            self.open_browser_btn.setVisible(False)

    def _open_in_browser(self) -> None:
        """Open current URL in system default browser."""
        if self._current_url:
            import webbrowser
            webbrowser.open(self._current_url)

    def _update_position(self) -> None:
        """Poll VLC for current position and update UI."""
        if not self._media_player:
            return
        if self._is_seeking:
            return

        pos = self._media_player.get_position()  # 0.0 → 1.0
        length = self._media_player.get_length()  # ms
        current = self._media_player.get_time()  # ms

        if pos >= 0:
            self.seek_slider.setValue(int(pos * 1000))
        if current >= 0:
            self.time_label.setText(_fmt_time(current))
        if length > 0:
            self.duration_label.setText(_fmt_time(length))

    def _on_back(self) -> None:
        self._stop()
        self.back_requested.emit()

    # ------------------------------------------------------------------ #
    #  Cleanup                                                             #
    # ------------------------------------------------------------------ #
    def closeEvent(self, event) -> None:  # noqa: N802
        self._stop()
        super().closeEvent(event)
