from ddgs import DDGS
from datetime import datetime, timedelta
import time
import random

def fetch_id_pulse_articles(keywords: list, max_results: int = 10) -> list:
    """Cari artikel domestik."""
    ddgs = DDGS()
    articles = []
    
    for keyword in keywords:
        print(f"[ID Pulse] Searching: {keyword}")
        try:
            results = ddgs.text(
                keyword,
                timelimit='d',
                max_results=max_results,
                language='id'
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
