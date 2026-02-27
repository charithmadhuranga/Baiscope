"""Torrent streaming handler using libtorrent."""

import os
import threading
import time
from typing import Optional, Callable

import libtorrent as lt


class TorrentStreamer:
    """Streams torrents directly to VLC without full download."""
    
    def __init__(self, download_path: str = None):
        if download_path is None:
            download_path = os.path.expanduser("~/.baiscope/torrents")
        os.makedirs(download_path, exist_ok=True)
        self.download_path = download_path
        self.handle = None
        self.session = None
        self.torrent_info = None
        self._stream_url = None
        self._ready = False
        self._error = None
        
    def add_torrent(self, torrent_url: str, timeout: int = 30) -> bool:
        """Add a torrent and start streaming.
        
        Args:
            torrent_url: Can be a magnet link, .torrent file path, or URL
            
        Returns:
            True if torrent added successfully
        """
        self._ready = False
        self._error = None
        
        try:
            # Create session
            self.session = lt.session()
            self.session.listen_on(6881, 6891)
            
            # Set upload rate limit (don't kill your connection)
            self.session.set_upload_rate_limit(0)  # Unlimited upload
            
            # Add torrent
            if torrent_url.startswith("magnet:"):
                # It's a magnet link
                print(f"Adding magnet: {torrent_url[:50]}...")
                self.handle = lt.add_magnet_uri(self.session, torrent_url, {
                    'save_path': self.download_path,
                    'storage_mode': lt.storage_mode_t.storage_mode_sparse,
                })
            elif torrent_url.startswith("http"):
                # It's a URL - download torrent first
                import requests
                print(f"Downloading torrent from: {torrent_url[:50]}...")
                resp = requests.get(torrent_url, timeout=30)
                torrent_data = resp.content
                
                # Parse torrent
                self.torrent_info = lt.torrent_info(lt.bdecode(torrent_data))
                self.handle = self.session.add_torrent({
                    'ti': self.torrent_info,
                    'save_path': self.download_path,
                    'storage_mode': lt.storage_mode_t.storage_mode_sparse,
                })
            else:
                # It's a file path
                self.torrent_info = lt.torrent_info(torrent_url)
                self.handle = self.session.add_torrent({
                    'ti': self.torrent_info,
                    'save_path': self.download_path,
                    'storage_mode': lt.storage_mode_t.storage_mode_sparse,
                })
            
            # Wait for torrent to be ready
            print("Waiting for torrent to start...")
            start_time = time.time()
            while not self._ready and (time.time() - start_time) < timeout:
                self._check_torrent_state()
                time.sleep(0.5)
            
            if not self._ready:
                self._error = "Timeout waiting for torrent to start"
                return False
                
            return True
            
        except Exception as e:
            self._error = str(e)
            print(f"Error adding torrent: {e}")
            return False
    
    def _check_torrent_state(self):
        """Check torrent state and get streamable file."""
        if not self.handle:
            return
            
        s = self.handle.status()
        
        # Check if we have enough pieces to start playing
        if s.progress > 0.01:  # At least 1% downloaded
            # Find a video file
            torrent_files = self.handle.get_torrent_info().files()
            
            # Look for video files
            video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.webm']
            
            for i, file in enumerate(torrent_files):
                filename = file.path
                if any(filename.lower().endswith(ext) for ext in video_extensions):
                    # Found a video file
                    # Generate the file path
                    self._stream_url = os.path.join(self.download_path, filename)
                    self._ready = True
                    print(f"Found video: {filename}")
                    return
    
    def get_stream_url(self) -> Optional[str]:
        """Get the path to the streaming file."""
        if self._ready:
            return self._stream_url
        return None
    
    def get_status(self) -> dict:
        """Get current streaming status."""
        if not self.handle:
            return {"state": "idle", "progress": 0, "download_rate": 0}
        
        s = self.handle.status()
        
        state_map = {
            0: "queued",
            1: "checking",
            2: "downloading_metadata",
            3: "downloading",
            4: "finished",
            5: "seeding",
            6: "allocating",
            7: "checking_resume_data",
        }
        
        return {
            "state": state_map.get(s.state, "unknown"),
            "progress": s.progress * 100,
            "download_rate": s.download_rate / 1024,  # KB/s
            "upload_rate": s.upload_rate / 1024,
            "peers": s.num_peers,
            "seeds": s.num_seeds,
            "error": self._error,
        }
    
    def stop(self):
        """Stop streaming and clean up."""
        if self.session:
            try:
                if self.handle:
                    self.session.remove_torrent(self.handle)
                self.session.stop_dht()
                self.session.stop_lsd()
                self.session.stop_upnp()
                self.session.stop_natpmp()
            except Exception:
                pass
        self.handle = None
        self.session = None
        self._ready = False


def stream_torrent(torrent_url: str, progress_callback: Callable = None) -> Optional[str]:
    """Convenience function to stream a torrent.
    
    Args:
        torrent_url: Magnet link or torrent URL
        progress_callback: Optional callback for progress updates
        
    Returns:
        Path to streaming file when ready, None on error
    """
    streamer = TorrentStreamer()
    
    if streamer.add_torrent(torrent_url):
        # Wait for file to be ready
        while not streamer.get_stream_url():
            status = streamer.get_status()
            if progress_callback:
                progress_callback(status)
            if status.get("error"):
                break
            time.sleep(1)
        
        return streamer.get_stream_url()
    
    return None


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
        print(f"Streaming: {url}")
        
        streamer = TorrentStreamer()
        
        def progress(status):
            print(f"Progress: {status['progress']:.1f}% | Peers: {status['peers']} | DL: {status['download_rate']:.0f} KB/s")
        
        if streamer.add_torrent(url):
            print("Streaming started!")
            
            while True:
                status = streamer.get_status()
                progress(status)
                
                if streamer.get_stream_url():
                    print(f"File ready: {streamer.get_stream_url()}")
                    break
                    
                if status.get("error"):
                    print(f"Error: {status['error']}")
                    break
                    
                time.sleep(2)
        else:
            print(f"Failed to add torrent: {streamer._error}")
    else:
        print("Usage: python torrent_streamer.py <magnet_url>")
