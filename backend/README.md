# Fact Knowledge Layer — Backend

A FastAPI backend that extracts facts from PDFs, embeds them, and detects
cross-document relationships using Google Gemini.

## Quick Start

### 1. Prerequisites
- Python 3.11+
- A Google Gemini API key (https://aistudio.google.com/app/apikey)

### 2. Install dependencies
```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment
```bash
cp .env.example .env
# Edit .env and set GEMINI_API_KEY
```

### 4. Run the server
```bash
uvicorn main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

---

## Architecture

```
backend/
├── main.py            — FastAPI app, CORS, lifespan startup
├── database.py        — SQLAlchemy async engine, session factory
├── models.py          — ORM models: Document, Fact, Relationship
├── schemas.py         — Pydantic request/response models
├── pdf_parser.py      — PDF → PageChunk list (pdfplumber + PyMuPDF fallback)
├── fact_extractor.py  — LLM fact extraction (Gemini, per-page)
├── embeddings.py      — Gemini text embeddings + cosine similarity search
├── fact_comparator.py — LLM relationship classification (Gemini)
└── routes/
    ├── documents.py   — Upload, list, delete; background pipeline
    ├── facts.py       — List/get extracted facts
    └── relationships.py — List/get cross-document relationships
```

## Pipeline (per new document)

1. **Parse** — PDF split page-by-page; tables serialised to pipe-delimited rows.
2. **Extract** — Each page sent individually to Gemini for fact extraction.
3. **Embed** — Each fact embedded with `text-embedding-004`.
4. **Retrieve candidates** — Cosine similarity against all facts from OTHER documents.
5. **Classify** — Each candidate pair above threshold sent to Gemini for categorisation.
6. **Persist** — Facts and relationships stored in SQLite.

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Per-page LLM calls | Keeps context window small; works for 25–100 page docs |
| JSON `attributes` column | Flexible schema; new fact types need no migrations |
| Embeddings stored in SQLite as JSON | Zero infra; swap to pgvector for scale |
| Incremental processing | Only new documents are extracted; no re-processing |
| Tenacity retries | Handles transient Gemini API errors gracefully |

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | (required) | Google AI Studio API key |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Gemini model for extraction & comparison |
| `GEMINI_EMBEDDING_MODEL` | `models/text-embedding-004` | Embedding model |
| `EMBEDDING_SIMILARITY_THRESHOLD` | `0.75` | Min cosine score for candidate pairs |
| `UPLOAD_DIR` | `./uploads` | Directory for stored PDFs |
| `DATABASE_URL` | `sqlite+aiosqlite:///./fact_knowledge.db` | SQLAlchemy connection string |
