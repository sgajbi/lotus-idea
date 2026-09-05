import pytest

from app.domain import SourceReconciliationPosture
from app.infrastructure.source_revision_claims import (
    build_source_revision_claims,
    source_reconciliation_posture,
    source_revision_claims_from_payloads,
)


@pytest.mark.parametrize(
    ("owner_status", "expected"),
    [
        ("COMPLETE", SourceReconciliationPosture.COMPLETE),
        ("partial", SourceReconciliationPosture.PARTIAL),
        ("UNRECONCILED", SourceReconciliationPosture.FAILED),
        ("not_applicable", SourceReconciliationPosture.NOT_APPLICABLE),
        ("owner-specific-value", SourceReconciliationPosture.UNKNOWN),
        (None, SourceReconciliationPosture.UNKNOWN),
    ],
)
def test_owner_reconciliation_status_is_normalized_conservatively(
    owner_status: str | None,
    expected: SourceReconciliationPosture,
) -> None:
    assert source_reconciliation_posture(owner_status) is expected


def test_builder_does_not_manufacture_claims_from_reconciliation_alone() -> None:
    assert build_source_revision_claims(reconciliation_status="COMPLETE") is None


def test_common_payload_mapper_preserves_first_owner_claim_across_shapes() -> None:
    claims = source_revision_claims_from_payloads(
        {"sourceRevision": "risk-run-7", "reconciliationStatus": "COMPLETE"},
        {"source_revision": "fallback-run", "methodology_version": "risk-v3"},
    )

    assert claims is not None
    assert claims.source_revision == "risk-run-7"
    assert claims.methodology_version == "risk-v3"
    assert claims.reconciliation_posture is SourceReconciliationPosture.COMPLETE


def test_common_payload_mapper_does_not_infer_revision_from_status() -> None:
    assert source_revision_claims_from_payloads({"reconciliationStatus": "COMPLETE"}) is None
