# RegGuard

Bare-bones notes for GitHub. This is a demo-style compliance intelligence app with a FastAPI backend, a React (Vite) frontend, and a Neo4j-backed retrieval pipeline. The UI uses mock data for most views, while some endpoints can hit the graph/ingestion stack.

## What runs today (current wiring)
- Backend API: FastAPI app in [main.py](main.py)
- Frontend: React app in [frontend](frontend)
- Retrieval: BM25 over chunks stored in Neo4j via [retrieval/simple_retrieve.py](retrieval/simple_retrieve.py)
- PDF report generation: WeasyPrint in [export/pdf_generator.py](export/pdf_generator.py)
- Email delivery: Resend in [export/email_sender.py](export/email_sender.py)
- Ingestion pipeline: CLI in [ingest.py](ingest.py) -> [ingestion/ingest.py](ingestion/ingest.py)
- Docker runtime: [Dockerfile](Dockerfile), [frontend/Dockerfile](frontend/Dockerfile), [docker-compose.yml](docker-compose.yml)

## Quick start (Docker)
1. Copy .env.example to .env and fill required values.
2. Run `docker compose up --build`.
3. Frontend: http://localhost:8080
4. Backend: http://localhost:8000

## Quick start (local dev)
Backend:
- `python -m venv venv && source venv/bin/activate`
- `pip install -r requirements.txt`
- `uvicorn main:app --reload --host 0.0.0.0 --port 8000`

Frontend:
- `cd frontend`
- `npm install`
- `npm run dev`

## Environment variables
See [.env.example](.env.example) for the full list. Key ones:
- `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_EMBEDDING_MODEL`
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- `RESEND_API_KEY`, `FROM_EMAIL`
- `CORS_ALLOW_ORIGINS` (comma-separated)
- Retrieval and chunking: `TOP_K_RETRIEVAL`, `CHUNK_SIZE_TOKENS`, `CHUNK_OVERLAP_TOKENS`

## API surface (current)
From [main.py](main.py):
- `GET /health`
- `GET /api/companies` (mock_data)
- `GET /api/gap-matrix/{company_id}` (mock_data)
- `GET /api/evidence/{company_id}` (mock_data)
- `POST /api/retrieve` (Neo4j BM25 search)
- `POST /api/chat` (Gemini + mock_data context)
- `POST /api/report/generate` (WeasyPrint + Resend)

## Data and ingestion
- Source PDFs live in [data](data) with subfolders: company, precedents, regulatory.
- Ingestion CLI: `python ingest.py --dir data/regulatory` or `--file path/to/file.pdf`.
- Known document names are hard-coded in [ingestion/ingest.py](ingestion/ingest.py) under `DOC_METADATA`.
- The pipeline extracts PDF text (pdfplumber), chunks text, embeds with Gemini, stores vectors in in-memory Qdrant, and writes nodes to Neo4j.

## Frontend
- Vite + React in [frontend](frontend)
- Tailwind config: [frontend/tailwind.config.js](frontend/tailwind.config.js)
- API base: `VITE_API_BASE` (defaults to http://localhost:8000)

## Scripts
- Mock data refresh: [scripts/generate_mock_data.py](scripts/generate_mock_data.py)
- Graph sanity checks: [scripts/validate_graph.py](scripts/validate_graph.py)

## Not used or future scope (present but not wired)
- Mapping scoring utility in [mapping/mapper.py](mapping/mapper.py) is not called by the API or ingestion flow.
- Clause extractor in [mapping/clause_extractor.py](mapping/clause_extractor.py) is only used by ingestion for regulation docs.
- Rate limiter and summary cache utilities in [utils/rate_limiter.py](utils/rate_limiter.py) and [utils/summary_cache.py](utils/summary_cache.py) are not referenced; they also depend on env vars not defined in config.
- RAPTOR summarization paths in [ingestion/chunker.py](ingestion/chunker.py) are gated by env flags and are off by default.
- [scripts/generate_mock_data.py](scripts/generate_mock_data.py) references a `gap.engine` module that is not in this repo, so it falls back to existing mock data.

## Security notes
- Do not commit .env. It is excluded by [.gitignore](.gitignore).
- [sample.py](sample.py) contains a hard-coded API key and is not used by the app. Treat as unsafe and remove or replace before sharing.
