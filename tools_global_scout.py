from ddgs import DDGS
from datetime import datetime
import time
import random

# region: kode DDG {country}-{language}. "Middle East" & "Europe" tidak
# punya kode region tunggal resmi (bukan negara spesifik) -- xa-ar untuk
# Middle East cukup umum dipakai, wt-wt (worldwide) untuk Europe sementara
# sampai dipersempit ke negara spesifik.
COUNTRY_ROTATION = {
    0: ("South Korea", "떡 트렌드", "kr-kr"),
    1: ("Japan", "パン トレンド", "jp-jp"),
    2: ("USA", "trending bread TikTok", "us-en"),
    3: ("Middle East", "خبز فايروسي", "xa-ar"),
    4: ("Europe", "trending bakery", "wt-wt"),
}

def get_todays_country():
    """Return (country_name, keyword, region) untuk hari ini."""
    day_of_week = datetime.now().weekday()
    return COUNTRY_ROTATION.get(day_of_week, ("USA", "trending bread", "us-en"))

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

if __name__ == "__main__":
    country, keyword, region = get_todays_country()
    articles = fetch_global_scout_articles(country, keyword, region)
    print(f"Fetched {len(articles)} articles from {country}")