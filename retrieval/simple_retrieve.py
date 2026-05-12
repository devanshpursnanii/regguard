from __future__ import annotations

from typing import Dict, List

from neo4j import GraphDatabase
from rank_bm25 import BM25Okapi

from config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER, TOP_K_RETRIEVAL


def _fetch_chunks(limit: int = 500) -> List[Dict[str, str]]:
    """Fetch chunk text and citations from Neo4j."""

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        result = session.run(
            """
            MATCH (c:Chunk)
            RETURN c.text AS text, c.citation_key AS citation
            LIMIT $limit
            """,
            limit=limit,
        )
        rows = [
            {"text": record["text"], "citation": record["citation"]}
            for record in result
        ]
    driver.close()
    return rows


def retrieve(query: str, top_k: int | None = None) -> List[Dict[str, str]]:
    """Retrieve top-k chunks using BM25 keyword scoring."""

    top_k = top_k or TOP_K_RETRIEVAL
    rows = _fetch_chunks()
    if not rows:
        return []

    corpus = [row["text"] for row in rows]
    tokenized = [doc.split() for doc in corpus]
    bm25 = BM25Okapi(tokenized)
    scores = bm25.get_scores(query.split())

    ranked = sorted(
        zip(rows, scores),
        key=lambda item: item[1],
        reverse=True,
    )

    results: List[Dict[str, str]] = []
    for row, score in ranked[:top_k]:
        results.append(
            {
                "text": row["text"],
                "citation_key": row["citation"],
                "score": float(score),
            }
        )

    return results
