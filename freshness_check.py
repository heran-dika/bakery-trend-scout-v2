import re
import requests
from datetime import datetime, timedelta, timezone
from dateutil import parser as date_parser

MAX_AGE_DAYS = 14
REQUEST_TIMEOUT = 10

META_KEYS = ["article:published_time", "og:updated_time", "pubdate", "publishdate", "\"date\""]


def parse_date_string(raw: str):
    try:
        dt = date_parser.parse(raw)
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except (ValueError, OverflowError, TypeError):
        return None


def extract_publish_date(html_text: str):
    m = re.search(r'"datePublished"\s*:\s*"([^"]+)"', html_text)
    if m:
        parsed = parse_date_string(m.group(1))
        if parsed:
            return parsed

    meta_tags = re.findall(r'<meta[^>]+>', html_text, re.IGNORECASE)
    for tag in meta_tags:
        tag_lower = tag.lower()
        if any(key in tag_lower for key in META_KEYS):
            content_match = re.search(r'content=["\']([^"\']+)["\']', tag, re.IGNORECASE)
            if content_match:
                parsed = parse_date_string(content_match.group(1))
                if parsed:
                    return parsed
    return None


def check_freshness(url: str, max_age_days: int = MAX_AGE_DAYS) -> dict:
    """Return dict: is_stale (bool), published_date (str|None), date_verified (bool), error (str|None).
    Kalau tanggal gak ketemu ATAU fetch gagal -> date_verified=False, is_stale=False
    (diterima tapi ditandai gak terverifikasi, TIDAK otomatis ditolak)."""
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        return {"is_stale": False, "published_date": None, "date_verified": False, "error": f"{type(e).__name__}: {e}"}

    published = extract_publish_date(resp.text)
    if published is None:
        return {"is_stale": False, "published_date": None, "date_verified": False, "error": None}

    age = datetime.now() - published
    is_stale = age > timedelta(days=max_age_days)
    return {
        "is_stale": is_stale,
        "published_date": published.date().isoformat(),
        "date_verified": True,
        "error": None,
    }


if __name__ == "__main__":
    TEST_URLS = [
        ("Detik 2022 (harus stale)", "https://food.detik.com/info-kuliner/d-6474420/santuy-terendam-banjir-pemilik-kedai-ini-malah-sibuk-bikin-pesanan-roti-canai"),
        ("Brilio 2016 (harus stale)", "https://www.brilio.net/cowok/10-foto-gadis-cantik-penjual-roti-canai-yang-hebohkan-netizen-1610114.html"),
    ]
    for label, url in TEST_URLS:
        print(f"\n--- {label} ---")
        result = check_freshness(url)
        print(result)


def enrich_canonical_entities(canonical_entities):
    """Cek freshness tiap source di canonical_entities, nambah is_stale/
    published_date/date_verified langsung ke dict source-nya (in-place-ish,
    return list baru). Gagal per-URL gak crash -- check_freshness sudah
    handle exception internal dan balikin date_verified=False."""
    for entity in canonical_entities:
        for source in entity["sources"]:
            result = check_freshness(source["url"])
            source["is_stale"] = result["is_stale"]
            source["published_date"] = result["published_date"]
            source["date_verified"] = result["date_verified"]
            status = "STALE" if result["is_stale"] else ("fresh" if result["date_verified"] else "unverified")
            domain_label = source["domain"]
            date_label = f" ({result['published_date']})" if result["published_date"] else ""
            print(f"    [freshness] {domain_label}: {status}{date_label}")
    return canonical_entities
