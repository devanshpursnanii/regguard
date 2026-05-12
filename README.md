# RegGuard

Bare-bones notes for GitHub. This is a demo-style compliance intelligence app with a FastAPI backend, a React (Vite) frontend, and a Neo4j-backed retrieval pipeline. The UI uses mock data for most views, while some endpoints can hit the graph/ingestion stack.

## Product overview (how it works)
RegGuard is a compliance intelligence console for teams that need quick visibility into regulatory gaps, evidence links, and audit-ready outputs.

High-level flow:
1. Documents are ingested from PDFs (regulatory + company policy + precedent cases).
2. The ingestion pipeline extracts text, chunks it, embeds with Gemini, and stores chunks in Neo4j.
3. The UI presents a dashboard with company status, a gap matrix, evidence pairs, and a chat assistant.
4. Users can ask questions and generate a PDF report that is emailed to them.

## Detailed flow (what is happening and how)
### 1) Document ingestion and indexing
- PDFs are read from [data](data) and classified by folder (regulatory/company/precedents).
- Text is extracted per page using pdfplumber, with light cleanup (headers/footers removed).
- Pages are split into sentence-based chunks with overlap so context is preserved across boundaries.
- Each chunk is embedded using Gemini embeddings and stored in an in-memory Qdrant vector store.
- Metadata and chunk nodes are stored in Neo4j with citations and document references.
- For regulatory PDFs, clause extraction runs (Gemini with heuristic fallback) to create Clause nodes.

### 2) Retrieval and evidence
- The `/api/retrieve` endpoint queries Neo4j chunks and runs BM25 to rank chunks by relevance.
- Results return text + citation keys for traceability.
- This endpoint expects a populated Neo4j graph, which comes from the ingestion CLI.

### 3) Mock data-backed UX
- The dashboard, gap matrix, and evidence views are served from JSON in [mock_data](mock_data).
- This keeps the UI fast and deterministic without running the full pipeline.
- The mock gap matrices and evidence pairs simulate compliance scoring outputs.

### 4) Chat and reporting
- The chat endpoint loads the mock gap matrix for a company and builds a prompt.
- Gemini generates a response; citations are appended when not present in the model output.
- PDF reports are generated using WeasyPrint from an HTML template and emailed via Resend.

### 5) Frontend behavior
- React fetches data from the backend API base (configurable via `VITE_API_BASE`).
- Users can navigate from the dashboard to a company detail page.
- Gap matrix table and evidence panels are rendered from API responses.
- The chat drawer calls the chat and report endpoints.

## What works today (features)
- Dashboard + company drill-down UI backed by mock data (companies, gap matrix, evidence).
- Evidence view and gap matrix view per company (mock_data).
- Chat endpoint that uses Gemini + mock gap matrix context to answer questions.
- Retrieval endpoint that runs BM25 over Neo4j chunks (requires ingest + Neo4j running).
- PDF report generation via WeasyPrint and delivery via Resend.
- Dockerized backend, frontend, and Neo4j for local setup.

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
