from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, List

import nltk
import google.generativeai as genai

from config import (
    CHUNK_OVERLAP_TOKENS,
    CHUNK_SIZE_TOKENS,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    LLM_TEMPERATURE,
    RAPTOR_ENABLED,
    RAPTOR_ENABLE_DOC_SUMMARY,
    RAPTOR_GROUP_SIZE,
)
from utils.llm_guard import cached_text_call


@dataclass
class Chunk:
    """In-memory representation of a document chunk."""

    id: str
    text: str
    page_number: int
    embedding_id: str | None
    doc_id: str
    doc_type: str
    summary_level: str
    token_count: int
    citation_key: str


def _ensure_nltk() -> None:
    """Ensure sentence tokenizer is available."""

    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        nltk.download("punkt")


def _estimate_tokens(text: str) -> int:
    """Estimate token count using whitespace as a proxy."""

    return max(1, len(text.split()))


def _citation_for_chunk(doc_meta: Dict[str, str], page_number: int) -> str:
    """Create a citation key for a chunk based on document type."""

    doc_type = doc_meta["doc_type"]
    if doc_type == "RegulationDocument":
        return f"[{doc_meta['id']}, p.{page_number}]"
    if doc_type == "CompanyDocument":
        return f"[{doc_meta['company_name']}, p.{page_number}]"
    if doc_type == "PrecedentCase":
        return doc_meta.get("citation_key", f"[{doc_meta['id']}]"
        )
    raise ValueError(f"Unsupported doc type for citation: {doc_type}")


def chunk_document(pages: List[Dict[str, str | int]], doc_meta: Dict[str, str]) -> List[Chunk]:
    """Chunk a document at sentence boundaries with overlap."""

    _ensure_nltk()
    chunks: List[Chunk] = []
    for page in pages:
        page_number = int(page["page_number"])
        sentences = nltk.sent_tokenize(str(page["text"]))
        current: List[str] = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = _estimate_tokens(sentence)
            if current_tokens + sentence_tokens > CHUNK_SIZE_TOKENS and current:
                chunk_text = " ".join(current).strip()
                chunk_id = f"{doc_meta['id']}-p{page_number}-c{len(chunks) + 1}"
                chunks.append(
                    Chunk(
                        id=chunk_id,
                        text=chunk_text,
                        page_number=page_number,
                        embedding_id=None,
                        doc_id=doc_meta["id"],
                        doc_type=doc_meta["doc_type"],
                        summary_level="base",
                        token_count=_estimate_tokens(chunk_text),
                        citation_key=_citation_for_chunk(doc_meta, page_number),
                    )
                )
                overlap_tokens = 0
                overlap_sentences: List[str] = []
                for overlap_sentence in reversed(current):
                    overlap_tokens += _estimate_tokens(overlap_sentence)
                    overlap_sentences.insert(0, overlap_sentence)
                    if overlap_tokens >= CHUNK_OVERLAP_TOKENS:
                        break
                current = overlap_sentences
                current_tokens = overlap_tokens

            current.append(sentence)
            current_tokens += sentence_tokens

        if current:
            chunk_text = " ".join(current).strip()
            chunk_id = f"{doc_meta['id']}-p{page_number}-c{len(chunks) + 1}"
            chunks.append(
                Chunk(
                    id=chunk_id,
                    text=chunk_text,
                    page_number=page_number,
                    embedding_id=None,
                    doc_id=doc_meta["id"],
                    doc_type=doc_meta["doc_type"],
                    summary_level="base",
                    token_count=_estimate_tokens(chunk_text),
                    citation_key=_citation_for_chunk(doc_meta, page_number),
                )
            )

    return chunks


def _summarize_group(model: genai.GenerativeModel, texts: Iterable[str]) -> str:
    """Summarize a group of chunk texts into a concise paragraph."""

    prompt = (
        "Summarize the following compliance text into a concise paragraph. "
        "Focus on obligations, prohibitions, and reporting requirements.\n\n"
        + "\n\n".join(texts)
    )
    return cached_text_call(
        "summary",
        prompt,
        lambda: model.generate_content(prompt).text.strip(),
    )


def build_raptor_summaries(chunks: List[Chunk], doc_meta: Dict[str, str]) -> List[Chunk]:
    """Create section and document summaries using Gemini."""

    if not RAPTOR_ENABLED:
        return []
    if not chunks:
        return []

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        GEMINI_MODEL,
        generation_config={"temperature": LLM_TEMPERATURE},
    )

    summaries: List[Chunk] = []
    group_size = RAPTOR_GROUP_SIZE
    for group_index in range(0, len(chunks), group_size):
        group = chunks[group_index : group_index + group_size]
        summary_text = _summarize_group(model, [chunk.text for chunk in group])
        page_number = group[0].page_number
        summary_id = f"{doc_meta['id']}-section-{math.floor(group_index / group_size) + 1}"
        summaries.append(
            Chunk(
                id=summary_id,
                text=summary_text,
                page_number=page_number,
                embedding_id=None,
                doc_id=doc_meta["id"],
                doc_type=doc_meta["doc_type"],
                summary_level="section",
                token_count=_estimate_tokens(summary_text),
                citation_key=_citation_for_chunk(doc_meta, page_number),
            )
        )

    if RAPTOR_ENABLE_DOC_SUMMARY:
        document_text = _summarize_group(model, [chunk.text for chunk in chunks])
        doc_summary_id = f"{doc_meta['id']}-document-summary"
        summaries.append(
            Chunk(
                id=doc_summary_id,
                text=document_text,
                page_number=1,
                embedding_id=None,
                doc_id=doc_meta["id"],
                doc_type=doc_meta["doc_type"],
                summary_level="document",
                token_count=_estimate_tokens(document_text),
                citation_key=_citation_for_chunk(doc_meta, 1),
            )
        )

    return summaries
