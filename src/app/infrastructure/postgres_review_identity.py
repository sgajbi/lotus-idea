from __future__ import annotations

from app.domain.review_governance import (
    ReviewMutationIdentity,
    ReviewMutationType,
    feedback_mutation_identity_from_event,
    review_mutation_identity_from_decision,
)
from app.infrastructure.postgres_codecs import (
    feedback_event_from_json,
    read_json_object,
    review_decision_from_json,
)
from app.infrastructure.postgres_protocols import PostgresConnection


class ConcurrentReviewIdentityMutationError(RuntimeError):
    def __init__(self, identity: ReviewMutationIdentity) -> None:
        super().__init__(
            f"concurrent {identity.mutation_type.value} identity: {identity.resource_id}"
        )
        self.identity = identity


def load_postgres_review_identity(
    connection: PostgresConnection,
    identity: ReviewMutationIdentity,
) -> ReviewMutationIdentity | None:
    if identity.mutation_type is ReviewMutationType.REVIEW_DECISION:
        query = """
            /* lotus-idea review-identity-decision */
            SELECT decision_json
            FROM idea_review_decision
            WHERE review_decision_id = %s
        """
        json_column = "decision_json"
    else:
        query = """
            /* lotus-idea review-identity-feedback */
            SELECT feedback_json
            FROM idea_feedback_event
            WHERE feedback_event_id = %s
        """
        json_column = "feedback_json"

    with connection.cursor() as cursor:
        cursor.execute(query, (identity.resource_id,))
        rows = cursor.fetchall()
    if not rows:
        return None
    payload = read_json_object(rows[0], json_column)
    if identity.mutation_type is ReviewMutationType.REVIEW_DECISION:
        return review_mutation_identity_from_decision(review_decision_from_json(payload))
    return feedback_mutation_identity_from_event(feedback_event_from_json(payload))
