import difflib
from typing import List, Dict

MATCH_THRESHOLD = 0.85


def normalize_name(name: str) -> str:
    """Normalisasi nama produk buat matching (lowercase + strip).
    Dipakai konsisten untuk intra-day dedup (canonicalize_entities) dan
    cross-day matching (pending_entities di db_operations.py) -- JANGAN
    duplikat logic ini di tempat lain."""
    return name.lower().strip()


def names_match(name_a: str, name_b: str, threshold: float = MATCH_THRESHOLD) -> bool:
    """True kalau dua nama produk (sudah/belum dinormalisasi) dianggap
    merujuk entity yang sama. Reusable untuk intra-day dan cross-day."""
    ratio = difflib.SequenceMatcher(None, normalize_name(name_a), normalize_name(name_b)).ratio()
    return ratio > threshold


def canonicalize_entities(entities: List[Dict]) -> List[Dict]:
    """Merge entitas dalam satu batch yang merujuk produk sama."""
    if not entities:
        return []

    normalized = []
    for entity in entities:
        normalized.append({
            **entity,
            "norm_name": normalize_name(entity["trend_name"])
        })

    clusters = {}
    for entity in normalized:
        matched = False

        for cluster_key in clusters.keys():
            if names_match(entity["norm_name"], cluster_key):
                clusters[cluster_key].append(entity)
                matched = True
                break

        if not matched:
            clusters[entity["norm_name"]] = [entity]

    result = []
    for cluster_key, items in clusters.items():
        canonical = max(items, key=lambda x: len(x["trend_name"]))["trend_name"]

        all_sources = []
        for item in items:
            all_sources.append({
                "url": item["url"],
                "domain": item["domain"],
                "title": item["title"],
            })

        result.append({
            "canonical_name": canonical,
            "sources": all_sources,
        })

    return result
