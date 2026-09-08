# Fact Knowledge Layer

A system that extracts factual claims from PDF documents, grounds each fact in
its source evidence (exact quote + page number), and identifies relationships
between facts across documents — corroboration, contradiction, or an apparent
contradiction explained by context (time period, data vintage, scope, or units).

Built for the Superjoin Engineering Intern hiring assignment.

---

## Setup and Run Instructions

### Prerequisites
- Python 3.11+
- Node.js 18+
- A Google Gemini API key ([get one here](https://aistudio.google.com/app/apikey))

### Backend

```sh
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Open .env and set GEMINI_API_KEY=your_actual_key

uvicorn main:app --reload --port 8000
```

The API is now live at `http://localhost:8000` (interactive docs at `/docs`).

### Frontend

```sh
npm install
npm run dev
```

Opens at `http://localhost:5173` and talks to the backend at
`http://localhost:8000` by default. To point it elsewhere, set
`VITE_API_BASE_URL` in a `.env` file at the project root.

### Using it
1. Open the app, go to the Upload page, and upload a PDF.
2. Processing (parsing → extraction → embedding → comparison) runs in the
   background; the Upload page polls and shows live status.
3. Browse extracted facts (with source quote + page number) on the Facts page.
4. Browse detected relationships, filterable by category, on the
   Relationships page — each one includes the model's reasoning.
5. Upload additional PDFs to the same running instance — new facts are
   compared against everything already in the database (incremental, no
   reprocessing of earlier documents).

---

## Video Demo

*[Add your demo video link here — ≤3 minutes, showing a PDF being processed
and all four required cases below]*

---

## Approach

**Pipeline:** PDF → per-page text/table extraction (`pdfplumber`, falling back
to `PyMuPDF` on parse failure) → each page sent to Gemini with a strict
JSON-only extraction prompt → each extracted fact embedded
(`text-embedding-004`) → cosine similarity against all previously stored facts
finds candidate related pairs → each candidate pair sent to Gemini a second
time with a separate classification prompt that labels the relationship as
`corroboration`, `contradiction`, or `context_explained` with a short
explanation.

**Why two separate LLM calls instead of one:** extraction and comparison are
different tasks with different failure modes. Keeping them separate makes
each prompt simpler and each output easier to validate independently, and
lets the comparison step run only on the (much smaller) set of candidate
pairs rather than doing an expensive all-pairs comparison across every fact
ever stored.

**Why embeddings before LLM comparison:** comparing every new fact against
every existing fact with an LLM call would not scale (grows quadratically
with corpus size). Embedding similarity is a cheap first filter — only pairs
above a similarity threshold (`EMBEDDING_SIMILARITY_THRESHOLD`, default
`0.75`) go to the more expensive classification step.

**Schema:** facts are stored with a fixed core (claim, entities, numbers,
time period, page number, source quote) plus a JSON `attributes` column for
anything document-specific — so the system doesn't need a schema migration
to handle a new kind of fact in an unseen document.

**Grounding:** every fact stores the exact source quote and page number it
was extracted from, so every claim in the UI can be traced back to the PDF.

**Generalization:** the extraction and comparison prompts contain no
document-specific vocabulary, filenames, or hardcoded fact types — they were
tested against two structurally different starter datasets (company
financial filings and macroeconomic institutional reports) without any
per-dataset logic.

### AI tools used
- **Onspace** — scaffolded the initial full-stack implementation (FastAPI
  backend + React frontend) from a detailed specification.
- **Claude** — reviewed the generated code, found and fixed three functional
  bugs before this was usable (see below), wrote this README, and helped
  plan the overall approach.
- **Google Gemini** (`gemini-1.5-flash` + `text-embedding-004`) — powers the
  actual fact extraction and relationship classification at runtime.

### Bugs found and fixed during review
The scaffolded code had three issues that would have broken the app in
practice; documenting them here since being honest about what didn't work
out of the box is more useful than pretending it was perfect:
1. `.env` was loaded *after* modules that read `GEMINI_API_KEY` at import
   time, so a correctly-set API key was silently ignored.
2. `vite.config.ts` imported a Vite plugin package that wasn't actually
   listed as a dependency, so a fresh `npm install && npm run build` failed.
3. The frontend's shared API request helper forced a JSON `Content-Type`
   header onto file-upload requests, which prevents the browser from setting
   the multipart boundary `FormData` needs — this broke PDF uploads from the
   UI specifically.

---

## Limitations and Next Steps

**What doesn't work yet / known weaknesses:**
- Extraction quality depends entirely on the LLM's single pass per page —
  facts split across a page boundary, or requiring context from a table on a
  different page, can be missed or extracted incompletely.
- The candidate-retrieval threshold is a single global constant
  (`EMBEDDING_SIMILARITY_THRESHOLD`); it isn't adaptive per document type, so
  it may need tuning between very different domains.
- No deduplication of near-identical facts extracted from repeated content
  (e.g., a figure restated in an executive summary and again in the body).
- No UI for correcting a wrong classification — a human-in-the-loop review
  step would materially improve trust in the output over time.
- No handling for scanned/image-only PDFs (no OCR fallback).

**What I'd build next:**
- A confidence score per fact and per relationship, surfaced in the UI, so
  low-confidence classifications can be flagged for review instead of shown
  with the same weight as clear-cut ones.
- Batched extraction calls (multiple pages per LLM call with careful
  prompting) to cut latency and cost on very large PDFs.
- A feedback loop where a user's manual correction to a relationship is
  used to refine future classification.
- Basic OCR fallback for scanned documents.

---

## Additional Notes

The two starter datasets provided (Delhivery corporate filings, and Indian
macroeconomic institutional reports) were chosen by the assignment authors
in a way that maps well onto the four required cases — the macroeconomic set
in particular has the same metrics reported by different institutions at
different times, which is well-suited to surfacing genuine
context-explained contradictions.
