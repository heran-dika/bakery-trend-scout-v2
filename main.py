import os
from datetime import datetime
from dotenv import load_dotenv

from tools_id_pulse import fetch_id_pulse_articles, DOMESTIC_KEYWORDS
from tools_global_scout import fetch_global_scout_articles, get_todays_country
from canonicalize import canonicalize_entities
from db_operations import insert_daily_trends
from agent_trend_analyst import update_trend_status
from agent_reporter import generate_report, send_email
from llm_fallback import call_llm_with_fallback

load_dotenv()

BAKERY_KEYWORDS = [
    "roti", "bread", "bakery", "donat", "donut", "cake", "kue",
    "pastry", "croissant", "brioche", "pan", "boulangerie",
    "떡", "パン", "خبز", "roll", "loaf", "dough", "adonan",
    "panggang", "oven", "tepung", "sourdough"
]

def is_bakery_related(title: str, snippet: str) -> bool:
    text = (title + " " + snippet).lower()
    return any(kw.lower() in text for kw in BAKERY_KEYWORDS)

def extract_trend_name(title: str, snippet: str) -> dict:
    """Extract trend_name via LLM dari title+snippet."""
    text = f"Title: {title}\nSnippet: {snippet}"
    prompt = f"""Extract the specific bakery product name mentioned. Return JSON only:
{{"product": "...", "type": "bread/cake/pastry/donut/other"}}

Article:
{text}"""
    
    result, layer = call_llm_with_fallback(prompt, response_type="json")
    
    if result and result.get("product"):
        return {
            "trend_name": result.get("product"),
            "sentiment": "Neutral",
            "llm_layer": layer
        }
    else:
        # Fallback ke title kalau LLM fail
        return {
            "trend_name": title[:60] if title else "Unknown",
            "sentiment": "Neutral",
            "llm_layer": "fallback_title"
        }

def main():
    print(f"\n{'='*60}")
    print(f"BakeryTrendScout Daily Run - {datetime.now().strftime('%Y-%m-%d')}")
    print(f"{'='*60}\n")
    
    # ID Pulse
    print("[1] Fetching ID Pulse...")
    id_articles = fetch_id_pulse_articles(DOMESTIC_KEYWORDS, max_results=5)
    print(f"    -> {len(id_articles)} articles fetched\n")
    
    id_articles_filtered = [a for a in id_articles if is_bakery_related(a['title'], a['snippet'])]
    print(f"    -> {len(id_articles_filtered)} kept (bakery-related)\n")
    
    if id_articles_filtered:
        print("[2] Extracting entities via LLM...")
        entities = []
        for a in id_articles_filtered:
            extracted = extract_trend_name(a['title'], a['snippet'])
            entities.append({
                'trend_name': extracted['trend_name'],
                'sentiment': extracted['sentiment'],
                'url': a['url'],
                'domain': a['domain'],
                'title': a['title']
            })
        print(f"    -> {len(entities)} entities extracted\n")
        
        print("[3] Canonicalizing...")
        canonical = canonicalize_entities(entities)
        print(f"    -> {len(canonical)} unique trends\n")
        
        print("[4] Inserting to DB...")
        inserted = insert_daily_trends(canonical, origin="Domestic")
        print(f"    -> {inserted} trends inserted\n")
    
    # Global Scout
    print("[5] Fetching Global Scout...")
    country, keyword = get_todays_country()
    global_articles = fetch_global_scout_articles(country, keyword, max_results=5)
    print(f"    -> {len(global_articles)} articles from {country}\n")
    
    global_articles_filtered = [a for a in global_articles if is_bakery_related(a['title'], a['snippet'])]
    print(f"    -> {len(global_articles_filtered)} kept (bakery-related)\n")
    
    if global_articles_filtered:
        print("[6] Extracting entities via LLM...")
        entities = []
        for a in global_articles_filtered:
            extracted = extract_trend_name(a['title'], a['snippet'])
            entities.append({
                'trend_name': extracted['trend_name'],
                'sentiment': extracted['sentiment'],
                'url': a['url'],
                'domain': a['domain'],
                'title': a['title']
            })
        print(f"    -> {len(entities)} entities extracted\n")
        
        print("[7] Canonicalizing...")
        canonical = canonicalize_entities(entities)
        print(f"    -> {len(canonical)} unique trends\n")
        
        print("[8] Inserting to DB...")
        inserted = insert_daily_trends(canonical, origin="Global")
        print(f"    -> {inserted} trends inserted\n")
    
    # Analysis
    print("[9] Analyzing trends...")
    update_trend_status()
    
    # Report & Email
    print("[10] Generating report...")
    report_html = generate_report()
    
    print("[11] Sending email...")
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
