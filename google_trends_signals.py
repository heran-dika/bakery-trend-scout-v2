import sqlite3
import time
from datetime import datetime
from pytrends.request import TrendReq

GEO = "ID"
TIMEFRAME = "today 3-m"
REQUEST_DELAY_SECONDS = 20
MAX_RETRIES = 1
RETRY_BACKOFF_SECONDS = 45

MIN_CONSISTENT_DAYS = 2
MIN_SCORE_THRESHOLD = 10  # [Menebak] belum dikalibrasi pakai data asli


def get_active_pending_entities():
    conn = sqlite3.connect("trends.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, trend_name FROM pending_entities")
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_already_checked_today(today: str) -> set:
    """pending_id yang udah punya row google_trends_signals di tanggal ini --
    di-skip biar re-run manual gak numpuk query pytrends yang gak perlu."""
    conn = sqlite3.connect("trends.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT pending_id FROM google_trends_signals WHERE date = ?", (today,))
    ids = {r[0] for r in cursor.fetchall()}
    conn.close()
    return ids


def fetch_single_keyword(pytrends, keyword):
    for attempt in range(MAX_RETRIES + 1):
        try:
            pytrends.build_payload([keyword], timeframe=TIMEFRAME, geo=GEO)
            df = pytrends.interest_over_time()
            return df, None
        except Exception as e:
            is_rate_limit = "429" in str(e) or "TooManyRequests" in type(e).__name__
            if is_rate_limit and attempt < MAX_RETRIES:
                print(f"  ... {keyword}: kena 429, tunggu {RETRY_BACKOFF_SECONDS}s lalu retry ({attempt + 1}/{MAX_RETRIES})")
                time.sleep(RETRY_BACKOFF_SECONDS)
                continue
            return None, e
    return None, None


def fetch_and_store_signals():
    """Ambil interest_over_time buat pending_entities aktif yang BELUM
    dicek hari ini. Gagal per-keyword di-skip, gak crash run."""
    entities = get_active_pending_entities()
    if not entities:
        print("  -> Tidak ada pending_entities aktif, skip Google Trends check")
        return

    today = datetime.now().date().isoformat()
    already_checked = get_already_checked_today(today)

    to_check = [(pid, kw) for pid, kw in entities if pid not in already_checked]
    skipped_count = len(entities) - len(to_check)

    if skipped_count > 0:
        print(f"  -> {skipped_count} entity sudah dicek hari ini, di-skip (idempotent)")

    if not to_check:
        print("  -> Semua pending_entities sudah dicek hari ini, tidak ada yang perlu di-query")
        return

    pytrends = TrendReq(hl="id-ID", tz=420)
    conn = sqlite3.connect("trends.db")
    cursor = conn.cursor()

    success_count = 0
    fail_count = 0

    for pending_id, keyword in to_check:
        df, error = fetch_single_keyword(pytrends, keyword)

        if error is not None:
            print(f"  x {keyword}: ERROR {type(error).__name__}: {error}")
            fail_count += 1
            time.sleep(REQUEST_DELAY_SECONDS)
            continue

        if df is None or df.empty:
            print(f"  ... {keyword}: response kosong (volume kemungkinan kecil)")
            fail_count += 1
            time.sleep(REQUEST_DELAY_SECONDS)
            continue

        non_partial = df[df["isPartial"] == False]
        if non_partial.empty:
            print(f"  ... {keyword}: semua baris partial, skip")
            fail_count += 1
            time.sleep(REQUEST_DELAY_SECONDS)
            continue

        latest_row = non_partial.iloc[-1]
        score = int(latest_row[keyword])

        cursor.execute("""
            INSERT OR REPLACE INTO google_trends_signals
            (pending_id, date, keyword, interest_score, is_partial)
            VALUES (?, ?, ?, ?, ?)
        """, (pending_id, today, keyword, score, 0))

        print(f"  OK {keyword}: interest_score={score}")
        success_count += 1
        time.sleep(REQUEST_DELAY_SECONDS)

    conn.commit()
    conn.close()
    print(f"  -> Selesai: {success_count} sukses, {fail_count} gagal/skip, {skipped_count} di-skip (sudah dicek)")


def is_consistent_signal(pending_id: int) -> dict:
    conn = sqlite3.connect("trends.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT date, interest_score FROM google_trends_signals
        WHERE pending_id = ?
        ORDER BY date DESC
        LIMIT 3
    """, (pending_id,))
    rows = cursor.fetchall()
    conn.close()

    qualifying = [r for r in rows if r[1] is not None and r[1] >= MIN_SCORE_THRESHOLD]

    return {
        "pending_id": pending_id,
        "days_checked": len(rows),
        "qualifying_days": len(qualifying),
        "is_consistent": len(qualifying) >= MIN_CONSISTENT_DAYS,
        "raw_scores": rows,
    }


if __name__ == "__main__":
    start = time.time()
    fetch_and_store_signals()
    elapsed = time.time() - start
    print(f"\n  (durasi total: {elapsed:.1f} detik)")

    conn = sqlite3.connect("trends.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT pending_id FROM google_trends_signals")
    ids = [r[0] for r in cursor.fetchall()]
    conn.close()

    print("\n=== Ringkasan konsistensi ===")
    for pid in ids:
        result = is_consistent_signal(pid)
        print(result)
