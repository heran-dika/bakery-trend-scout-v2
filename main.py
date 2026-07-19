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

def main():
    print(f"\n{'='*60}")
    print(f"BakeryTrendScout Daily Run - {datetime.now().strftime('%Y-%m-%d')}")
    print(f"{'='*60}\n")
    
    # ID Pulse
    print("[1] Fetching ID Pulse...")
    id_articles = fetch_id_pulse_articles(DOMESTIC_KEYWORDS, max_results=5)
    print(f"    -> {len(id_articles)} articles\n")
    
    if id_articles:
        entities = [
            {
                'trend_name': a['title'][:60],
                'sentiment': 'Neutral',
                'url': a['url'],
                'domain': a['domain'],
                'title': a['title']
            }
            for a in id_articles
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
    print(f"    -> {len(global_articles)} articles from {country}\n")
    
    if global_articles:
        entities = [
            {
                'trend_name': a['title'][:60],
                'sentiment': 'Neutral',
                'url': a['url'],
                'domain': a['domain'],
                'title': a['title']
            }
            for a in global_articles
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
        subject="🍞 BakeryTrendScout Daily Report",
        html_body=report_html
    )
    
    print(f"\n{'='*60}")
    print(f"✓ Pipeline completed")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
