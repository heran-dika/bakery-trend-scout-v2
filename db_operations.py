import sqlite3
from datetime import datetime
from typing import List, Dict

def insert_daily_trends(canonical_entities: List[Dict], origin: str = "Domestic") -> int:
    """Insert canonical entities ke daily_trends + trend_sources."""
    conn = sqlite3.connect("trends.db")
    cursor = conn.cursor()
    
    threshold_mention = 1  # Ubah dari 2 domain -> 1 mention saja
    inserted_count = 0
    
    for entity in canonical_entities:
        if entity["mention_count"] < threshold_mention:
            print(f"  ✗ Dropped: {entity['canonical_name']}")
            continue
        
        cursor.execute("""
            INSERT INTO daily_trends 
            (date, trend_name, mention_count, status, sentiment, trend_origin)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().date(),
            entity["canonical_name"],
            entity["mention_count"],
            "Baru",
            entity.get("sentiment", "Neutral"),
            origin
        ))
        
        trend_id = cursor.lastrowid
        
        for source in entity["sources"]:
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
        print(f"  ✓ Inserted: {entity['canonical_name']} ({entity['mention_count']} mentions)")
    
    conn.commit()
    conn.close()
    
    return inserted_count

def classify_source_type(domain: str) -> str:
    """Klasifikasi sumber berbasis rule."""
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
