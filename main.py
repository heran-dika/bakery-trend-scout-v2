import os
from datetime import datetime
from dotenv import load_dotenv

from tools_id_pulse import fetch_id_pulse_articles, DOMESTIC_KEYWORDS
from tools_global_scout import fetch_global_scout_articles, get_todays_country
from canonicalize import canonicalize_entities
from db_operations import insert_daily_trends
from agent_trend_analyst import update_trend_status
from agent_reporter import generate_report, send_email

load_dotenv()

BAKERY_KEYWORDS = [
    "roti", "bread", "bakery", "donat", "donut", "cake", "kue",
    "pastry", "croissant", "brioche", "pan", "boulangerie",
    "떡", "パン", "خبز", "roll", "loaf", "dough", "adonan",
    "panggang", "oven", "tepung", "sourdough"
]

def is_bakery_related(title: str, snippet: str) -> bool:
    """Rule-based filter: title/snippet harus mengandung keyword bakery."""
    text = (title + " " + snippet).lower()
    return any(kw.lower() in text for kw in BAKERY_KEYWORDS)

def main():
    print(f"\n{'='*60}")
    print(f"BakeryTrendScout Daily Run - {datetime.now().strftime('%Y-%m-%d')}")
    print(f"{'='*60}\n")
    
    # ID Pulse
    print("[1] Fetching ID Pulse...")
    id_articles = fetch_id_pulse_articles(DOMESTIC_KEYWORDS, max_results=5)
    print(f"    -> {len(id_articles)} articles fetched\n")
    
    id_articles_filtered = [a for a in id_articles if is_bakery_related(a['title'], a['snippet'])]
    dropped = len(id_articles) - len(id_articles_filtered)
    print(f"    -> {len(id_articles_filtered)} kept, {dropped} dropped (not bakery-related)\n")
    
    if id_articles_filtered:
        entities = [
            {
                'trend_name': a['title'][:60],
                'sentiment': 'Neutral',
                'url': a['url'],
                'domain': a['domain'],
                'title': a['title']
            }
            for a in id_articles_filtered
        ]
        
        print("[2] Canonicalizing...")
        canonical = canonicalize_entities(entities)
        print(f"    -> {len(canonical)} unique trends\n")
        
        print("[3] Inserting to DB...")
        inserted = insert_daily_trends(canonical, origin="Domestic")
        print(f"    -> {inserted} trends inserted\n")
    
    # Global Scout
    print("[4] Fetching Global Scout...")
    country, keyword = get_todays_country()
    global_articles = fetch_global_scout_articles(country, keyword, max_results=5)
    print(f"    -> {len(global_articles)} articles fetched from {country}\n")
    
    global_articles_filtered = [a for a in global_articles if is_bakery_related(a['title'], a['snippet'])]
    dropped = len(global_articles) - len(global_articles_filtered)
    print(f"    -> {len(global_articles_filtered)} kept, {dropped} dropped (not bakery-related)\n")
    
    if global_articles_filtered:
        entities = [
            {
                'trend_name': a['title'][:60],
                'sentiment': 'Neutral',
                'url': a['url'],
                'domain': a['domain'],
                'title': a['title']
            }
            for a in global_articles_filtered
        ]
        
        print("[5] Canonicalizing...")
        canonical = canonicalize_entities(entities)
        print(f"    -> {len(canonical)} unique trends\n")
        
        print("[6] Inserting to DB...")
        inserted = insert_daily_trends(canonical, origin="Global")
        print(f"    -> {inserted} trends inserted\n")
    
    # Analysis
    print("[7] Analyzing trends...")
    update_trend_status()
    
    # Report & Email
    print("[8] Generating report...")
    report_html = generate_report()
    
    print("[9] Sending email...")
    recipient = os.getenv("EMAIL_FROM")
    send_email(
        recipient=recipient,
        subject="BakeryTrendScout Daily Report",
        html_body=report_html
    )
    
    print(f"\n{'='*60}")
    print(f"Pipeline completed")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
