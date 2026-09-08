"""
SQLAlchemy ORM models.

Design decisions:
  - `facts.attributes` is a JSON column so new fact types don't require migrations.
  - `facts.embedding`  stores the vector as a JSON-encoded float list (SQLite has no
    native vector type; for scale, swap to pgvector or a dedicated store).
  - `relationships.explanation` holds the LLM's free-text reasoning.
"""

import json
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float,
    ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import relationship, mapped_column, Mapped
from sqlalchemy.types import TypeDecorator, TEXT

from database import Base


# --------------------------------------------------------------------------- #
#  Custom JSON column (works with SQLite)
# --------------------------------------------------------------------------- #

class JSONColumn(TypeDecorator):
    impl = TEXT
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return json.loads(value)


# --------------------------------------------------------------------------- #
#  Models
# --------------------------------------------------------------------------- #

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    original_name: Mapped[str] = mapped_column(String(512), nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default="uploaded"
    )  # uploaded | processing | done | error
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    facts: Mapped[list["Fact"]] = relationship(
        "Fact", back_populates="document", cascade="all, delete-orphan"
    )


class Fact(Base):
    __tablename__ = "facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Core structured fields — always present
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    entities: Mapped[list[str] | None] = mapped_column(JSONColumn, nullable=True)      # ["ACME Corp", "RBI"]
    numbers: Mapped[list[dict] | None] = mapped_column(JSONColumn, nullable=True)       # [{"value": 12.5, "unit": "%"}]
    time_period: Mapped[str | None] = mapped_column(String(256), nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Flexible bag-of-attributes for domain-specific extras
    attributes: Mapped[dict[str, Any] | None] = mapped_column(JSONColumn, nullable=True)
    # Embedding stored as JSON float list
    embedding: Mapped[list[float] | None] = mapped_column(JSONColumn, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    document: Mapped["Document"] = relationship("Document", back_populates="facts")

    # Relationships where this fact is on either side
    relationships_as_fact_a: Mapped[list["Relationship"]] = relationship(
        "Relationship",
        foreign_keys="Relationship.fact_a_id",
        back_populates="fact_a",
        cascade="all, delete-orphan",
    )
    relationships_as_fact_b: Mapped[list["Relationship"]] = relationship(
        "Relationship",
        foreign_keys="Relationship.fact_b_id",
        back_populates="fact_b",
        cascade="all, delete-orphan",
    )


class Relationship(Base):
    __tablename__ = "relationships"
    __table_args__ = (
        # Prevent duplicate pairs regardless of order
        UniqueConstraint("fact_a_id", "fact_b_id", name="uq_fact_pair"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    fact_a_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("facts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fact_b_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("facts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # corroboration | contradiction | context_explained
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    fact_a: Mapped["Fact"] = relationship(
        "Fact", foreign_keys=[fact_a_id], back_populates="relationships_as_fact_a"
    )
    fact_b: Mapped["Fact"] = relationship(
        "Fact", foreign_keys=[fact_b_id], back_populates="relationships_as_fact_b"
    )
