"""API contract for a persisted deterministic comparison."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ComparisonResponse(BaseModel):
    id: UUID
    project_id: UUID
    brief_revision: int
    quote_revision_snapshot: dict[str, object]
    comparison_payload: dict[str, object]
    generated_at: datetime
    stale: bool
