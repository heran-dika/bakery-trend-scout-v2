from ddgs import DDGS
from datetime import datetime
import time
import random

# region: kode DDG {country}-{language}.
# Revisi 2026-07-23: Middle East & Europe di-drop (terlalu generic/catch-all,
# gak sesuai target pasar -- lidah bakery Indonesia lebih dekat ke Asia).
# Digantikan Malaysia & Thailand (negara tetangga, keyword sudah dites/dites
# ulang buat filter noise TikTok-discover & platform-noise lain).
# China dites juga (query native Mandarin hasilnya bagus), tapi DI-DROP
# dulu atas keputusan Dika 2026-07-23 -- bisa direvisit nanti.
COUNTRY_ROTATION = {
    0: ("South Korea", "ë–¡ íŠ¸ë Œë“œ", "kr-kr"),
    1: ("Japan", "ãƒ‘ãƒ³ ãƒˆãƒ¬ãƒ³ãƒ‰", "jp-jp"),
    2: ("USA", "trending bread TikTok", "us-en"),
    3: ("Malaysia", "kedai roti viral Malaysia", "my-en"),
    4: ("Thailand", "à¸‚à¸™à¸¡à¸›à¸±à¸‡ à¹€à¸—à¸£à¸™à¸”à¹Œ 2026", "th-en"),
}

def get_todays_country():
    """Return (country_name, keyword, region) untuk hari ini, atau None
    kalau weekend (Sabtu/Minggu) -- desain sengaja cuma scan hari kerja,
    BUKAN fallback diam-diam ke negara manapun."""
    day_of_week = datetime.now().weekday()
    return COUNTRY_ROTATION.get(day_of_week)

def fetch_global_scout_articles(country: str, keyword: str, region: str = "wt-wt", max_results: int = 10) -> list:
    """Cari artikel global (7 hari) dengan keyword lokal, di-bias ke region negara target."""
    ddgs = DDGS()
    articles = []
    print(f"[Global Scout] Searching {country} ({region}): {keyword}")
    try:
        results = ddgs.text(
            keyword,
            timelimit='w',
            max_results=max_results,
            region=region,
        )
        for result in results:
            articles.append({
                'title': result.get('title', ''),
                'snippet': result.get('body', ''),
                'url': result.get('href', ''),
                'domain': extract_domain(result.get('href', '')),
                'country': country,
            })
        time.sleep(random.uniform(3, 8))
    except Exception as e:
        print(f"[Global Scout] Error untuk {country}: {e}")
        return []
    return articles

def extract_domain(url: str) -> str:
    from urllib.parse import urlparse
    s = url.strip()
    if s.startswith("[") and s.endswith(")") and "](" in s:
        idx = s.index("](")
        inner_url = s[idx + 2:-1]
        if inner_url.startswith("http://") or inner_url.startswith("https://"):
            url = inner_url
    parsed = urlparse(url)
    return parsed.netloc or "unknown"

if __name__ == "__main__":
    result = get_todays_country()
    if result is None:
        print("Weekend -- tidak ada negara terjadwal hari ini.")
    else:
        country, keyword, region = result
        articles = fetch_global_scout_articles(country, keyword, region)
        print(f"Fetched {len(articles)} articles from {country}")
