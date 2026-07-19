import difflib
from typing import List, Dict

def canonicalize_entities(entities: List[Dict]) -> List[Dict]:
    """Merge entitas dalam satu batch yang merujuk produk sama."""
    if not entities:
        return []
    
    normalized = []
    for entity in entities:
        norm_name = entity["trend_name"].lower().strip()
        normalized.append({
            **entity,
            "norm_name": norm_name
        })
    
    clusters = {}
    for entity in normalized:
        matched = False
        
        for cluster_key in clusters.keys():
            ratio = difflib.SequenceMatcher(None, entity["norm_name"], cluster_key).ratio()
            if ratio > 0.85:
                clusters[cluster_key].append(entity)
                matched = True
                break
        
        if not matched:
            clusters[entity["norm_name"]] = [entity]
    
    result = []
    for cluster_key, items in clusters.items():
        canonical = max(items, key=lambda x: len(x["trend_name"]))["trend_name"]
        unique_domains = set(item["domain"] for item in items)
        
        all_sources = []
        for item in items:
            all_sources.append({
                "url": item["url"],
                "domain": item["domain"],
                "title": item["title"],
            })
        
        result.append({
            "canonical_name": canonical,
            "mention_count": len(unique_domains),
            "sentiment": item.get("sentiment", "Neutral"),
            "sources": all_sources,
        })
    
    return result
