from __future__ import annotations

from app.domain.candidate_state import ALLOWED_REVIEW_POSTURES_BY_LIFECYCLE


def candidate_state_compatibility_sql(
    *,
    lifecycle_column: str = "lifecycle_status",
    review_posture_column: str = "review_posture",
) -> str:
    """Render the trusted enum policy as a PostgreSQL eligibility predicate."""
    clauses = []
    for lifecycle_status, allowed_postures in ALLOWED_REVIEW_POSTURES_BY_LIFECYCLE.items():
        posture_values = ", ".join(
            f"'{posture.value}'"
            for posture in sorted(allowed_postures, key=lambda item: item.value)
        )
        clauses.append(
            f"({lifecycle_column} = '{lifecycle_status.value}' "
            f"AND {review_posture_column} IN ({posture_values}))"
        )
    return "(" + " OR ".join(clauses) + ")"


def candidate_record_state_compatibility_sql() -> str:
    return (
        "((candidate_json->>'lifecycle_status') = lifecycle_status "
        "AND (candidate_json->>'review_posture') = review_posture "
        f"AND {candidate_state_compatibility_sql()})"
    )
