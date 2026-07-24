import os
import re
import logging
from datetime import datetime
from typing import Optional, Literal
from dotenv import load_dotenv
from pydantic import BaseModel

from tools_id_pulse import fetch_id_pulse_articles, DOMESTIC_KEYWORDS
from tools_global_scout import fetch_global_scout_articles, get_todays_country
from canonicalize import canonicalize_entities
from db_operations import insert_daily_trends, delete_today_trends, process_entity_with_pending, expire_old_pending
from freshness_check import enrich_canonical_entities
from agent_trend_analyst import update_trend_status
from agent_reporter import generate_report, send_email
from llm_fallback import call_llm_with_fallback
from google_trends_signals import fetch_and_store_signals

load_dotenv()

logging.basicConfig(
    filename="pipeline_debug.log",
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    encoding="utf-8"
)

BAKERY_KEYWORDS = [
    "roti", "bread", "bakery", "donat", "donut", "cake", "kue",
    "pastry", "croissant", "brioche", "pan", "boulangerie",
    "떡", "パン", "خبز",
    "roll", "loaf", "dough", "adonan",
    "panggang", "oven", "tepung", "sourdough"
]

_ASCII_KEYWORDS = [kw for kw in BAKERY_KEYWORDS if kw.isascii()]
_NON_ASCII_KEYWORDS = [kw for kw in BAKERY_KEYWORDS if not kw.isascii()]
_ASCII_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(kw) for kw in _ASCII_KEYWORDS) + r")\b",
    re.IGNORECASE
)

def is_bakery_related(title: str, snippet: str) -> bool:
    text = title + " " + snippet
    if _ASCII_PATTERN.search(text):
        return True
    text_lower = text.lower()
    return any(kw in text_lower for kw in _NON_ASCII_KEYWORDS)

class ExtractedProduct(BaseModel):
    product: Optional[str] = None
    type: Optional[Literal["bread", "cake", "pastry", "donut", "other"]] = None

def extract_trend_name(title: str, snippet: str):
    """Extract trend_name via LLM dari title+snippet.
    Return None kalau LLM gagal total ATAU artikel cuma bahas kategori/tren
    umum tanpa nama produk spesifik (product: null) -- entitas ini di-skip,
    TIDAK fallback ke title (fallback ke title = pola kegagalan v1)."""
    text = f"Title: {title}\nSnippet: {snippet}"
    prompt = f"""Extract the specific bakery product name mentioned, if any.

Return JSON only: {{"product": "...", "type": "bread/cake/pastry/donut/other"}}

Rules:
- "product" harus nama produk/varian/brand SPESIFIK (contoh: "Roti Kukus Srikaya", "Donat Kentang Ubi", "Salt Bread Thailand").
- Kalau artikel cuma bahas kategori/tren secara umum tanpa nyebut nama produk/varian/brand spesifik (misal listicle "Sembilan Tren Donat 2026", ringkasan pasar, ranking umum), kembalikan "product": null.
- JANGAN pakai kategori/kata kunci pencarian sebagai nama produk.

Article:
{text}"""

    result, layer = call_llm_with_fallback(prompt, response_schema=ExtractedProduct)

    if result and result.get("product"):
        return {
            'trend_name': result.get("product"),
            'llm_layer': layer
        }
    return None

def fetch_and_filter(fetch_fn, *args, **kwargs):
    articles = fetch_fn(*args, **kwargs)
    kept = []
    for a in articles:
        is_kept = is_bakery_related(a['title'], a['snippet'])
        logging.info(
            f"[FILTER {'KEEP' if is_kept else 'DROP'}] domain={a['domain']} "
            f"title={a['title']!r} snippet={a['snippet'][:150]!r}"
        )
        if is_kept:
            kept.append(a)
    return articles, kept

def build_entities(articles):
    """Ekstrak + skip entitas yang gagal/generic. Log tiap skip biar keliatan alasannya.
    Jeda kecil antar panggilan LLM -- proteksi RPM selama angka pastinya belum diverifikasi."""
    import time
    entities = []
    for i, a in enumerate(articles):
        if i > 0:
            time.sleep(1.5)
        extracted = extract_trend_name(a['title'], a['snippet'])
        if extracted is None:
            logging.info(f"[EXTRACT SKIP] title={a['title']!r} (LLM gagal atau product generic/null)")
            continue
        entities.append({
            'trend_name': extracted['trend_name'],
            'url': a['url'],
            'domain': a['domain'],
            'title': a['title']
        })
    return entities

def main():
    print(f"\n{'='*60}")
    print(f"BakeryTrendScout Daily Run - {datetime.now().strftime('%Y-%m-%d')}")
    print(f"{'='*60}\n")
    logging.info(f"=== RUN START {datetime.now().isoformat()} ===")

    print("[0] Clearing today's existing data (if any)...")
    delete_today_trends()

    print("[0b] Expiring stale pending entities...")
    expire_old_pending()

    print("[1] Fetching ID Pulse...")
    id_articles, id_articles_filtered = fetch_and_filter(fetch_id_pulse_articles, DOMESTIC_KEYWORDS, max_results=10)
    print(f"    -> {len(id_articles)} articles fetched\n")
    print(f"    -> {len(id_articles_filtered)} kept (bakery-related)\n")

    if id_articles_filtered:
        print("[2] Extracting entities via LLM...")
        entities = build_entities(id_articles_filtered)
        print(f"    -> {len(entities)} entities extracted\n")

        if entities:
            print("[3] Canonicalizing...")
            canonical = canonicalize_entities(entities)
            print(f"    -> {len(canonical)} unique trends\n")

            print("[3b] Checking source freshness (best-effort)...")
            canonical = enrich_canonical_entities(canonical)

            print("[4] Inserting to DB (via pending accumulation)...")
            counts = {"inserted": 0, "pending_new": 0, "pending_merged": 0, "dropped": 0}
            for entity in canonical:
                status = process_entity_with_pending(entity, origin="Domestic")
                counts[status] += 1
            print(f"    -> {counts['inserted']} promoted, {counts['pending_new']} new pending, "
                  f"{counts['pending_merged']} merged into pending, {counts['dropped']} dropped\n")

    print("[5] Fetching Global Scout...")
    country_info = get_todays_country()
    if country_info is None:
        print("    -> Weekend, tidak ada negara terjadwal, skip Global Scout\n")
        global_articles_filtered = []
    else:
        country, keyword, region = country_info
        global_articles, global_articles_filtered = fetch_and_filter(fetch_global_scout_articles, country, keyword, region, max_results=10)
        print(f"    -> {len(global_articles)} articles from {country}\n")
        print(f"    -> {len(global_articles_filtered)} kept (bakery-related)\n")

    if global_articles_filtered:
        print("[6] Extracting entities via LLM...")
        entities = build_entities(global_articles_filtered)
        print(f"    -> {len(entities)} entities extracted\n")

        if entities:
            print("[7] Canonicalizing...")
            canonical = canonicalize_entities(entities)
            print(f"    -> {len(canonical)} unique trends\n")

            print("[7b] Checking source freshness (best-effort)...")
            canonical = enrich_canonical_entities(canonical)

            print("[8] Inserting to DB (via pending accumulation)...")
            counts = {"inserted": 0, "pending_new": 0, "pending_merged": 0, "dropped": 0}
            for entity in canonical:
                status = process_entity_with_pending(entity, origin="Global")
                counts[status] += 1
            print(f"    -> {counts['inserted']} promoted, {counts['pending_new']} new pending, "
                  f"{counts['pending_merged']} merged into pending, {counts['dropped']} dropped\n")

    print("[8b] Checking Google Trends signals (best-effort, non-blocking)...")
    try:
        fetch_and_store_signals()
    except Exception as e:
        print(f"    -> Google Trends check failed, skipping: {type(e).__name__}: {e}")
        logging.info(f"[GOOGLE_TRENDS_FAIL] {type(e).__name__}: {e}")

    print("[9] Analyzing trends...")
    update_trend_status()

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
    logging.info(f"=== RUN END {datetime.now().isoformat()} ===")

if __name__ == "__main__":
    main()
