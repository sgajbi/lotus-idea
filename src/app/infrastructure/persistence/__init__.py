"""PostgreSQL persistence composition for the Idea-owned durable boundary."""

from app.infrastructure.persistence.candidate_mutation import (
    load_candidate_persistence_snapshot,
)

__all__ = ["load_candidate_persistence_snapshot"]
