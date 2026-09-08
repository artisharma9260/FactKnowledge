"""
Pydantic request / response schemas.
"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict


# --------------------------------------------------------------------------- #
#  Document
# --------------------------------------------------------------------------- #

class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    original_name: str
    page_count: int | None
    status: str
    error_message: str | None
    uploaded_at: datetime
    processed_at: datetime | None


# --------------------------------------------------------------------------- #
#  Fact
# --------------------------------------------------------------------------- #

class FactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    claim: str
    entities: list[str] | None
    numbers: list[dict] | None
    time_period: str | None
    page_number: int | None
    source_quote: str | None
    attributes: dict[str, Any] | None
    created_at: datetime

    # Joined from Document
    document_filename: str | None = None
    document_original_name: str | None = None


# --------------------------------------------------------------------------- #
#  Relationship
# --------------------------------------------------------------------------- #

class RelationshipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fact_a_id: int
    fact_b_id: int
    category: str
    explanation: str
    similarity_score: float | None
    created_at: datetime

    fact_a: FactOut | None = None
    fact_b: FactOut | None = None


# --------------------------------------------------------------------------- #
#  Processing status
# --------------------------------------------------------------------------- #

class ProcessingStatus(BaseModel):
    document_id: int
    status: str
    message: str
    facts_extracted: int = 0
    relationships_found: int = 0
