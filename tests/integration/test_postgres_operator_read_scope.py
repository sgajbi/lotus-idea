from __future__ import annotations

from app.main import app
from tests.integration.postgres_runtime_support import high_cash_payload, persistence_headers
from tests.support.http import managed_test_client


def test_postgres_operator_reads_require_complete_scope_and_narrow_within_it(
    postgres_database_url: str,
) -> None:
    client = managed_test_client(app)
    persisted = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(),
        headers=persistence_headers("postgres-operator-read-scope-001"),
    )
    assert persisted.status_code == 200
    candidate_id = str(persisted.json()["persistence"]["candidateId"])

    # Evidence replay: a generic operator role with no scope, or with one dimension missing,
    # is refused before the durable candidate is read and learns nothing about it.
    unscoped_replay = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/evidence-replay",
        json=_replay_payload(),
        headers=_operator_headers("idea.candidate.evidence.replay", scoped=False),
    )
    partial_headers = _operator_headers("idea.candidate.evidence.replay")
    partial_headers.pop("X-Caller-Client-Ids")
    partial_replay = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/evidence-replay",
        json=_replay_payload(),
        headers=partial_headers,
    )
    scoped_replay = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/evidence-replay",
        json=_replay_payload(),
        headers=_operator_headers("idea.candidate.evidence.replay"),
    )

    assert unscoped_replay.status_code == 403
    assert partial_replay.status_code == 403
    assert candidate_id not in unscoped_replay.text
    assert candidate_id not in partial_replay.text
    assert scoped_replay.status_code == 200
    assert scoped_replay.json()["candidateId"] == candidate_id
    assert scoped_replay.json()["replayStatus"] != "not_found"
    assert scoped_replay.json()["durableStorageBacked"] is True

    # Operator exception counts: refused without complete scope; with complete scope the
    # PostgreSQL projection is narrowed to the caller's scope, so a caller entitled to a
    # different portfolio observes zero candidates rather than the whole estate.
    unscoped_exceptions = client.get(
        "/api/v1/review-queues/operator/exceptions",
        params={"evaluatedAtUtc": "2026-06-21T10:15:00Z"},
        headers=_operator_headers("idea.review.queue.exceptions.read", scoped=False),
    )
    scoped_exceptions = client.get(
        "/api/v1/review-queues/operator/exceptions",
        params={"evaluatedAtUtc": "2026-06-21T10:15:00Z"},
        headers=_operator_headers("idea.review.queue.exceptions.read"),
    )
    foreign_exceptions = client.get(
        "/api/v1/review-queues/operator/exceptions",
        params={"evaluatedAtUtc": "2026-06-21T10:15:00Z"},
        headers=_operator_headers(
            "idea.review.queue.exceptions.read", portfolio_ids="PB_SG_OTHER_002"
        ),
    )

    assert unscoped_exceptions.status_code == 403
    assert unscoped_exceptions.json()["code"] == "permission_denied"
    assert scoped_exceptions.status_code == 200
    assert foreign_exceptions.status_code == 200
    assert _advisor_candidate_count(scoped_exceptions.json()) == 1
    assert _advisor_candidate_count(foreign_exceptions.json()) == 0
    assert candidate_id not in scoped_exceptions.text


def _operator_headers(
    capability: str,
    *,
    scoped: bool = True,
    portfolio_ids: str = "PB_SG_GLOBAL_BAL_001",
) -> dict[str, str]:
    headers = {
        "X-Caller-Subject": "platform-operator",
        "X-Caller-Roles": "operator",
        "X-Caller-Capabilities": capability,
    }
    if scoped:
        headers.update(
            {
                "X-Caller-Tenant-Ids": "tenant-private-bank-sg",
                "X-Caller-Book-Ids": "book-advisor-001",
                "X-Caller-Portfolio-Ids": portfolio_ids,
                "X-Caller-Client-Ids": "client-001",
            }
        )
    return headers


def _replay_payload() -> dict[str, object]:
    payload = high_cash_payload()
    source_evidence = payload["sourceEvidence"]
    return {
        "evaluatedAtUtc": "2026-06-21T10:30:00Z",
        "currentSourceRefs": [
            ref
            for key, ref in source_evidence.items()
            if isinstance(ref, dict) and "productId" in ref
        ],
    }


def _advisor_candidate_count(payload: dict[str, object]) -> int:
    audiences = payload["audiences"]
    assert isinstance(audiences, list)
    for audience in audiences:
        if audience["audience"] == "advisor":
            return int(audience["candidateSnapshotCount"])
    raise AssertionError("advisor audience missing from exception projection")
