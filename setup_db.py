import sqlite3
from pathlib import Path

db_path = Path("trends.db")
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS daily_trends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    trend_name TEXT NOT NULL,
    mention_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'Baru',
    sentiment TEXT,
    trend_origin TEXT,
    source_country TEXT,
    first_seen_global_date DATE,
    localization_status TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS trend_recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trend_name TEXT NOT NULL UNIQUE,
    raw_dough_formula TEXT,
    baking_process TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS global_scan_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    country TEXT NOT NULL,
    status TEXT,
    query_count INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS trend_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trend_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    domain TEXT,
    title TEXT,
    source_type TEXT,
    llm_layer_used TEXT,
    FOREIGN KEY (trend_id) REFERENCES daily_trends(id)
)
""")

conn.commit()
conn.close()
print("✓ Database initialized: trends.db")
