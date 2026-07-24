import sqlite3
from datetime import datetime
from canonicalize import names_match
from typing import List, Dict

EXCLUDED_DOMAINS = [
    "wikipedia.org",
    "wikipedia.com",
    "etsy.com",
    "trendybakery.com",  # marketplace, sengaja di-exclude (confirmed Dika 2026-07-21)
    "shopee.co.id",
    "tokopedia.com",
    "bukalapak.com",
    "pinterest.com",
    "pinterest.co.id",
    "belowzero.co.id",  # distributor bahan baku, artikel undated soal peluang bisnis luar negeri, bukan sinyal tren (confirmed Dika 2026-07-21)
    "ytrecipe.com",  # affiliate site (jualan produk Amazon lewat konten masak YouTube), evergreen bukan sinyal tren (confirmed Dika 2026-07-22)
]

MIN_DISTINCT_DOMAINS = 2

def is_source_excluded(domain: str, url: str = "") -> bool:
    """True kalau domain di-exclude, ATAU domain tiktok.com tapi URL-nya
    BUKAN post individual (bukan /video/ atau /@username/) -- artinya
    halaman explore/hashtag/search generic, bukan konten spesifik."""
    domain_lower = domain.lower()

    if any(excluded in domain_lower for excluded in EXCLUDED_DOMAINS):
        return True

    if "tiktok.com" in domain_lower:
        url_lower = url.lower()
        is_individual_post = "/video/" in url_lower or "/@" in url_lower
        if not is_individual_post:
            return True

    return False

def insert_daily_trends(canonical_entities: List[Dict], origin: str = "Domestic") -> int:
    """Insert canonical entities ke daily_trends + trend_sources.
    mention_count = jumlah domain UNIK setelah exclusion filter (bukan sebelum,
    bukan raw jumlah sumber). Entity di-drop kalau distinct domain < MIN_DISTINCT_DOMAINS."""
    conn = sqlite3.connect("trends.db")
    cursor = conn.cursor()

    inserted_count = 0

    for entity in canonical_entities:
        valid_sources = [s for s in entity["sources"] if not is_source_excluded(s["domain"], s.get("url", ""))]

        if not valid_sources:
            print(f"  x Dropped (all sources excluded): {entity['canonical_name']}")
            continue

        distinct_domains = len(set(s["domain"] for s in valid_sources))

        if distinct_domains < MIN_DISTINCT_DOMAINS:
            print(f"  x Dropped (only {distinct_domains} distinct domain, need >= {MIN_DISTINCT_DOMAINS}): {entity['canonical_name']}")
            continue

        cursor.execute("""
            INSERT INTO daily_trends
            (date, trend_name, mention_count, status, trend_origin)
            VALUES (?, ?, ?, ?, ?)
        """, (
            datetime.now().date(),
            entity["canonical_name"],
            distinct_domains,
            "Baru",
            origin
        ))

        trend_id = cursor.lastrowid

        for source in valid_sources:
            cursor.execute("""
                INSERT INTO trend_sources
                (trend_id, url, domain, title, source_type, llm_layer_used)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                trend_id,
                source["url"],
                source["domain"],
                source["title"],
                classify_source_type(source["domain"]),
                "manual"
            ))

        inserted_count += 1
        print(f"  OK Inserted: {entity['canonical_name']} ({distinct_domains} distinct domains)")

    conn.commit()
    conn.close()

    return inserted_count

def delete_today_trends():
    """Hapus semua row daily_trends + trend_sources untuk tanggal hari ini.
    Dipanggil di awal tiap run biar run baru selalu overwrite run sebelumnya
    di tanggal yang sama (bukan numpuk)."""
    conn = sqlite3.connect("trends.db")
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM daily_trends WHERE date = date('now')")
    ids = [r[0] for r in cursor.fetchall()]

    if ids:
        cursor.executemany("DELETE FROM trend_sources WHERE trend_id = ?", [(i,) for i in ids])
        cursor.execute("DELETE FROM daily_trends WHERE date = date('now')")
        print(f"  -> Cleared {len(ids)} existing trend(s) for today before fresh run")

    conn.commit()
    conn.close()

def classify_source_type(domain: str) -> str:
    domain_lower = domain.lower()

    social_keywords = ["instagram", "tiktok", "twitter", "facebook", "reddit", "youtube"]
    media_keywords = ["news", "bbc", "reuters", "ap", "detik", "kompas", "blog", "medium"]

    for keyword in social_keywords:
        if keyword in domain_lower:
            return "social"

    for keyword in media_keywords:
        if keyword in domain_lower:
            return "media"

    return "unknown"


PENDING_EXPIRY_DAYS = 3


def expire_old_pending():
    """Hapus entity di pending_entities yang first_seen_date-nya lebih dari
    PENDING_EXPIRY_DAYS hari lalu dan belum lolos threshold. Dipanggil di
    awal tiap run, sebelum entity baru diproses."""
    conn = sqlite3.connect("trends.db")
    cursor = conn.cursor()

    cursor.execute(f"""
        SELECT id FROM pending_entities
        WHERE julianday('now') - julianday(first_seen_date) > {PENDING_EXPIRY_DAYS}
    """)
    expired_ids = [r[0] for r in cursor.fetchall()]

    if expired_ids:
        cursor.executemany("DELETE FROM pending_sources WHERE pending_id = ?", [(i,) for i in expired_ids])
        cursor.executemany("DELETE FROM pending_entities WHERE id = ?", [(i,) for i in expired_ids])
        print(f"  -> Expired {len(expired_ids)} pending entity(s) older than {PENDING_EXPIRY_DAYS} days")

    conn.commit()
    conn.close()


def process_entity_with_pending(canonical_entity: Dict, origin: str) -> str:
    """Proses satu canonical entity lewat alur pending (akumulasi cross-day).
    Return: 'inserted' kalau langsung promote ke daily_trends,
            'pending_new' kalau bikin pending baru,
            'pending_merged' kalau digabung ke pending yang sudah ada tapi belum lolos,
            'dropped' kalau semua source ke-exclude."""
    excluded_sources = [s for s in canonical_entity["sources"] if is_source_excluded(s["domain"], s.get("url", ""))]
    stale_sources = [s for s in canonical_entity["sources"] if not is_source_excluded(s["domain"], s.get("url", "")) and s.get("is_stale", False)]
    valid_sources = [s for s in canonical_entity["sources"] if not is_source_excluded(s["domain"], s.get("url", "")) and not s.get("is_stale", False)]

    if not valid_sources:
        reasons = []
        if excluded_sources:
            reasons.append(f"{len(excluded_sources)} excluded domain")
        if stale_sources:
            reasons.append(f"{len(stale_sources)} stale/basi")
        reason_str = ", ".join(reasons) if reasons else "unknown reason"
        print(f"  x Dropped ({reason_str}): {canonical_entity['canonical_name']}")
        return "dropped"

    conn = sqlite3.connect("trends.db")
    cursor = conn.cursor()

    cursor.execute("SELECT id, trend_name FROM pending_entities WHERE trend_origin = ?", (origin,))
    existing = cursor.fetchall()

    matched_id = None
    for pid, pname in existing:
        if names_match(canonical_entity["canonical_name"], pname):
            matched_id = pid
            break

    today = datetime.now().date()

    if matched_id is None:
        cursor.execute("""
            INSERT INTO pending_entities (trend_name, first_seen_date, last_seen_date, trend_origin)
            VALUES (?, ?, ?, ?)
        """, (canonical_entity["canonical_name"], today, today, origin))
        matched_id = cursor.lastrowid
        result_status = "pending_new"
    else:
        cursor.execute("UPDATE pending_entities SET last_seen_date = ? WHERE id = ?", (today, matched_id))
        result_status = "pending_merged"

    for source in valid_sources:
        cursor.execute("""
            INSERT INTO pending_sources (pending_id, url, domain, title, date_added, published_date, date_verified)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (matched_id, source["url"], source["domain"], source["title"], today,
              source.get("published_date"), int(source.get("date_verified", False))))

    cursor.execute("SELECT domain, url, title, published_date, date_verified FROM pending_sources WHERE pending_id = ?", (matched_id,))
    all_sources = cursor.fetchall()
    distinct_domains = len(set(s[0] for s in all_sources))

    if distinct_domains >= MIN_DISTINCT_DOMAINS:
        cursor.execute("""
            INSERT INTO daily_trends (date, trend_name, mention_count, status, trend_origin)
            VALUES (?, ?, ?, ?, ?)
        """, (today, canonical_entity["canonical_name"], distinct_domains, "Baru", origin))
        trend_id = cursor.lastrowid

        for domain, url, title, published_date, date_verified in all_sources:
            cursor.execute("""
                INSERT INTO trend_sources (trend_id, url, domain, title, source_type, llm_layer_used, published_date, date_verified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (trend_id, url, domain, title, classify_source_type(domain), "manual", published_date, date_verified))

        cursor.execute("DELETE FROM pending_sources WHERE pending_id = ?", (matched_id,))
        cursor.execute("DELETE FROM pending_entities WHERE id = ?", (matched_id,))

        print(f"  OK Promoted from pending: {canonical_entity['canonical_name']} ({distinct_domains} distinct domains)")
        conn.commit()
        conn.close()
        return "inserted"

    print(f"  ... Pending ({distinct_domains}/{MIN_DISTINCT_DOMAINS} domains so far): {canonical_entity['canonical_name']}")
    conn.commit()
    conn.close()
    return result_status
