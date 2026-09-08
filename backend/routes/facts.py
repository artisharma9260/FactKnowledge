"""
Facts routes — list and retrieve extracted facts.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Document, Fact
from schemas import FactOut

router = APIRouter()


def _enrich(fact: Fact, doc: Document | None) -> FactOut:
    """Convert ORM Fact to FactOut, injecting document name fields."""
    out = FactOut.model_validate(fact)
    if doc:
        out.document_filename = doc.filename
        out.document_original_name = doc.original_name
    return out


@router.get("/", response_model=list[FactOut])
async def list_facts(
    document_id: int | None = Query(None, description="Filter by document"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """List facts, optionally filtered by document."""
    stmt = select(Fact).order_by(Fact.id)
    if document_id is not None:
        stmt = stmt.where(Fact.document_id == document_id)
    stmt = stmt.offset(skip).limit(limit)

    result = await db.execute(stmt)
    facts = result.scalars().all()

    # Batch-load documents
    doc_ids = {f.document_id for f in facts}
    docs: dict[int, Document] = {}
    for did in doc_ids:
        doc = await db.get(Document, did)
        if doc:
            docs[did] = doc

    return [_enrich(f, docs.get(f.document_id)) for f in facts]


@router.get("/{fact_id}", response_model=FactOut)
async def get_fact(fact_id: int, db: AsyncSession = Depends(get_db)):
    fact = await db.get(Fact, fact_id)
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found.")
    doc = await db.get(Document, fact.document_id)
    return _enrich(fact, doc)
