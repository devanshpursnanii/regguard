from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

import pdfplumber


def detect_document_type(file_path: str) -> str:
    """Detect document type from the directory path."""

    path = Path(file_path).as_posix()
    if "/regulatory/" in path:
        return "RegulationDocument"
    if "/company/" in path:
        return "CompanyDocument"
    if "/precedents/" in path:
        return "PrecedentCase"
    raise ValueError(f"Unable to detect document type from path: {file_path}")


def _clean_page_text(text: str) -> str:
    """Normalize whitespace and fix hyphenated line breaks."""

    fixed = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    fixed = fixed.replace("\u00a0", " ")
    fixed = re.sub(r"[ \t]+", " ", fixed)
    fixed = re.sub(r"\n{2,}", "\n", fixed)
    return fixed.strip()


def extract_pdf(file_path: str) -> List[Dict[str, str | int]]:
    """Extract text from a PDF into a list of page dictionaries."""

    pages: List[Dict[str, str | int]] = []
    with pdfplumber.open(file_path) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            raw_text = page.extract_text() or ""
            lines = raw_text.splitlines()
            cleaned_lines: List[str] = []
            for i, line in enumerate(lines):
                is_header = i < 3 and len(line.strip()) < 60
                is_footer = i >= max(len(lines) - 3, 0) and len(line.strip()) < 60
                if is_header or is_footer:
                    continue
                cleaned_lines.append(line)
            cleaned_text = _clean_page_text("\n".join(cleaned_lines))
            if cleaned_text:
                pages.append({"page_number": page_index, "text": cleaned_text})
    return pages
