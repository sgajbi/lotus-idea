from __future__ import annotations

from dataclasses import replace

import psycopg
import pytest
from tests.support.http import managed_test_client

import app.api.downstream_realization as downstream_realization_api
from app.domain import InMemoryIdeaRepository, SourceCutPosture
from app.main import app
from app.ports.downstream_realization import DownstreamRealizationOutcome
from app.runtime.downstream_realization_state import ConversionRealizationClients
from app.runtime.repository_state import (
    get_idea_repository,
    reset_idea_repository_for_tests,
)
from tests.integration.test_downstream_realization_api import (
    CapturingConversionClient,
    downstream_submission_headers,
    record_conversion_intent,
    seed_approved_candidate,
)


def test_historical_conversion_intent_cannot_authorize_new_downstream_submission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    advise_client = CapturingConversionClient(DownstreamRealizationOutcome.accepted_by_downstream())
    manage_client = CapturingConversionClient(DownstreamRealizationOutcome.accepted_by_downstream())
    monkeypatch.setattr(
        downstream_realization_api,
        "get_conversion_realization_clients",
        lambda: ConversionRealizationClients(advise_client, manage_client),
    )
    candidate_id = seed_approved_candidate(
        client,
        suffix="-historical-authority-refusal",
        idempotency_prefix="historical-authority-refusal",
    )
    conversion_intent_id = "conversion-historical-authority-refusal-001"
    record_conversion_intent(
        client,
        candidate_id,
        conversion_intent_id=conversion_intent_id,
        target="advise_proposal",
        idempotency_key=conversion_intent_id,
    )

    repository = get_idea_repository()
    snapshot = repository.snapshot()
    record = snapshot.candidate_records[candidate_id]
    current_intent = record.conversion_intents[0]
    assert current_intent.review_authority_grant is not None
    historical_evidence = replace(
        current_intent.review_authority_grant.candidate_evidence,
        source_revision_vector_digest="legacy:unknown",
        source_cut_posture=SourceCutPosture.UNKNOWN,
    )
    historical_intent = replace(
        current_intent,
        source_revision_vector_digest="legacy:unknown",
        source_cut_posture=SourceCutPosture.UNKNOWN,
        review_authority_grant=replace(
            current_intent.review_authority_grant,
            candidate_evidence=historical_evidence,
        ),
    )
    reset_idea_repository_for_tests(
        InMemoryIdeaRepository(
            replace(
                snapshot,
                candidate_records={
                    **snapshot.candidate_records,
                    candidate_id: replace(record, conversion_intents=(historical_intent,)),
                },
            )
        )
    )
    historical_snapshot = get_idea_repository().snapshot()

    response = client.post(
        f"/api/v1/conversion-intents/{conversion_intent_id}/downstream-submissions",
        headers=downstream_submission_headers("downstream-historical-authority-refusal-001"),
    )

    assert response.status_code == 409
    assert response.json() == {
        "type": "about:blank",
        "title": "Conversion intent authority conflict",
        "status": 409,
        "detail": (
            "The retained conversion intent no longer has current authority for a new "
            "downstream submission attempt."
        ),
        "code": "conversion_intent_authority_conflict",
    }
    assert advise_client.submitted == ()
    assert manage_client.submitted == ()
    assert get_idea_repository().snapshot() == historical_snapshot


def test_postgres_hydrated_historical_intent_refuses_before_claim_or_io(
    postgres_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = managed_test_client(app)
    advise_client = CapturingConversionClient(DownstreamRealizationOutcome.accepted_by_downstream())
    manage_client = CapturingConversionClient(DownstreamRealizationOutcome.accepted_by_downstream())
    monkeypatch.setattr(
        downstream_realization_api,
        "get_conversion_realization_clients",
        lambda: ConversionRealizationClients(advise_client, manage_client),
    )
    candidate_id = seed_approved_candidate(
        client,
        suffix="-postgres-historical-authority",
        idempotency_prefix="postgres-historical-authority",
    )
    conversion_intent_id = "conversion-postgres-historical-authority-001"
    record_conversion_intent(
        client,
        candidate_id,
        conversion_intent_id=conversion_intent_id,
        target="advise_proposal",
        idempotency_key=conversion_intent_id,
    )

    with psycopg.connect(postgres_database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE idea_conversion_intent
            SET intent_json = jsonb_set(
                intent_json - 'source_revision_vector_digest' - 'source_cut_posture',
                '{review_authority_grant,candidate_evidence}',
                (intent_json #> '{review_authority_grant,candidate_evidence}')
                    - 'source_revision_vector_digest'
                    - 'source_cut_posture'
            )
            WHERE conversion_intent_id = %s
            """,
            (conversion_intent_id,),
        )
        assert cursor.rowcount == 1
    reset_idea_repository_for_tests(reload_from_environment=True)

    hydrated_intent = get_idea_repository().conversion_intent_by_id(conversion_intent_id)
    assert hydrated_intent is not None
    assert hydrated_intent.source_revision_vector_digest == "legacy:unknown"
    assert hydrated_intent.source_cut_posture is SourceCutPosture.UNKNOWN
    with psycopg.connect(postgres_database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM idea_downstream_submission),
                (SELECT COUNT(*) FROM idea_audit_event),
                (SELECT COUNT(*) FROM idea_outbox_event)
            """
        )
        counts_before = cursor.fetchone()
    assert counts_before is not None

    response = client.post(
        f"/api/v1/conversion-intents/{conversion_intent_id}/downstream-submissions",
        headers=downstream_submission_headers("downstream-postgres-historical-authority-001"),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "conversion_intent_authority_conflict"
    assert advise_client.submitted == ()
    assert manage_client.submitted == ()
    with psycopg.connect(postgres_database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM idea_downstream_submission),
                (SELECT COUNT(*) FROM idea_audit_event),
                (SELECT COUNT(*) FROM idea_outbox_event)
            """
        )
        assert cursor.fetchone() == counts_before
    assert counts_before[0] == 0
