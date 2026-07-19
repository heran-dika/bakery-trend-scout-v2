import sqlite3
import difflib
from datetime import datetime, timedelta
from typing import Dict

def get_distinct_trends() -> Dict[str, int]:
    """Ambil entitas unik dari hari sebelumnya."""
    conn = sqlite3.connect("trends.db")
    cursor = conn.cursor()
    
    yesterday = (datetime.now() - timedelta(days=1)).date()
    
    cursor.execute("""
        SELECT DISTINCT trend_name, mention_count 
        FROM daily_trends 
        WHERE date = ?
    """, (yesterday,))
    
    historical = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    
    return historical

def fuzzy_match(new_trend: str, historical_trends: list) -> tuple:
    """Match trend baru terhadap historical trends."""
    best_match = None
    best_ratio = 0.0
    
    for historical_trend in historical_trends:
        ratio = difflib.SequenceMatcher(None, new_trend.lower(), historical_trend.lower()).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = historical_trend
    
    return best_match, best_ratio

def determine_status(today_count: int, yesterday_count: int) -> str:
    """Tentukan status tren."""
    if yesterday_count == 0:
        return "Baru"
    
    change_pct = (today_count - yesterday_count) / yesterday_count
    
    if change_pct > 0.1:
        return "Naik"
    elif change_pct < -0.1:
        return "Turun"
    else:
        return "Stabil"

def update_trend_status():
    """Bandingkan trend hari ini vs kemarin."""
    conn = sqlite3.connect("trends.db")
    cursor = conn.cursor()
    
    today = datetime.now().date()
    
    cursor.execute("""
        SELECT id, trend_name, mention_count 
        FROM daily_trends 
        WHERE date = ?
    """, (today,))
    
    todays_trends = cursor.fetchall()
    
    historical = get_distinct_trends()
    
    print(f"Comparing {len(todays_trends)} trends today vs {len(historical)} historical")
    
    for trend_id, trend_name, mention_count in todays_trends:
        if historical:
            matched, ratio = fuzzy_match(trend_name, list(historical.keys()))
            
            if matched and ratio > 0.85:
                yesterday_count = historical[matched]
                status = determine_status(mention_count, yesterday_count)
                print(f"  Matched: {trend_name} -> {matched} (status: {status}, ratio: {ratio:.2f})")
            else:
                status = "Baru"
                print(f"  New: {trend_name} (status: Baru)")
        else:
            status = "Baru"
            print(f"  New (no historical): {trend_name}")
        
        cursor.execute("""
            UPDATE daily_trends 
            SET status = ? 
            WHERE id = ?
        """, (status, trend_id))
    
    conn.commit()
    conn.close()
    
    print("✓ Trend status updated")
