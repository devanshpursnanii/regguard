from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from neo4j import GraphDatabase

from config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER, validate_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("regguard.validate_graph")


def _print_counts(session) -> None:
    """Print node counts by label and MAPS_TO edge counts."""

    counts = session.run(
        """
        MATCH (n)
        RETURN labels(n) AS labels, count(n) AS count
        """
    )
    logger.info("Node counts by label:")
    for record in counts:
        logger.info("%s: %s", record["labels"], record["count"])

    edges = session.run(
        """
        MATCH ()-[r:MAPS_TO]->()
        RETURN count(r) AS count
        """
    ).single()
    logger.info("MAPS_TO edges: %s", edges["count"] if edges else 0)


def _print_sample_citations(session) -> None:
    """Print sample citation_key values per node type."""

    labels = ["Chunk", "Clause", "PrecedentCase"]
    for label in labels:
        result = session.run(
            f"MATCH (n:{label}) WHERE n.citation_key IS NOT NULL RETURN n.citation_key AS citation LIMIT 3"
        )
        citations = [record["citation"] for record in result]
        logger.info("%s citations: %s", label, citations)


def main() -> None:
    """Validate graph contents with counts and citation samples."""

    validate_config()
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        _print_counts(session)
        _print_sample_citations(session)
    driver.close()


if __name__ == "__main__":
    main()
