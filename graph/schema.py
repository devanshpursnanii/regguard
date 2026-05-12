from __future__ import annotations

from typing import Iterable

from neo4j import Driver


CONSTRAINTS: Iterable[str] = (
    "CREATE CONSTRAINT regulation_id_unique IF NOT EXISTS FOR (n:RegulationDocument) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT company_id_unique IF NOT EXISTS FOR (n:CompanyDocument) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT precedent_id_unique IF NOT EXISTS FOR (n:PrecedentCase) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS FOR (n:Chunk) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT clause_id_unique IF NOT EXISTS FOR (n:Clause) REQUIRE n.id IS UNIQUE",
)

INDEXES: Iterable[str] = (
    "CREATE INDEX regulation_title_idx IF NOT EXISTS FOR (n:RegulationDocument) ON (n.title)",
    "CREATE INDEX regulation_date_idx IF NOT EXISTS FOR (n:RegulationDocument) ON (n.date)",
    "CREATE INDEX company_name_idx IF NOT EXISTS FOR (n:CompanyDocument) ON (n.company_name)",
    "CREATE INDEX precedent_date_idx IF NOT EXISTS FOR (n:PrecedentCase) ON (n.date)",
    "CREATE INDEX precedent_citation_idx IF NOT EXISTS FOR (n:PrecedentCase) ON (n.citation_key)",
    "CREATE INDEX chunk_doc_idx IF NOT EXISTS FOR (n:Chunk) ON (n.doc_id)",
    "CREATE INDEX chunk_citation_idx IF NOT EXISTS FOR (n:Chunk) ON (n.citation_key)",
    "CREATE INDEX clause_regulation_idx IF NOT EXISTS FOR (n:Clause) ON (n.regulation_id)",
    "CREATE INDEX clause_citation_idx IF NOT EXISTS FOR (n:Clause) ON (n.citation_key)",
)


def initialize_schema(driver: Driver) -> None:
    """Create Neo4j constraints and indexes if they do not already exist."""

    with driver.session() as session:
        for statement in CONSTRAINTS:
            session.run(statement)
        for statement in INDEXES:
            session.run(statement)
