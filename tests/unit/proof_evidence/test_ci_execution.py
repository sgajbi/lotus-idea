from __future__ import annotations

from dataclasses import asdict, replace
from typing import Any, cast

import pytest

from app.domain.proof_evidence import (
    EvidenceClass,
    ci_execution_receipt_digest,
    ci_execution_receipt_from_mapping,
    ci_execution_receipt_is_well_formed,
    evidence_class_can_clear,
)
from tests.support.ai_lineage_store_proof import valid_ai_lineage_ci_execution_receipt


def test_evidence_classes_do_not_inherit_authority() -> None:
    assert evidence_class_can_clear(
        actual=EvidenceClass.CI_EXECUTION,
        required=EvidenceClass.CI_EXECUTION,
    )
    assert not evidence_class_can_clear(
        actual=EvidenceClass.SOURCE_CONTRACT,
        required=EvidenceClass.CI_EXECUTION,
    )
    assert not evidence_class_can_clear(
        actual=EvidenceClass.PRODUCTION_CERTIFICATION,
        required=EvidenceClass.RUNTIME_EXECUTION,
    )


def test_ci_execution_receipt_round_trips_with_stable_digest() -> None:
    receipt = valid_ai_lineage_ci_execution_receipt()

    restored = ci_execution_receipt_from_mapping(asdict(receipt))

    assert restored == receipt
    assert ci_execution_receipt_is_well_formed(receipt)
    assert ci_execution_receipt_digest(receipt) == ci_execution_receipt_digest(restored)


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("repository", "lotus-idea"),
        ("workflow_path", "main-releasability.yml"),
        ("run_id", 0),
        ("run_attempt", True),
        ("source_commit_sha", "not-a-commit"),
        ("source_ref", "main"),
        ("conclusion", "neutral"),
        ("completed_at_utc", "2026-06-21T10:00:00"),
        ("artifact_sha256", "a" * 64),
        ("assertions", ()),
        ("assertions", ("duplicate", "duplicate")),
    ],
)
def test_ci_execution_receipt_rejects_malformed_identity(
    field_name: str,
    bad_value: object,
) -> None:
    receipt = cast(Any, replace)(
        valid_ai_lineage_ci_execution_receipt(),
        **{field_name: bad_value},
    )

    assert not ci_execution_receipt_is_well_formed(receipt)
    assert ci_execution_receipt_from_mapping(asdict(receipt)) is None


def test_ci_execution_receipt_rejects_unknown_fields() -> None:
    payload = asdict(valid_ai_lineage_ci_execution_receipt())
    payload["trusted"] = True

    assert ci_execution_receipt_from_mapping(payload) is None
