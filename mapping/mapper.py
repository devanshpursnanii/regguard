from __future__ import annotations

import json
from typing import Dict

import google.generativeai as genai

from config import GEMINI_API_KEY, GEMINI_MODEL, LLM_TEMPERATURE
from utils.llm_guard import cached_text_call


def score_mapping(reg_clause: str, company_text: str) -> Dict[str, str | float]:
    """Score a clause mapping using Gemini."""

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        GEMINI_MODEL,
        generation_config={"temperature": LLM_TEMPERATURE},
    )

    prompt = (
        "Assess whether the company policy text complies with the regulatory clause. "
        "Return JSON with keys: score (0-1), status (matched/partial/missing), rationale, "
        "matched_sentence, regulatory_sentence.\n\n"
        f"Regulatory clause: {reg_clause}\n\nCompany policy: {company_text}"
    )

    response_text = cached_text_call(
        "mapping_score",
        prompt,
        lambda: model.generate_content(prompt).text,
    )

    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        return {
            "score": 0.0,
            "status": "missing",
            "rationale": response_text.strip(),
            "matched_sentence": "",
            "regulatory_sentence": "",
        }

    return data
