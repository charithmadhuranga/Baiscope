import requests
from bs4 import BeautifulSoup

def test_servers(url):
    print(f"--- Servers for {url} ---")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, "lxml")
    
    # Gogoanime servers
    for a in soup.select("div.anime_muti_link ul li a"):
        print(a.get("class", [""])[0], "->", a.get("data-video"))
        
    # Dramacool servers
    for li in soup.select(".list-server-items li"):
        print(li.get_text(strip=True), "->", li.get("data-video", ""))

test_servers("https://anitaku.to/gintama-silver-soul-arc-episode-1")
test_servers("https://ww16.dramacool.bg/episode/89993/encounter-2018-episode-1/")
