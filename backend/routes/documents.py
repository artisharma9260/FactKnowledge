"""
Document routes — upload, list, delete, and trigger processing.

Processing pipeline (triggered after upload):
  1. Parse PDF page-by-page.
  2. For each page, call Gemini to extract facts.
  3. Embed each extracted fact.
  4. For each new fact, find similar existing facts (from OTHER documents)
     using cosine similarity, then classify each candidate pair with Gemini.
  5. Persist facts and relationships to SQLite.

Incremental guarantee: already-processed documents are NEVER re-parsed or
re-extracted. Only the new document's facts are compared against the store.
"""

import asyncio
import logging
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from embeddings import embed_text, find_similar_facts
from fact_comparator import compare_facts
from fact_extractor import extract_facts_from_chunk
from models import Document, Fact, Relationship
from pdf_parser import parse_pdf
from schemas import DocumentOut, ProcessingStatus

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Guard against concurrent processing of the same document
_processing_lock: dict[int, bool] = {}


# --------------------------------------------------------------------------- #
#  Routes
# --------------------------------------------------------------------------- #

@router.post("/upload", response_model=DocumentOut, status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a PDF and start background processing."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    # Save to disk with a unique name
    unique_name = f"{uuid.uuid4().hex}_{file.filename}"
    save_path = UPLOAD_DIR / unique_name

    with save_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    # Persist document record
    doc = Document(
        filename=unique_name,
        original_name=file.filename,
        status="uploaded",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    logger.info("Document %d uploaded: %s", doc.id, file.filename)
    background_tasks.add_task(_process_document, doc.id)

    return doc


@router.get("/", response_model=list[DocumentOut])
async def list_documents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).order_by(Document.uploaded_at.desc()))
    return result.scalars().all()


@router.get("/{doc_id}", response_model=DocumentOut)
async def get_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc


@router.get("/{doc_id}/status", response_model=ProcessingStatus)
async def get_processing_status(doc_id: int, db: AsyncSession = Depends(get_db)):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    facts_result = await db.execute(
        select(Fact).where(Fact.document_id == doc_id)
    )
    facts_count = len(facts_result.scalars().all())

    rels_result = await db.execute(
        select(Relationship).join(
            Fact, (Relationship.fact_a_id == Fact.id) | (Relationship.fact_b_id == Fact.id)
        ).where(Fact.document_id == doc_id)
    )
    rels_count = len(set(r.id for r in rels_result.scalars().all()))

    return ProcessingStatus(
        document_id=doc_id,
        status=doc.status,
        message=doc.error_message or _status_message(doc.status),
        facts_extracted=facts_count,
        relationships_found=rels_count,
    )


@router.delete("/{doc_id}", status_code=204)
async def delete_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Remove file
    path = UPLOAD_DIR / doc.filename
    if path.exists():
        path.unlink()

    await db.delete(doc)
    await db.commit()


# --------------------------------------------------------------------------- #
#  Background processing pipeline
# --------------------------------------------------------------------------- #

async def _process_document(doc_id: int):
    """
    Full extraction + comparison pipeline, run in the background.
    Uses a fresh DB session (background task runs outside the request lifecycle).
    """
    from database import AsyncSessionLocal

    if _processing_lock.get(doc_id):
        logger.warning("Document %d is already being processed; skipping.", doc_id)
        return

    _processing_lock[doc_id] = True
    async with AsyncSessionLocal() as db:
        try:
            await _run_pipeline(doc_id, db)
        except Exception as exc:
            logger.exception("Pipeline failed for document %d: %s", doc_id, exc)
            doc = await db.get(Document, doc_id)
            if doc:
                doc.status = "error"
                doc.error_message = str(exc)[:1000]
                await db.commit()
        finally:
            _processing_lock.pop(doc_id, None)


async def _run_pipeline(doc_id: int, db: AsyncSession):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise ValueError(f"Document {doc_id} not found in DB.")

    # Idempotency guard
    if doc.status == "done":
        logger.info("Document %d already processed; skipping.", doc_id)
        return

    doc.status = "processing"
    await db.commit()

    # ------------------------------------------------------------------ #
    # Step 1: Parse PDF
    # ------------------------------------------------------------------ #
    pdf_path = UPLOAD_DIR / doc.filename
    logger.info("[Doc %d] Parsing PDF …", doc_id)
    chunks = parse_pdf(pdf_path)
    doc.page_count = len(chunks)
    await db.commit()

    # ------------------------------------------------------------------ #
    # Step 2: Extract facts from each page
    # ------------------------------------------------------------------ #
    logger.info("[Doc %d] Extracting facts from %d pages …", doc_id, len(chunks))
    new_facts: list[Fact] = []

    for chunk in chunks:
        try:
            raw_facts = await extract_facts_from_chunk(chunk, doc_id)
        except Exception as exc:
            logger.error(
                "[Doc %d] Fact extraction failed on page %d: %s",
                doc_id, chunk["page_number"], exc,
            )
            continue

        for rf in raw_facts:
            fact = Fact(
                document_id=rf["document_id"],
                page_number=rf["page_number"],
                claim=rf["claim"],
                entities=rf["entities"],
                numbers=rf["numbers"],
                time_period=rf["time_period"],
                source_quote=rf["source_quote"],
                attributes=rf["attributes"],
            )
            db.add(fact)
            new_facts.append(fact)

        # Flush periodically to get IDs assigned
        await db.flush()

    await db.commit()
    logger.info("[Doc %d] %d facts saved.", doc_id, len(new_facts))

    # ------------------------------------------------------------------ #
    # Step 3: Embed new facts
    # ------------------------------------------------------------------ #
    logger.info("[Doc %d] Generating embeddings …", doc_id)
    for fact in new_facts:
        try:
            embed_input = f"{fact.claim} {fact.time_period or ''} {' '.join(fact.entities or [])}"
            fact.embedding = await embed_text(embed_input)
        except Exception as exc:
            logger.warning("[Doc %d] Embedding failed for fact %d: %s", doc_id, fact.id, exc)

    await db.commit()

    # ------------------------------------------------------------------ #
    # Step 4: Retrieve existing facts from OTHER documents
    # ------------------------------------------------------------------ #
    existing_result = await db.execute(
        select(Fact).where(Fact.document_id != doc_id)
    )
    existing_facts_orm = existing_result.scalars().all()

    # Build lightweight dicts (avoid repeated ORM attribute access in tight loop)
    existing_fact_dicts: list[dict] = []
    for f in existing_facts_orm:
        doc_result = await db.get(Document, f.document_id)
        existing_fact_dicts.append({
            "id": f.id,
            "document_id": f.document_id,
            "document_original_name": doc_result.original_name if doc_result else "",
            "claim": f.claim,
            "entities": f.entities,
            "numbers": f.numbers,
            "time_period": f.time_period,
            "source_quote": f.source_quote,
            "page_number": f.page_number,
            "embedding": f.embedding,
        })

    if not existing_fact_dicts:
        logger.info("[Doc %d] No existing facts to compare against.", doc_id)
    else:
        logger.info(
            "[Doc %d] Comparing %d new facts against %d existing facts …",
            doc_id, len(new_facts), len(existing_fact_dicts),
        )

    # ------------------------------------------------------------------ #
    # Step 5: Compare & classify relationships
    # ------------------------------------------------------------------ #
    await db.refresh(doc)  # reload after flushes
    new_doc_result = await db.get(Document, doc_id)

    for fact in new_facts:
        if not fact.embedding:
            continue

        candidates = find_similar_facts(fact.embedding, existing_fact_dicts)

        for existing_dict, score in candidates:
            # Check if this pair already exists (handles re-runs gracefully)
            pair_check = await db.execute(
                select(Relationship).where(
                    (
                        (Relationship.fact_a_id == fact.id) &
                        (Relationship.fact_b_id == existing_dict["id"])
                    ) | (
                        (Relationship.fact_a_id == existing_dict["id"]) &
                        (Relationship.fact_b_id == fact.id)
                    )
                )
            )
            if pair_check.scalar_one_or_none():
                continue  # Already classified

            new_fact_dict = {
                "id": fact.id,
                "document_id": fact.document_id,
                "document_original_name": new_doc_result.original_name if new_doc_result else "",
                "claim": fact.claim,
                "entities": fact.entities,
                "numbers": fact.numbers,
                "time_period": fact.time_period,
                "source_quote": fact.source_quote,
                "page_number": fact.page_number,
            }

            try:
                result = await compare_facts(new_fact_dict, existing_dict, score)
            except Exception as exc:
                logger.error(
                    "[Doc %d] Comparison failed for facts %d vs %d: %s",
                    doc_id, fact.id, existing_dict["id"], exc,
                )
                continue

            if result:
                rel = Relationship(
                    fact_a_id=fact.id,
                    fact_b_id=existing_dict["id"],
                    category=result["category"],
                    explanation=result["explanation"],
                    similarity_score=result.get("similarity_score"),
                )
                db.add(rel)

        await db.flush()

    await db.commit()

    # ------------------------------------------------------------------ #
    # Done
    # ------------------------------------------------------------------ #
    doc.status = "done"
    doc.processed_at = datetime.utcnow()
    await db.commit()
    logger.info("[Doc %d] Processing complete.", doc_id)


def _status_message(status: str) -> str:
    return {
        "uploaded": "Queued for processing",
        "processing": "Extracting facts and finding relationships …",
        "done": "Processing complete",
        "error": "Processing failed",
    }.get(status, status)
