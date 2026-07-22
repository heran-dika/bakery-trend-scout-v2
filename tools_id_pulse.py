from ddgs import DDGS
from datetime import datetime, timedelta
import time
import random

def fetch_id_pulse_articles(keywords: list, max_results: int = 10) -> list:
    """Cari artikel domestik. region='id-id' bias hasil ke konteks Indonesia,
    supaya kata ambigu (mis. 'tren') tidak nyasar ke bahasa lain."""
    ddgs = DDGS()
    articles = []
    for keyword in keywords:
        print(f"[ID Pulse] Searching: {keyword}")
        try:
            results = ddgs.text(
                keyword,
                timelimit='d',
                max_results=max_results,
                region='id-id'
            )
            for result in results:
                articles.append({
                    'title': result.get('title', ''),
                    'snippet': result.get('body', ''),
                    'url': result.get('href', ''),
                    'domain': extract_domain(result.get('href', '')),
                })
            time.sleep(random.uniform(3, 8))
        except Exception as e:
            print(f"[ID Pulse] Error: {e}")
            continue
    return articles

def extract_domain(url: str) -> str:
    from urllib.parse import urlparse

    # Kadang ddgs balikin href yang ke-wrap markdown link: "[text](https://...)"
    # -- ambil URL asli di dalam kurung dulu kalau pola ini kedetect, sebelum diparse.
    # (String manipulation biasa, bukan regex -- lebih tahan terhadap masalah
    # copy-paste backslash antar environment.)
    s = url.strip()
    if s.startswith("[") and s.endswith(")") and "](" in s:
        idx = s.index("](")
        inner_url = s[idx + 2:-1]
        if inner_url.startswith("http://") or inner_url.startswith("https://"):
            url = inner_url

    parsed = urlparse(url)
    return parsed.netloc or "unknown"

DOMESTIC_KEYWORDS = [
    "roti viral",
    "bakery trending",
    "donat tren",
]

if __name__ == "__main__":
    articles = fetch_id_pulse_articles(DOMESTIC_KEYWORDS)
    print(f"Fetched {len(articles)} articles")