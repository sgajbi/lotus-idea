from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest

from app.domain import (
    MAX_PRESENTED_CANDIDATE_COUNT,
    PRESENTATION_PRODUCER,
    PRESENTATION_RECEIPT_SCHEMA_VERSION,
    PRESENTATION_SURFACE,
    CandidatePresentationReceipt,
    InMemoryIdeaRepository,
    OpportunityFamily,
    PresentationReceiptCandidateStateError,
    PresentationReceiptDecision,
    SourceCutPosture,
    validate_presentation_receipt_candidate,
)
from tests.support.opportunity_effectiveness_fixture import (
    candidate_fixture,
    record_fixture,
    snapshot_fixture,
)


def test_candidate_presentation_receipt_accepts_governed_visible_queue_evidence() -> None:
    receipt = _receipt()

    assert receipt.schema_version == PRESENTATION_RECEIPT_SCHEMA_VERSION
    assert receipt.surface == PRESENTATION_SURFACE
    assert receipt.producer == PRESENTATION_PRODUCER
    assert receipt.rank_at_presentation == 2
    assert receipt.visible_candidate_count == 7


def test_candidate_presentation_receipt_keeps_global_rank_separate_from_visible_count() -> None:
    receipt = _receipt(rank_at_presentation=25, visible_candidate_count=1)

    assert receipt.rank_at_presentation == 25
    assert receipt.visible_candidate_count == 1


def test_legacy_receipt_retains_unknown_cut_and_cannot_match_current_candidate() -> None:
    receipt = _receipt(
        schema_version="lotus-idea.candidate-presentation-receipt.v1",
        source_revision_vector_digest=None,
        source_cut_posture=SourceCutPosture.UNKNOWN,
    )

    assert receipt.source_revision_vector_digest is None
    with pytest.raises(PresentationReceiptCandidateStateError, match="revision vector"):
        validate_presentation_receipt_candidate(receipt, _candidate())


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    (
        ("receipt_id", "", "receipt_id must be a governed reference"),
        ("candidate_id", "candidate/unsafe", "candidate_id must be a governed reference"),
        ("tenant_id", 42, "tenant_id must be a governed reference"),
        ("queue_policy_version", "v 1", "queue_policy_version must be a governed reference"),
        ("ranking_policy_version", "v", "ranking_policy_version must be a governed reference"),
        ("schema_version", "lotus-idea.candidate-presentation-receipt.v3", "unsupported"),
        ("surface", "search_results", "unsupported"),
        ("producer", "lotus-gateway", "unsupported"),
        ("presented_at_utc", datetime(2026, 8, 30), "timezone-aware"),
        ("presented_at_utc", "2026-08-30T12:00:00Z", "must be a datetime"),
        (
            "presented_at_utc",
            datetime(2026, 8, 30, tzinfo=timezone(timedelta(hours=1))),
            "must be UTC",
        ),
        ("accepted_at_utc", datetime(2026, 8, 30), "timezone-aware"),
        (
            "accepted_at_utc",
            datetime(2026, 8, 30, tzinfo=timezone(timedelta(hours=1))),
            "must be UTC",
        ),
        ("rank_at_presentation", 0, "must be a positive integer"),
        ("rank_at_presentation", True, "must be a positive integer"),
        ("visible_candidate_count", 0, "must be between"),
        ("visible_candidate_count", MAX_PRESENTED_CANDIDATE_COUNT + 1, "must be between"),
        ("visible_candidate_count", True, "must be between"),
        ("queue_snapshot_digest", "queue-snapshot", "must be a sha256 digest"),
        ("source_revision_vector_digest", "source-vector", "must be a sha256 digest"),
        ("candidate_material_version", 0, "must be a positive integer"),
        ("candidate_material_version", True, "must be a positive integer"),
        ("candidate_evidence_version", 0, "must be a positive integer"),
    ),
)
def test_candidate_presentation_receipt_rejects_ungoverned_evidence(
    field_name: str,
    value: object,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        _receipt(**{field_name: value})


def test_in_memory_repository_records_and_replays_exact_receipt() -> None:
    repository = _repository()
    receipt = _receipt()

    accepted = repository.record_presentation_receipt(receipt)
    replayed = repository.record_presentation_receipt(receipt)

    assert accepted.decision is PresentationReceiptDecision.ACCEPTED
    assert accepted.receipt == receipt
    assert replayed.decision is PresentationReceiptDecision.REPLAYED
    assert replayed.receipt == receipt


def test_presentation_replay_retains_original_server_acceptance_time() -> None:
    repository = _repository()
    receipt = _receipt()
    retry = _receipt(accepted_at_utc=receipt.accepted_at_utc + timedelta(microseconds=1))

    repository.record_presentation_receipt(receipt)
    replayed = repository.record_presentation_receipt(retry)

    assert replayed.decision is PresentationReceiptDecision.REPLAYED
    assert replayed.receipt == receipt


def test_in_memory_repository_snapshot_preserves_presentation_receipts_across_restart() -> None:
    repository = _repository()
    receipt = _receipt()
    repository.record_presentation_receipt(receipt)

    restarted = InMemoryIdeaRepository(repository.snapshot())
    replayed = restarted.record_presentation_receipt(receipt)

    assert restarted.snapshot().presentation_receipts == {receipt.receipt_id: receipt}
    assert replayed.decision is PresentationReceiptDecision.REPLAYED
    assert replayed.receipt == receipt


def test_in_memory_repository_reports_identity_conflict_without_overwrite() -> None:
    repository = _repository()
    receipt = _receipt()
    repository.record_presentation_receipt(receipt)

    conflict = repository.record_presentation_receipt(_receipt(rank_at_presentation=3))
    replay = repository.record_presentation_receipt(receipt)

    assert conflict.decision is PresentationReceiptDecision.CONFLICT
    assert conflict.receipt == receipt
    assert replay.decision is PresentationReceiptDecision.REPLAYED


def test_in_memory_repository_does_not_disclose_receipt_across_candidate_scope() -> None:
    repository = _repository()
    repository.record_presentation_receipt(_receipt())

    with pytest.raises(PresentationReceiptCandidateStateError):
        repository.record_presentation_receipt(
            _receipt(candidate_id="candidate-other", tenant_id="tenant-other")
        )


@pytest.mark.parametrize(
    "overrides",
    (
        {"candidate_id": "candidate-missing"},
        {"tenant_id": "tenant-other"},
        {"candidate_material_version": 2},
        {"candidate_evidence_version": 2},
        {"source_revision_vector_digest": f"sha256:{'f' * 64}"},
        {"accepted_at_utc": datetime(2026, 8, 30, 11, 59, 59, tzinfo=UTC)},
    ),
)
def test_in_memory_repository_rejects_receipt_that_does_not_match_candidate(
    overrides: dict[str, Any],
) -> None:
    with pytest.raises(PresentationReceiptCandidateStateError):
        _repository().record_presentation_receipt(_receipt(**overrides))


def test_candidate_validation_rejects_mismatched_identity_before_other_claims() -> None:
    candidate = candidate_fixture(
        "candidate-0001",
        family=OpportunityFamily.HIGH_CASH,
        score=Decimal("88"),
        created_at=datetime(2026, 8, 30, 12, tzinfo=UTC),
        tenant_id="tenant-0001",
    )

    with pytest.raises(PresentationReceiptCandidateStateError, match="identity does not match"):
        validate_presentation_receipt_candidate(
            _receipt(candidate_id="candidate-other"),
            candidate,
        )


def _receipt(**overrides: Any) -> CandidatePresentationReceipt:
    candidate = _candidate()
    values: dict[str, Any] = {
        "receipt_id": "receipt-0001",
        "candidate_id": "candidate-0001",
        "tenant_id": "tenant-0001",
        "presented_at_utc": datetime(2026, 8, 30, 12, tzinfo=UTC),
        "rank_at_presentation": 2,
        "visible_candidate_count": 7,
        "queue_snapshot_digest": f"sha256:{'a' * 64}",
        "queue_policy_version": "idea-review-queue-v1",
        "ranking_policy_version": "idea-score-v2",
        "candidate_material_version": 1,
        "candidate_evidence_version": 1,
        "source_revision_vector_digest": candidate.evidence_packet.source_revision_vector_digest,
        "source_cut_posture": candidate.evidence_packet.source_cut_posture,
        "accepted_at_utc": datetime(2026, 8, 30, 12, 0, 1, tzinfo=UTC),
    }
    values.update(overrides)
    return CandidatePresentationReceipt(**values)


def _repository() -> InMemoryIdeaRepository:
    candidate = _candidate()
    return InMemoryIdeaRepository(snapshot_fixture(record_fixture(candidate)))


def _candidate():
    return candidate_fixture(
        "candidate-0001",
        family=OpportunityFamily.HIGH_CASH,
        score=Decimal("88"),
        created_at=datetime(2026, 8, 30, 12, tzinfo=UTC),
        tenant_id="tenant-0001",
    )
