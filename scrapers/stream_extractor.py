"""Stream URL extractor using Selenium browser automation."""

import time
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager


class StreamExtractor:
    """Extracts direct video URLs from streaming sites using Selenium."""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        
    def _get_driver(self) -> webdriver.Chrome:
        """Create and configure Chrome driver."""
        options = Options()
        
        if self.headless:
            options.add_argument("--headless=new")
        
        # Use system Chrome
        options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Disable web security to allow CORS
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--allow-file-access-from-files")
        
        # Use ChromeDriverManager to get the right driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(30)
        return driver
    
    def extract_stream_url(self, url: str, timeout: int = 20) -> Optional[dict]:
        """Extract video stream URL from a streaming page.
        
        Returns:
            dict with 'url' and 'headers' if successful, None otherwise
        """
        try:
            if not self.driver:
                self.driver = self._get_driver()
            
            print(f"Loading: {url}")
            self.driver.get(url)
            
            # Wait for video element
            time.sleep(3)
            
            # Try to find video element
            video_url = None
            
            # Method 1: Find <video> tag with src
            try:
                video = self.driver.find_element(By.TAG_NAME, "video")
                src = video.get_attribute("src")
                if src and (src.startswith("http") or src.startswith("//")):
                    if src.startswith("//"):
                        src = "https:" + src
                    print(f"Found video src: {src[:60]}...")
                    video_url = src
            except Exception:
                pass
            
            # Method 2: Find source elements inside video
            if not video_url:
                try:
                    sources = self.driver.find_elements(By.CSS_SELECTOR, "video source")
                    for source in sources:
                        src = source.get_attribute("src")
                        if src and (src.startswith("http") or src.startswith("//")):
                            if src.startswith("//"):
                                src = "https:" + src
                            print(f"Found source src: {src[:60]}...")
                            video_url = src
                            break
                except Exception:
                    pass
            
            # Method 3: Look for iframe and get its src
            if not video_url:
                try:
                    iframe = self.driver.find_element(By.TAG_NAME, "iframe")
                    src = iframe.get_attribute("src")
                    if src:
                        print(f"Found iframe: {src[:60]}...")
                        # Navigate to iframe
                        self.driver.switch_to.frame(iframe)
                        time.sleep(2)
                        
                        # Try again to find video
                        try:
                            video = self.driver.find_element(By.TAG_NAME, "video")
                            src = video.get_attribute("src")
                            if src:
                                if src.startswith("//"):
                                    src = "https:" + src
                                video_url = src
                        except Exception:
                            pass
                            
                        self.driver.switch_to.default_content()
                except Exception:
                    pass
            
            # Method 4: Look for jwplayer or other player divs
            if not video_url:
                try:
                    # Check for jwplayer
                    jw_div = self.driver.find_element(By.ID, "player")
                    html = jw_div.get_attribute("innerHTML")
                    if "jwplayer" in html.lower():
                        # Try to extract from JavaScript
                        print("Found jwplayer, trying to extract URL...")
                except Exception:
                    pass
            
            if video_url:
                return {
                    "url": video_url,
                    "headers": {"Referer": url}
                }
            
            print("No video URL found")
            return None
            
        except TimeoutException:
            print(f"Timeout loading: {url}")
            return None
        except WebDriverException as e:
            print(f"WebDriver error: {e}")
            return None
        except Exception as e:
            print(f"Error extracting stream: {e}")
            return None
    
    def close(self):
        """Close the browser."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
    
    def __del__(self):
        self.close()


def extract_stream(url: str, timeout: int = 20) -> Optional[dict]:
    """Convenience function to extract stream URL."""
    extractor = StreamExtractor(headless=True)
    try:
        return extractor.extract_stream_url(url, timeout)
    finally:
        extractor.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        result = extract_stream(sys.argv[1])
        if result:
            print(f"SUCCESS: {result['url']}")
        else:
            print("FAILED")
