# Fact Knowledge Layer

A system that extracts factual claims from PDF documents, grounds each fact in
its source evidence (exact quote + page number), and identifies relationships
between facts across documents — corroboration, contradiction, or an apparent
contradiction explained by context (time period, data vintage, scope, or units).

Built for the Superjoin Engineering Intern hiring assignment.

---

## Setup and Run Instructions

### Prerequisites
- Python 3.11+ (tested on 3.13)
- Node.js 18+
- A Google Gemini API key ([get one free here](https://aistudio.google.com/app/apikey))

### Backend

```sh
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

cp .env.example .env
# Open .env and set GEMINI_API_KEY=your_actual_key
```

```sh
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

### A note on the free Gemini tier
The free tier caps requests at a handful per minute per model. This project
self-throttles all Gemini calls (extraction, embedding, and comparison)
through a shared rate limiter (`backend/rate_limiter.py`) to stay under that
limit, so a large PDF (50-100 pages) will take several minutes to fully
process rather than failing outright. This is a deliberate trade-off — see
Limitations below.

---

## Video Demo

https://drive.google.com/file/d/1NJAnMzQ0lTiPJu5werCwI80o4aBV0ucK/view?usp=sharing

≤3 minutes, showing: a PDF being uploaded and processed, then all four
required cases (corroboration, contradiction, context-explained,
extraction/reasoning failure) with the source evidence visible on screen.

---

## Approach

**Pipeline:** PDF → per-page text/table extraction (`pdfplumber`, falling back
to `PyMuPDF` on parse failure) → each page sent to Gemini with a strict
JSON-only extraction prompt → each extracted fact embedded via Gemini's
embedding model → cosine similarity against all previously stored facts finds
candidate related pairs → each candidate pair sent to Gemini a second time
with a separate classification prompt that labels the relationship as
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

**Rate limiting:** all Gemini calls pass through a single shared async
throttle (`rate_limiter.py`) so extraction, embedding, and comparison calls
never collectively exceed the free tier's requests-per-minute quota,
regardless of which part of the pipeline is calling. This was added after
testing surfaced 429 errors on large PDFs — see Limitations.

**Generalization:** the extraction and comparison prompts contain no
document-specific vocabulary, filenames, or hardcoded fact types — they were
tested against two structurally different starter datasets (company
financial filings and macroeconomic institutional reports) without any
per-dataset logic.

### AI tools used
- **Claude** — reviewed the generated code, found and fixed several
  functional bugs before this was usable (see below), diagnosed a Gemini
  model/SDK deprecation issue, added rate limiting, wrote this README, and
  helped plan the overall approach.
- **Google Gemini** — powers fact extraction, embeddings, and relationship
  classification at runtime, via `gemini-flash-latest` and
  `gemini-embedding-001` (Google-maintained aliases, chosen because the
  originally scaffolded model names — `gemini-1.5-flash` and
  `text-embedding-004` — have since been retired by Google).

### Bugs and issues found and fixed during review
Documenting these honestly rather than presenting the scaffold as flawless:

1. **Env loading order bug** — `.env` was loaded *after* modules that read
   `GEMINI_API_KEY` at import time, so a correctly-set API key was silently
   ignored. Fixed by moving `load_dotenv()` before those imports and making
   the key lookup lazy.
2. **Broken frontend build** — `vite.config.ts` imported a Vite plugin
   package that wasn't actually listed as a dependency, so a fresh
   `npm install && npm run build` failed immediately on a clean clone.
3. **Broken file uploads in the UI** — the frontend's shared API request
   helper forced a JSON `Content-Type` header onto every request, including
   file uploads sent as `FormData`. This prevents the browser from setting
   the multipart boundary the upload needs, silently breaking every PDF
   upload from the UI.
4. **Retired model names** — the scaffold defaulted to `gemini-1.5-flash`
   and `text-embedding-004`, both since deprecated by Google. Switched to
   the `-latest` alias family, which Google maintains to always resolve to
   a current model, to reduce how often this breaks again.
5. **Free-tier rate limiting** — large PDFs (50-100+ pages) triggered `429`
   quota errors within seconds, because pages were extracted back-to-back
   with no throttling. Added a shared rate limiter so all Gemini calls
   self-space instead of failing and being silently skipped.
6. **Portability** — the frontend lockfile pointed at a regional npm mirror
   instead of the standard registry, which could fail to install on a
   different network. Regenerated against the standard registry.
7. **Missing dependency** — `greenlet`, required by SQLAlchemy's async
   engine, wasn't listed explicitly and caused a startup crash on a fresh
   install.

---

## Limitations and Next Steps

**What doesn't work yet / known weaknesses:**
- On the free Gemini tier, processing a large PDF is slow by design (the
  rate limiter intentionally trades speed for reliability) — a 100-page
  document can take 15-20+ minutes end to end. A paid tier or a
  self-hosted/open extraction model would remove this constraint.
- Extraction quality depends entirely on the LLM's single pass per page —
  facts split across a page boundary, or requiring context from a table on a
  different page, can be missed or extracted incompletely.
- The candidate-retrieval similarity threshold is a single global constant;
  it isn't adaptive per document type, so it may need tuning between very
  different domains.
- No deduplication of near-identical facts extracted from repeated content
  (e.g., a figure restated in an executive summary and again in the body).
- No UI for correcting a wrong classification — a human-in-the-loop review
  step would materially improve trust in the output over time.
- No handling for scanned/image-only PDFs (no OCR fallback).
- Relies on Google-maintained "latest" model aliases to reduce (not
  eliminate) the risk of another model deprecation breaking the pipeline.

**What I'd build next:**
- A confidence score per fact and per relationship, surfaced in the UI, so
  low-confidence classifications can be flagged for review instead of shown
  with the same weight as clear-cut ones.
- Batched extraction calls (multiple pages per LLM call with careful
  prompting) to cut latency and API usage on very large PDFs.
- A feedback loop where a user's manual correction to a relationship is
  used to refine future classification.
- Basic OCR fallback for scanned documents.
- Migrate off the now-deprecated `google-generativeai` SDK to Google's
  current `google-genai` package.

---

## Additional Notes

The two starter datasets provided (Delhivery corporate filings, and Indian
macroeconomic institutional reports) were chosen by the assignment authors
in a way that maps well onto the four required cases — the macroeconomic set
in particular has the same metrics reported by different institutions at
different times, which is well-suited to surfacing genuine
context-explained contradictions.

This project depends on Google's free-tier Gemini API, which has both a low
requests-per-minute quota and models that are periodically deprecated with
short notice. Sample output (screenshots/exported JSON) and full video
footage are included per the assignment's guidance, so the solution can be
evaluated without needing to re-run it against a live API key.
