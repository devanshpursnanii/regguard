from __future__ import annotations

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import CORS_ALLOW_ORIGINS, FROM_EMAIL, GEMINI_API_KEY, GEMINI_MODEL, LLM_TEMPERATURE
from export.email_sender import send_report_email
from export.pdf_generator import generate_report_pdf
from retrieval.simple_retrieve import retrieve
from utils.llm_guard import cached_text_call

app = FastAPI(title="RegGuard")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

MOCK_DIR = Path("mock_data")


class ChatRequest(BaseModel):
    company_id: str
    message: str


class RetrieveRequest(BaseModel):
    query: str
    top_k: int | None = None


class ReportRequest(BaseModel):
    company_id: str
    email: str


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Basic health check endpoint."""

    return {"status": "ok"}


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Missing mock data: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/companies")
async def get_companies() -> List[Dict[str, Any]]:
    """Return list of companies for the demo dashboard."""

    path = MOCK_DIR / "companies.json"
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/gap-matrix/{company_id}")
async def get_gap_matrix(company_id: str) -> Dict[str, Any]:
    """Return the precomputed gap matrix for a company."""

    return _read_json(MOCK_DIR / f"gap_matrix_{company_id}.json")


@app.get("/api/evidence/{company_id}")
async def get_evidence(company_id: str) -> Dict[str, Any]:
    """Return evidence pairs for a company."""

    return _read_json(MOCK_DIR / f"evidence_{company_id}.json")


@app.post("/api/retrieve")
async def retrieve_chunks(payload: RetrieveRequest) -> Dict[str, Any]:
    """Retrieve chunks using the real graph store and BM25."""

    results = retrieve(payload.query, payload.top_k)
    return {"results": results}


@app.post("/api/chat")
async def chat(payload: ChatRequest) -> Dict[str, Any]:
    """Answer a compliance question using Gemini with mock context."""

    gap_matrix = _read_json(MOCK_DIR / f"gap_matrix_{payload.company_id}.json")
    prompt_header = (MOCK_DIR / "chat_prompt.txt").read_text(encoding="utf-8")
    context = json.dumps(gap_matrix, indent=2)
    prompt = (
        f"{prompt_header}\n\n"
        "Gap matrix context:\n"
        f"{context}\n\n"
        f"User question: {payload.message}"
    )

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        GEMINI_MODEL,
        generation_config={"temperature": LLM_TEMPERATURE},
    )

    def _call() -> str:
        return model.generate_content(prompt).text

    response_text = cached_text_call("chat", prompt, _call)
    citations: List[str] = []
    for clause in gap_matrix.get("clauses", []):
        citation = clause.get("regulatory_citation")
        if citation and citation not in citations:
            citations.append(citation)

    if "[R" not in response_text and citations:
        response_text = f"{response_text}\n\nSources: {', '.join(citations[:2])}"

    return {"answer": response_text, "citations": citations[:4]}


@app.post("/api/report/generate")
async def generate_report(payload: ReportRequest) -> Dict[str, str]:
    """Generate a PDF report and email it to the user."""

    gap_matrix = _read_json(MOCK_DIR / f"gap_matrix_{payload.company_id}.json")
    output_path = Path("mock_data") / f"report_{payload.company_id}.pdf"
    generate_report_pdf(gap_matrix, output_path)
    send_report_email(
        FROM_EMAIL,
        payload.email,
        "RegGuard Compliance Report",
        "Your RegGuard compliance report is attached.",
        output_path,
    )
    return {"status": "sent"}
