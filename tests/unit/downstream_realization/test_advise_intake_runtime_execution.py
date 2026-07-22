from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

from app.application.downstream_realization.advise_intake_runtime_execution import (
    advise_intake_runtime_execution_is_valid,
    build_advise_intake_runtime_execution_payload,
)
from tests.unit.downstream_realization.fixtures import (
    valid_advise_intake_runtime_execution,
)


def test_advise_intake_runtime_execution_accepts_bounded_live_receipts() -> None:
    payload = valid_advise_intake_runtime_execution()

    assert advise_intake_runtime_execution_is_valid(payload)
    assert payload["aggregateBlockersSatisfied"] == ("advise_live_contract_proof_missing",)
    assert payload["remainingCertificationBlockers"] == (
        "suitability_policy_authority_remains_lotus_advise",
    )
    assert payload["nonProofClaims"]["supportedFeaturePromoted"] is False  # type: ignore[index]


def test_advise_intake_runtime_execution_builder_binds_contract_checks() -> None:
    baseline = valid_advise_intake_runtime_execution()

    payload = build_advise_intake_runtime_execution_payload(
        generated_at_utc=datetime(2026, 7, 22, 0, 0, tzinfo=UTC),
        repository_root=Path(__file__).resolve().parents[3],
        advise_root=None,
        runtime_mode="local_asgi_testclient",
        receipt_evidence=baseline["receiptEvidence"],  # type: ignore[arg-type]
    )

    assert payload["runtimeChecks"]["acceptedReceiptObserved"] is True
    assert payload["runtimeChecks"]["tenantIsolationObserved"] is True


def test_advise_intake_runtime_execution_rejects_supported_feature_overclaim() -> None:
    payload = deepcopy(valid_advise_intake_runtime_execution())
    payload["nonProofClaims"]["supportedFeaturePromoted"] = True  # type: ignore[index]

    assert not advise_intake_runtime_execution_is_valid(payload)


def test_advise_intake_runtime_execution_rejects_missing_replay_evidence() -> None:
    payload = deepcopy(valid_advise_intake_runtime_execution())
    payload["receiptEvidence"]["acceptedReplay"]["intakeStatus"] = "ACCEPTED"  # type: ignore[index]

    assert not advise_intake_runtime_execution_is_valid(payload)
