from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass

from .settings import CHUNKS_PATH


TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass
class SearchHit:
    score: float
    chunk: dict


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def load_chunks() -> list[dict]:
    if not CHUNKS_PATH.exists():
        raise FileNotFoundError("No index found. Run: python -m src.cli ingest")
    return json.loads(CHUNKS_PATH.read_text())


def expand_query(query: str) -> str:
    lowered = query.lower()
    additions: list[str] = []
    if any(term in lowered for term in ["trip", "trips", "tripped", "tackle", "challenge"]):
        additions.extend(["trips", "attempts", "trip", "fouls", "misconduct", "careless", "reckless"])
    if "penalty area" in lowered or "inside the box" in lowered or "box" in lowered:
        additions.extend(["penalty", "area", "direct", "free", "kick", "law", "12", "14"])
    if "handball" in lowered or "handles" in lowered or "hand" in lowered:
        additions.extend(["handball", "handles", "hand", "arm", "unnaturally", "bigger"])
    if "offside" in lowered:
        additions.extend(["offside", "position", "interfering", "opponent", "advantage"])
    return " ".join([query, *additions])


def metadata_boost(query: str, chunk: dict) -> float:
    lowered = query.lower()
    chunk_text = chunk.get("text", "").lower()
    law = chunk.get("law_number")
    boost = 0.0
    if any(term in lowered for term in ["trip", "trips", "tripped", "tackle", "challenge", "foul"]):
        if law == "12":
            boost += 5.0
        if "trips or attempts to trip" in chunk_text:
            boost += 12.0
        if "holding" in chunk_text and "hold" not in lowered:
            boost -= 5.0
    if "penalty area" in lowered or "inside the box" in lowered:
        if law == "14":
            boost += 8.0
        if law == "12":
            boost += 2.0
        if law in {"13", "15", "16", "17"}:
            boost -= 4.0
    if "penalty" in lowered and any(term in lowered for term in ["contact", "fall", "falls", "foul", "offence"]):
        if law == "12":
            boost += 8.0
        if law == "14":
            boost += 3.0
    if chunk.get("page", 0) >= 200 and law in {"11", "12", "14"}:
        boost -= 3.0
    if "offside" in lowered and law == "11":
        boost += 5.0
    return boost


def search(query: str, limit: int = 6) -> list[SearchHit]:
    chunks = load_chunks()
    docs = [tokenize(chunk["text"]) for chunk in chunks]
    expanded_query = expand_query(query)
    query_terms = tokenize(expanded_query)
    doc_count = len(docs)
    avg_len = sum(len(doc) for doc in docs) / max(doc_count, 1)
    doc_freq: Counter[str] = Counter()

    for doc in docs:
        for term in set(doc):
            doc_freq[term] += 1

    hits: list[SearchHit] = []
    k1 = 1.5
    b = 0.75

    for chunk, doc in zip(chunks, docs):
        tf = Counter(doc)
        score = 0.0
        doc_len = len(doc)
        for term in query_terms:
            if term not in tf:
                continue
            idf = math.log(1 + (doc_count - doc_freq[term] + 0.5) / (doc_freq[term] + 0.5))
            denom = tf[term] + k1 * (1 - b + b * doc_len / avg_len)
            score += idf * (tf[term] * (k1 + 1)) / denom
        score += metadata_boost(query, chunk)
        if score > 0:
            hits.append(SearchHit(score=score, chunk=chunk))

    return sorted(hits, key=lambda hit: hit.score, reverse=True)[:limit]
