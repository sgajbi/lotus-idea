from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.application.downstream_realization.manage_intake_runtime_execution import (
    MANAGE_INTAKE_RUNTIME_EXECUTION_ENV,
    build_manage_intake_runtime_execution_payload,
    load_manage_intake_runtime_execution_from_env,
    manage_intake_runtime_execution_is_valid,
)
from tests.unit.downstream_realization.fixtures import (
    valid_manage_intake_runtime_execution,
)


def test_manage_intake_runtime_execution_accepts_bounded_live_receipts() -> None:
    payload = valid_manage_intake_runtime_execution()

    assert manage_intake_runtime_execution_is_valid(payload)
    assert payload["aggregateBlockersSatisfied"] == ("manage_live_contract_proof_missing",)
    assert payload["remainingCertificationBlockers"] == (
        "rebalance_execution_authority_remains_lotus_manage",
    )
    assert payload["nonProofClaims"]["supportedFeaturePromoted"] is False  # type: ignore[index]


def test_manage_intake_runtime_execution_builder_binds_contract_checks() -> None:
    baseline = valid_manage_intake_runtime_execution()

    payload = build_manage_intake_runtime_execution_payload(
        generated_at_utc=datetime(2026, 7, 22, 0, 0, tzinfo=UTC),
        repository_root=Path(__file__).resolve().parents[3],
        manage_root=None,
        runtime_mode="local_asgi_testclient",
        receipt_evidence=baseline["receiptEvidence"],  # type: ignore[arg-type]
    )

    assert payload["runtimeChecks"]["acceptedReceiptObserved"] is True
    assert payload["runtimeChecks"]["tenantIsolationObserved"] is True


def test_manage_intake_runtime_execution_builder_requires_aware_generation_time() -> None:
    baseline = valid_manage_intake_runtime_execution()

    with pytest.raises(ValueError, match="timezone-aware"):
        build_manage_intake_runtime_execution_payload(
            generated_at_utc=datetime(2026, 7, 22, 0, 0),
            repository_root=Path(__file__).resolve().parents[3],
            manage_root=None,
            runtime_mode="local_asgi_testclient",
            receipt_evidence=baseline["receiptEvidence"],  # type: ignore[arg-type]
        )


def test_manage_intake_runtime_execution_rejects_authority_overclaim() -> None:
    payload = deepcopy(valid_manage_intake_runtime_execution())
    payload["nonProofClaims"]["rebalanceExecutionAuthorityGranted"] = True  # type: ignore[index]

    assert not manage_intake_runtime_execution_is_valid(payload)


def test_manage_intake_runtime_execution_rejects_missing_replay_evidence() -> None:
    payload = deepcopy(valid_manage_intake_runtime_execution())
    payload["receiptEvidence"]["acceptedReplay"]["intakeStatus"] = "ACCEPTED"  # type: ignore[index]

    assert not manage_intake_runtime_execution_is_valid(payload)


def test_manage_intake_runtime_execution_rejects_contract_drift() -> None:
    payload = deepcopy(valid_manage_intake_runtime_execution())
    payload["evidenceRefs"] = ()
    assert not manage_intake_runtime_execution_is_valid(payload)

    payload = deepcopy(valid_manage_intake_runtime_execution())
    payload["aggregateBlockersSatisfied"] = ()
    assert not manage_intake_runtime_execution_is_valid(payload)

    payload = deepcopy(valid_manage_intake_runtime_execution())
    payload["remainingCertificationBlockers"] = ()
    assert not manage_intake_runtime_execution_is_valid(payload)

    payload = deepcopy(valid_manage_intake_runtime_execution())
    payload["producerCertificationBlockersRetained"] = ()
    assert not manage_intake_runtime_execution_is_valid(payload)


def test_manage_intake_runtime_execution_rejects_runtime_metadata_drift() -> None:
    payload = deepcopy(valid_manage_intake_runtime_execution())
    payload["runtimeMode"] = "manual_claim"
    assert not manage_intake_runtime_execution_is_valid(payload)

    payload = deepcopy(valid_manage_intake_runtime_execution())
    payload["generatedAtUtc"] = "2026-07-22T00:00:00"
    assert not manage_intake_runtime_execution_is_valid(payload)

    payload = deepcopy(valid_manage_intake_runtime_execution())
    payload["sourceAuthority"] = ()
    assert not manage_intake_runtime_execution_is_valid(payload)

    payload = deepcopy(valid_manage_intake_runtime_execution())
    payload["runtimeChecks"]["routeServingObserved"] = False  # type: ignore[index]
    assert not manage_intake_runtime_execution_is_valid(payload)


def test_manage_intake_runtime_execution_rejects_payload_and_receipt_shape_drift() -> None:
    payload = deepcopy(valid_manage_intake_runtime_execution())
    payload["unexpectedClaim"] = True
    assert not manage_intake_runtime_execution_is_valid(payload)

    payload = deepcopy(valid_manage_intake_runtime_execution())
    payload["receiptEvidence"]["accepted"]["unexpectedField"] = True  # type: ignore[index]
    assert not manage_intake_runtime_execution_is_valid(payload)


def test_load_manage_intake_runtime_execution_from_env_returns_payload_and_relative_ref(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    proof_path = tmp_path / "manage-proof.json"
    proof_path.write_text("{}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(MANAGE_INTAKE_RUNTIME_EXECUTION_ENV, str(proof_path))

    payload, artifact_ref = load_manage_intake_runtime_execution_from_env()

    assert payload == {}
    assert artifact_ref == "manage-proof.json"


def test_load_manage_intake_runtime_execution_from_env_rejects_non_object(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    proof_path = tmp_path / "manage-proof.json"
    proof_path.write_text("[]", encoding="utf-8")
    monkeypatch.setenv(MANAGE_INTAKE_RUNTIME_EXECUTION_ENV, str(proof_path))

    with pytest.raises(ValueError, match=MANAGE_INTAKE_RUNTIME_EXECUTION_ENV):
        load_manage_intake_runtime_execution_from_env()


def test_load_manage_intake_runtime_execution_from_env_uses_env_ref_for_external_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cwd = tmp_path / "repo"
    external = tmp_path / "external"
    cwd.mkdir()
    external.mkdir()
    proof_path = external / "manage-proof.json"
    proof_path.write_text("{}", encoding="utf-8")
    monkeypatch.chdir(cwd)
    monkeypatch.setenv(MANAGE_INTAKE_RUNTIME_EXECUTION_ENV, str(proof_path))

    payload, artifact_ref = load_manage_intake_runtime_execution_from_env()

    assert payload == {}
    assert artifact_ref == f"{MANAGE_INTAKE_RUNTIME_EXECUTION_ENV} artifact"
