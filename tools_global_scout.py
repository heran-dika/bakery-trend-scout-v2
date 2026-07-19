from ddgs import DDGS
from datetime import datetime
import time
import random

COUNTRY_ROTATION = {
    0: ("South Korea", "떡 트렌드"),
    1: ("Japan", "パン トレンド"),
    2: ("USA", "trending bread TikTok"),
    3: ("Middle East", "خبز فايروسي"),
    4: ("Europe", "trending bakery"),
}

def get_todays_country():
    """Return (country_name, keyword) untuk hari ini."""
    day_of_week = datetime.now().weekday()
    return COUNTRY_ROTATION.get(day_of_week, ("USA", "trending bread"))

def fetch_global_scout_articles(country: str, keyword: str, max_results: int = 10) -> list:
    """Cari artikel global (7 hari) dengan keyword lokal."""
    ddgs = DDGS()
    articles = []
    
    print(f"[Global Scout] Searching {country}: {keyword}")
    try:
        results = ddgs.text(
            keyword,
            timelimit='w',
            max_results=max_results,
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
    parsed = urlparse(url)
    return parsed.netloc or "unknown"

if __name__ == "__main__":
    country, keyword = get_todays_country()
    articles = fetch_global_scout_articles(country, keyword)
    print(f"Fetched {len(articles)} articles from {country}")
