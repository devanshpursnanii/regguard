from __future__ import annotations

import os
from typing import Final

from dotenv import load_dotenv

load_dotenv()

GEMINI_MODEL: Final[str] = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
GEMINI_EMBEDDING_MODEL: Final[str] = os.getenv("GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-2")
LLM_TEMPERATURE: Final[float] = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_MAX_RPM: Final[int] = int(os.getenv("LLM_MAX_RPM", "6"))
LLM_CACHE_DIR: Final[str] = os.getenv("LLM_CACHE_DIR", ".llm_cache")
RAPTOR_ENABLED: Final[bool] = os.getenv("RAPTOR_ENABLED", "false").lower() in {
    "1",
    "true",
    "yes",
}
RAPTOR_GROUP_SIZE: Final[int] = int(os.getenv("RAPTOR_GROUP_SIZE", "15"))
RAPTOR_ENABLE_DOC_SUMMARY: Final[bool] = os.getenv(
    "RAPTOR_ENABLE_DOC_SUMMARY", "false"
).lower() in {"1", "true", "yes"}

CHUNK_SIZE_TOKENS: Final[int] = int(os.getenv("CHUNK_SIZE_TOKENS", "400"))
CHUNK_OVERLAP_TOKENS: Final[int] = int(os.getenv("CHUNK_OVERLAP_TOKENS", "50"))
TOP_K_RETRIEVAL: Final[int] = int(os.getenv("TOP_K_RETRIEVAL", "8"))

BM25_WEIGHT: Final[float] = float(os.getenv("BM25_WEIGHT", "0.3"))
DENSE_WEIGHT: Final[float] = float(os.getenv("DENSE_WEIGHT", "0.5"))
GRAPH_WEIGHT: Final[float] = float(os.getenv("GRAPH_WEIGHT", "0.2"))

CONFIDENCE_THRESHOLD: Final[float] = float(os.getenv("CONFIDENCE_THRESHOLD", "0.4"))
PARTIAL_THRESHOLD: Final[float] = float(os.getenv("PARTIAL_THRESHOLD", "0.7"))
RAPTOR_LEVELS: Final[int] = int(os.getenv("RAPTOR_LEVELS", "3"))

NEO4J_URI: Final[str] = os.getenv("NEO4J_URI", "")
NEO4J_USER: Final[str] = os.getenv("NEO4J_USER", "")
NEO4J_PASSWORD: Final[str] = os.getenv("NEO4J_PASSWORD", "")

QDRANT_MODE: Final[str] = os.getenv("QDRANT_MODE", "in_memory")

RESEND_API_KEY: Final[str] = os.getenv("RESEND_API_KEY", "")
GEMINI_API_KEY: Final[str] = os.getenv("GEMINI_API_KEY", "")
FROM_EMAIL: Final[str] = os.getenv("FROM_EMAIL", "")


def _split_origins(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


CORS_ALLOW_ORIGINS: Final[list[str]] = _split_origins(
    os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5173")
)

CITATION_REGULATORY: Final[str] = os.getenv(
    "CITATION_REGULATORY",
    "[{regulation_id}, Clause {clause_number}]",
)
CITATION_COMPANY: Final[str] = os.getenv(
    "CITATION_COMPANY",
    "[{company_name}, p.{page_number}]",
)
CITATION_EVIDENCE: Final[str] = os.getenv(
    "CITATION_EVIDENCE",
    "{regulatory_citation} \u2194 {company_citation}",
)


def validate_config() -> None:
    """Validate required environment variables are present."""

    missing = []
    if not NEO4J_URI:
        missing.append("NEO4J_URI")
    if not NEO4J_USER:
        missing.append("NEO4J_USER")
    if not NEO4J_PASSWORD:
        missing.append("NEO4J_PASSWORD")
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    if not RESEND_API_KEY:
        missing.append("RESEND_API_KEY")
    if not FROM_EMAIL:
        missing.append("FROM_EMAIL")

    if missing:
        missing_str = ", ".join(missing)
        raise ValueError(f"Missing required environment variables: {missing_str}")
