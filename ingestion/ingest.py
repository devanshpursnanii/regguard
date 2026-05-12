from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Iterable, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

import google.generativeai as genai
from neo4j import GraphDatabase

from config import (
    CITATION_REGULATORY,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    LLM_TEMPERATURE,
    NEO4J_PASSWORD,
    NEO4J_URI,
    NEO4J_USER,
    validate_config,
)
from graph.schema import initialize_schema
from ingestion.chunker import Chunk, build_raptor_summaries, chunk_document
from ingestion.embedder import EmbeddingStore
from ingestion.extractor import detect_document_type, extract_pdf
from mapping.clause_extractor import extract_clauses_from_pages
from utils.llm_guard import cached_text_call

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("regguard.ingestion")

DOC_METADATA: Dict[str, Dict[str, str]] = {
    "R1_digital_lending_directions_2025.pdf": {
        "id": "R1",
        "doc_type": "RegulationDocument",
        "title": "RBI Digital Lending Directions",
        "regulator": "RBI",
        "date": "2025-05",
        "version": "May 2025",
    },
    "R2_kyc_master_direction_2025.pdf": {
        "id": "R2",
        "doc_type": "RegulationDocument",
        "title": "RBI KYC Master Direction",
        "regulator": "RBI",
        "date": "2025-08",
        "version": "Aug 2025",
    },
    "C1_lendingkart_fpc_2025.pdf": {
        "id": "C1",
        "doc_type": "CompanyDocument",
        "company_name": "C1-Lendingkart",
        "doc_name": "Lendingkart Finance Fair Practices Code 2025",
        "doc_type_name": "Fair Practices Code",
        "date": "2025",
    },
    "C2_csb_fpc_2024.pdf": {
        "id": "C2",
        "doc_type": "CompanyDocument",
        "company_name": "C2-CSB",
        "doc_name": "CSB Bank Fair Practices Code",
        "doc_type_name": "Fair Practices Code",
        "date": "2024-11",
    },
    "P1_sappers_finance_penalty_2023.pdf": {
        "id": "P1",
        "doc_type": "PrecedentCase",
        "title": "RBI penalty order on Sappers Finance",
        "date": "2023-11",
        "citation_key": "[P1-Sappers, Nov 2023]",
    },
}


def _extract_precedent_fields(text: str) -> Dict[str, str | List[str]]:
    """Extract penalty amount and cited regulations from a precedent document."""

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        GEMINI_MODEL,
        generation_config={"temperature": LLM_TEMPERATURE},
    )

    prompt = (
        "Extract the penalty amount and regulation identifiers cited in the following RBI penalty order. "
        "Return JSON with keys: penalty_amount (string), regulation_ids (array of strings), summary (string).\n\n"
        f"{text}"
    )
    response_text = cached_text_call(
        "precedent",
        prompt,
        lambda: model.generate_content(prompt).text,
    )

    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        data = {
            "penalty_amount": "",
            "regulation_ids": [],
            "summary": response_text.strip(),
        }

    if "summary" not in data:
        data["summary"] = response_text.strip()

    return data


def _list_target_files(paths: Iterable[Path]) -> List[Path]:
    """Return only files that are part of the known corpus."""

    allowed_names = set(DOC_METADATA.keys())
    targets: List[Path] = []
    for path in paths:
        if path.is_file() and path.name in allowed_names:
            targets.append(path)
    return targets


def _neo4j_driver():
    """Create a Neo4j driver instance."""

    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def _reset_graph(driver) -> None:
    """Delete all nodes and relationships from Neo4j."""

    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")


def _upsert_document(session, meta: Dict[str, str], file_path: str, extra: Dict[str, str | List[str]] | None = None) -> None:
    """Upsert a document node based on its type."""

    doc_type = meta["doc_type"]
    if doc_type == "RegulationDocument":
        session.run(
            """
            MERGE (d:RegulationDocument {id: $id})
            SET d.title = $title,
                d.regulator = $regulator,
                d.date = $date,
                d.version = $version,
                d.file_path = $file_path
            """,
            id=meta["id"],
            title=meta["title"],
            regulator=meta["regulator"],
            date=meta["date"],
            version=meta["version"],
            file_path=file_path,
        )
        return

    if doc_type == "CompanyDocument":
        session.run(
            """
            MERGE (d:CompanyDocument {id: $id})
            SET d.company_name = $company_name,
                d.doc_type = $doc_type,
                d.file_path = $file_path
            """,
            id=meta["id"],
            company_name=meta["company_name"],
            doc_type=meta["doc_type_name"],
            file_path=file_path,
        )
        return

    if doc_type == "PrecedentCase":
        payload = {
            "id": meta["id"],
            "title": meta["title"],
            "date": meta["date"],
            "file_path": file_path,
            "citation_key": meta["citation_key"],
        }
        if extra:
            payload.update(extra)
        session.run(
            """
            MERGE (d:PrecedentCase {id: $id})
            SET d.title = $title,
                d.date = $date,
                d.file_path = $file_path,
                d.regulation_ids = $regulation_ids,
                d.penalty_amount = $penalty_amount,
                d.summary = $summary,
                d.citation_key = $citation_key
            """,
            **payload,
        )
        return

    raise ValueError(f"Unsupported document type: {doc_type}")


def _upsert_chunk(session, chunk: Chunk) -> None:
    """Upsert a Chunk node and BELONGS_TO relation."""

    session.run(
        """
        MERGE (c:Chunk {id: $id})
        SET c.text = $text,
            c.page_number = $page_number,
            c.embedding_id = $embedding_id,
            c.doc_id = $doc_id,
            c.summary_level = $summary_level,
            c.token_count = $token_count,
            c.citation_key = $citation_key
        """,
        id=chunk.id,
        text=chunk.text,
        page_number=chunk.page_number,
        embedding_id=chunk.embedding_id,
        doc_id=chunk.doc_id,
        summary_level=chunk.summary_level,
        token_count=chunk.token_count,
        citation_key=chunk.citation_key,
    )

    session.run(
        """
        MATCH (c:Chunk {id: $chunk_id})
        MATCH (d {id: $doc_id})
        MERGE (c)-[:BELONGS_TO]->(d)
        """,
        chunk_id=chunk.id,
        doc_id=chunk.doc_id,
    )


def _upsert_clause(session, clause: Dict[str, str], regulation_id: str) -> None:
    """Upsert a Clause node and BELONGS_TO relation."""

    clause_number = clause.get("clause_number", "").strip()
    clause_text = clause.get("text", "").strip()
    parent_section = clause.get("parent_section", "").strip()
    if not clause_number or not clause_text:
        return

    clause_id = f"{regulation_id}-{clause_number}"
    citation_key = CITATION_REGULATORY.format(
        regulation_id=regulation_id,
        clause_number=clause_number,
    )

    session.run(
        """
        MERGE (c:Clause {id: $id})
        SET c.clause_number = $clause_number,
            c.text = $text,
            c.parent_section = $parent_section,
            c.regulation_id = $regulation_id,
            c.citation_key = $citation_key
        """,
        id=clause_id,
        clause_number=clause_number,
        text=clause_text,
        parent_section=parent_section,
        regulation_id=regulation_id,
        citation_key=citation_key,
    )

    session.run(
        """
        MATCH (c:Clause {id: $clause_id})
        MATCH (d:RegulationDocument {id: $regulation_id})
        MERGE (c)-[:BELONGS_TO]->(d)
        """,
        clause_id=clause_id,
        regulation_id=regulation_id,
    )


def process_file(file_path: Path, store: EmbeddingStore, dry_run: bool, no_raptor: bool) -> None:
    """Process a single PDF file through the ingestion pipeline."""

    meta = DOC_METADATA[file_path.name].copy()
    detected_type = detect_document_type(str(file_path))
    if meta["doc_type"] != detected_type:
        raise ValueError(f"Doc type mismatch for {file_path.name}: {detected_type}")

    pages = extract_pdf(str(file_path))
    chunks = chunk_document(pages, meta)
    summary_chunks: List[Chunk] = []
    if not no_raptor:
        summary_chunks = build_raptor_summaries(chunks, meta)
    all_chunks = chunks + summary_chunks

    if dry_run:
        logger.info("Dry run: %s chunks created for %s", len(all_chunks), file_path.name)
        return

    embeddings, qdrant_ids = store.embed_and_store(
        texts=[chunk.text for chunk in all_chunks],
        metadatas=[
            {
                "doc_id": chunk.doc_id,
                "doc_type": chunk.doc_type,
                "page_number": chunk.page_number,
                "citation_key": chunk.citation_key,
            }
            for chunk in all_chunks
        ],
        ids=[chunk.id for chunk in all_chunks],
    )

    for chunk, _embedding, qdrant_id in zip(all_chunks, embeddings, qdrant_ids):
        chunk.embedding_id = qdrant_id

    extra: Dict[str, str | List[str]] | None = None
    if meta["doc_type"] == "PrecedentCase":
        excerpt = "\n".join(page["text"] for page in pages[:3])
        extra = _extract_precedent_fields(excerpt)

    clauses: List[Dict[str, str]] = []
    if meta["doc_type"] == "RegulationDocument":
        clauses = extract_clauses_from_pages(meta["id"], pages)

    with _neo4j_driver() as driver:
        initialize_schema(driver)
        with driver.session() as session:
            _upsert_document(session, meta, str(file_path), extra)
            for chunk in all_chunks:
                _upsert_chunk(session, chunk)
            for clause in clauses:
                _upsert_clause(session, clause, meta["id"])

    logger.info("Ingested %s with %s chunks", file_path.name, len(all_chunks))


def main() -> None:
    """CLI entrypoint for the ingestion pipeline."""

    parser = argparse.ArgumentParser(description="RegGuard ingestion pipeline")
    parser.add_argument("--file", type=str, help="Path to a single PDF file")
    parser.add_argument("--dir", type=str, help="Directory with PDF files")
    parser.add_argument("--dry-run", action="store_true", help="Run without writing to stores")
    parser.add_argument("--no-raptor", action="store_true", help="Skip RAPTOR summaries")
    parser.add_argument("--reset", action="store_true", help="Reset Neo4j graph before ingest")
    args = parser.parse_args()

    if not args.file and not args.dir:
        raise ValueError("Provide either --file or --dir")

    validate_config()

    store = EmbeddingStore()

    if args.reset and not args.dry_run:
        with _neo4j_driver() as driver:
            _reset_graph(driver)

    targets: List[Path] = []
    if args.file:
        targets = _list_target_files([Path(args.file)])
    if args.dir:
        dir_path = Path(args.dir)
        if not dir_path.exists():
            raise ValueError(f"Directory not found: {dir_path}")
        targets = _list_target_files(dir_path.glob("*.pdf"))

    if not targets:
        logger.warning("No valid corpus files found")
        return

    for file_path in targets:
        process_file(file_path, store, args.dry_run, args.no_raptor)


if __name__ == "__main__":
    main()
