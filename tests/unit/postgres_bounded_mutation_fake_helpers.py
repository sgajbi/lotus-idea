from __future__ import annotations

from typing import Any, Protocol, Sequence


class BoundedMutationFakeCursor(Protocol):
    connection: Any
    _rows: list[dict[str, Any]]


def execute_bounded_mutation_query(
    cursor: BoundedMutationFakeCursor,
    normalized: str,
    params: Sequence[Any] | None,
) -> bool:
    if normalized.startswith("/* lotus-idea aggregate-mutation-"):
        cursor._rows = []
        return True
    if normalized.startswith("/* lotus-idea ai-lineage-identity-candidates */"):
        assert params is not None
        request_id, _, attestation_nonce, _, provider_nonce = params
        cursor._rows = [
            {"candidate_id": row["candidate_id"]}
            for row in cursor.connection.rows["idea_ai_explanation_lineage"]
            if row["ai_explanation_request_id"] == request_id
            or (
                attestation_nonce is not None
                and row.get("lotus_ai_replay_nonce") == attestation_nonce
            )
            or (
                provider_nonce is not None
                and row.get("provider_retention_replay_nonce") == provider_nonce
            )
        ]
        return True
    if normalized.startswith("/* lotus-idea mutation-lookup-conversion-candidate */"):
        assert params is not None
        cursor._rows = [
            {"candidate_id": row["candidate_id"]}
            for row in cursor.connection.rows["idea_conversion_intent"]
            if row["conversion_intent_id"] == params[0]
        ]
        return True
    return False
