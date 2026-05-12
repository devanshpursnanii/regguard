from __future__ import annotations

import json
import logging
import re
from typing import Dict, Iterable, List

import google.generativeai as genai

from config import GEMINI_API_KEY, GEMINI_MODEL, LLM_TEMPERATURE
from utils.llm_guard import cached_text_call

logger = logging.getLogger("regguard.clause_extractor")


def _heuristic_extract(text: str) -> List[Dict[str, str]]:
    """Fallback clause extraction using simple numbering heuristics."""

    clauses: List[Dict[str, str]] = []
    current: Dict[str, str] | None = None
    pattern = re.compile(r"^\s*(\d+(?:\.\d+)*)[\).:\-]?\s+(.*)$")

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = pattern.match(line)
        if match:
            clause_number = match.group(1)
            clause_text = match.group(2).strip()
            parent_section = clause_number.split(".")[0]
            current = {
                "clause_number": clause_number,
                "text": clause_text,
                "parent_section": parent_section,
            }
            clauses.append(current)
        elif current is not None:
            current["text"] = f"{current['text']} {line}".strip()

    return clauses


def _extract_with_llm(regulation_id: str, text: str, page_number: int) -> List[Dict[str, str]]:
    """Extract clauses from text using Gemini and fall back on heuristics."""

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        GEMINI_MODEL,
        generation_config={"temperature": LLM_TEMPERATURE},
    )

    prompt = (
        "Extract clauses from the following regulatory text. "
        "Return JSON array with keys: clause_number, text, parent_section.\n\n"
        f"Regulation: {regulation_id}\n"
        f"Page: {page_number}\n\n"
        f"{text}"
    )

    response_text = cached_text_call(
        f"clause_extract_p{page_number}",
        prompt,
        lambda: model.generate_content(prompt).text,
    )

    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        return _heuristic_extract(text)

    if not isinstance(data, list):
        return _heuristic_extract(text)

    items = [item for item in data if isinstance(item, dict)]
    return items if items else _heuristic_extract(text)


def extract_clauses_from_pages(
    regulation_id: str,
    pages: Iterable[Dict[str, str | int]],
) -> List[Dict[str, str]]:
    """Extract clauses from page text with caching and fallback heuristics."""

    clauses: List[Dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for page in pages:
        page_number = int(page.get("page_number", 0))
        page_text = str(page.get("text", "")).strip()
        if not page_text:
            continue
        page_clauses = _extract_with_llm(regulation_id, page_text, page_number)
        for clause in page_clauses:
            clause_number = clause.get("clause_number", "").strip()
            clause_text = clause.get("text", "").strip()
            if not clause_number or not clause_text:
                continue
            key = (clause_number, clause_text)
            if key in seen:
                continue
            seen.add(key)
            clauses.append(clause)

    if not clauses:
        logger.warning("No clauses extracted for %s", regulation_id)
    return clauses


def extract_clauses(regulation_id: str, text: str) -> List[Dict[str, str]]:
    """Extract clauses from regulatory text using Gemini."""

    pages = [{"page_number": 1, "text": text}]
    return extract_clauses_from_pages(regulation_id, pages)
