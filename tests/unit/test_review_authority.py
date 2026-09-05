from dataclasses import replace
from datetime import datetime, timedelta

import pytest

from app.domain.presentation_receipts import CandidatePresentationReceipt
from app.domain.review_authority import (
    REVIEW_AUTHORITY_POLICY_VERSION,
    WORKBENCH_REVIEW_WINDOW,
    CandidateEvidenceIdentity,
    ReviewAuthorityConflict,
    ReviewAuthorityGrant,
    ReviewAuthorityStatus,
    ReviewChannel,
    validate_expected_candidate_evidence,
    validate_workbench_presentation,
)
from tests.unit.test_review_governance import DECIDED_AT, candidate


QUEUE_DIGEST = "sha256:" + "a" * 64


def evidence_identity() -> CandidateEvidenceIdentity:
    return CandidateEvidenceIdentity.from_candidate(candidate())


def presentation_receipt(
    *,
    accepted_at_utc: datetime = DECIDED_AT - timedelta(minutes=1),
) -> CandidatePresentationReceipt:
    identity = evidence_identity()
    return CandidatePresentationReceipt(
        receipt_id="receipt-review-authority-001",
        candidate_id=identity.candidate_id,
        tenant_id="tenant-private-bank-sg",
        presented_at_utc=accepted_at_utc,
        rank_at_presentation=1,
        visible_candidate_count=3,
        queue_snapshot_digest=QUEUE_DIGEST,
        queue_policy_version="idea-review-queue-v1",
        ranking_policy_version="idea-deterministic-ranking-v1",
        candidate_material_version=identity.material_version,
        candidate_evidence_version=identity.evidence_version,
        accepted_at_utc=accepted_at_utc,
    )


def authority_grant() -> ReviewAuthorityGrant:
    receipt = presentation_receipt()
    return ReviewAuthorityGrant(
        review_id="review-approve-for-conversion",
        candidate_evidence=evidence_identity(),
        review_channel=ReviewChannel.WORKBENCH,
        actor_subject="advisor-001",
        actor_role="advisor",
        review_policy_version="idea-human-review-v1",
        accepted_at_utc=DECIDED_AT,
        applicability_expires_at_utc=DECIDED_AT + timedelta(minutes=20),
        presentation_receipt_id=receipt.receipt_id,
        queue_snapshot_digest=receipt.queue_snapshot_digest,
    )


def test_expected_candidate_evidence_binds_material_evidence_packet_and_hash() -> None:
    expected = evidence_identity()

    validate_expected_candidate_evidence(expected, candidate())

    for changed in (
        replace(expected, material_version=expected.material_version + 1),
        replace(expected, evidence_version=expected.evidence_version + 1),
        replace(expected, evidence_packet_id="iep-review-new"),
        replace(expected, evidence_content_hash="sha256:review-new"),
    ):
        with pytest.raises(ReviewAuthorityConflict, match="evidence identity is stale"):
            validate_expected_candidate_evidence(changed, candidate())


def test_workbench_presentation_must_match_exact_version_and_review_window() -> None:
    expected = evidence_identity()
    receipt = presentation_receipt()

    validate_workbench_presentation(
        expected=expected,
        receipt=receipt,
        review_accepted_at_utc=DECIDED_AT,
    )

    stale_receipt = replace(
        receipt,
        accepted_at_utc=DECIDED_AT - WORKBENCH_REVIEW_WINDOW - timedelta.resolution,
        presented_at_utc=DECIDED_AT - WORKBENCH_REVIEW_WINDOW - timedelta.resolution,
    )
    with pytest.raises(ReviewAuthorityConflict, match="outside the governed review window"):
        validate_workbench_presentation(
            expected=expected,
            receipt=stale_receipt,
            review_accepted_at_utc=DECIDED_AT,
        )

    with pytest.raises(ReviewAuthorityConflict, match="evidence version does not match"):
        validate_workbench_presentation(
            expected=expected,
            receipt=replace(receipt, candidate_evidence_version=2),
            review_accepted_at_utc=DECIDED_AT,
        )


def test_workbench_authority_requires_real_presentation_context() -> None:
    with pytest.raises(ValueError, match="requires presentation context"):
        ReviewAuthorityGrant(
            review_id="review-001",
            candidate_evidence=evidence_identity(),
            review_channel=ReviewChannel.WORKBENCH,
            actor_subject="advisor-001",
            actor_role="advisor",
            review_policy_version="idea-human-review-v1",
            accepted_at_utc=DECIDED_AT,
            applicability_expires_at_utc=None,
        )


def test_operator_authority_never_fabricates_workbench_receipt() -> None:
    grant = ReviewAuthorityGrant(
        review_id="review-operator-001",
        candidate_evidence=evidence_identity(),
        review_channel=ReviewChannel.OPERATOR,
        actor_subject="operator-001",
        actor_role="operator",
        review_policy_version="idea-human-review-v1",
        accepted_at_utc=DECIDED_AT,
        applicability_expires_at_utc=None,
    )

    assert grant.presentation_receipt_id is None
    assert grant.queue_snapshot_digest is None

    with pytest.raises(ValueError, match="cannot carry presentation context"):
        replace(
            grant,
            presentation_receipt_id="receipt-fabricated",
            queue_snapshot_digest=QUEUE_DIGEST,
        )


def test_authority_posture_fails_closed_for_change_supportability_and_expiry() -> None:
    grant = authority_grant()
    assert grant.applicability_expires_at_utc is not None
    assert grant.authority_policy_version == REVIEW_AUTHORITY_POLICY_VERSION
    current = candidate(applicability_expires_at_utc=grant.applicability_expires_at_utc)

    assert grant.effective_status(current, evaluated_at_utc=DECIDED_AT) is (
        ReviewAuthorityStatus.ACTIVE
    )
    assert replace(
        grant,
        authority_policy_version="idea-review-authority-v0",
    ).effective_status(current, evaluated_at_utc=DECIDED_AT) is ReviewAuthorityStatus.REVOKED
    changed_evidence = replace(
        current,
        identity=replace(current.identity, evidence_version=2),
    )
    assert grant.effective_status(changed_evidence, evaluated_at_utc=DECIDED_AT) is (
        ReviewAuthorityStatus.SUPERSEDED
    )
    assert (
        grant.effective_status(
            current,
            evaluated_at_utc=grant.applicability_expires_at_utc,
        )
        is ReviewAuthorityStatus.EXPIRED
    )


def test_authority_rejects_non_utc_and_grant_at_expiry() -> None:
    grant = authority_grant()

    with pytest.raises(ValueError, match="cannot be granted at or after expiry"):
        replace(grant, applicability_expires_at_utc=grant.accepted_at_utc)
    with pytest.raises(ValueError, match="must be UTC"):
        replace(grant, accepted_at_utc=datetime(2026, 6, 21, 10, 5))
