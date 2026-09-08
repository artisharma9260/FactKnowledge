"""
Relationships routes — list and retrieve cross-document fact relationships.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Document, Fact, Relationship
from schemas import FactOut, RelationshipOut

router = APIRouter()

VALID_CATEGORIES = {"corroboration", "contradiction", "context_explained"}


async def _enrich_fact(fact: Fact, db: AsyncSession) -> FactOut:
    doc = await db.get(Document, fact.document_id)
    out = FactOut.model_validate(fact)
    if doc:
        out.document_filename = doc.filename
        out.document_original_name = doc.original_name
    return out


async def _enrich_relationship(rel: Relationship, db: AsyncSession) -> RelationshipOut:
    out = RelationshipOut.model_validate(rel)
    fact_a = await db.get(Fact, rel.fact_a_id)
    fact_b = await db.get(Fact, rel.fact_b_id)
    if fact_a:
        out.fact_a = await _enrich_fact(fact_a, db)
    if fact_b:
        out.fact_b = await _enrich_fact(fact_b, db)
    return out


@router.get("/", response_model=list[RelationshipOut])
async def list_relationships(
    category: str | None = Query(None, description="Filter: corroboration | contradiction | context_explained"),
    document_id: int | None = Query(None, description="Filter by document (either side)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """List relationships, optionally filtered by category or document."""
    if category and category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Must be one of: {', '.join(VALID_CATEGORIES)}",
        )

    stmt = select(Relationship).order_by(Relationship.created_at.desc())

    if category:
        stmt = stmt.where(Relationship.category == category)

    if document_id is not None:
        # Filter to relationships where at least one fact belongs to this document
        stmt = stmt.join(
            Fact,
            or_(
                Relationship.fact_a_id == Fact.id,
                Relationship.fact_b_id == Fact.id,
            ),
        ).where(Fact.document_id == document_id).distinct()

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    rels = result.scalars().all()

    enriched = []
    for rel in rels:
        enriched.append(await _enrich_relationship(rel, db))
    return enriched


@router.get("/{rel_id}", response_model=RelationshipOut)
async def get_relationship(rel_id: int, db: AsyncSession = Depends(get_db)):
    rel = await db.get(Relationship, rel_id)
    if not rel:
        raise HTTPException(status_code=404, detail="Relationship not found.")
    return await _enrich_relationship(rel, db)
