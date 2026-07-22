from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

from app.application.downstream_realization.advise_intake_runtime_execution import (
    ADVISE_INTAKE_RUNTIME_EXECUTION_ENV,
    advise_intake_runtime_execution_is_valid,
    build_advise_intake_runtime_execution_payload,
    load_advise_intake_runtime_execution_from_env,
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


def test_advise_intake_runtime_execution_builder_requires_aware_generation_time() -> None:
    baseline = valid_advise_intake_runtime_execution()

    try:
        build_advise_intake_runtime_execution_payload(
            generated_at_utc=datetime(2026, 7, 22, 0, 0),
            repository_root=Path(__file__).resolve().parents[3],
            advise_root=None,
            runtime_mode="local_asgi_testclient",
            receipt_evidence=baseline["receiptEvidence"],  # type: ignore[arg-type]
        )
    except ValueError as exc:
        assert "timezone-aware" in str(exc)
    else:  # pragma: no cover - defensive assertion path
        raise AssertionError("naive generation time must be rejected")


def test_advise_intake_runtime_execution_rejects_supported_feature_overclaim() -> None:
    payload = deepcopy(valid_advise_intake_runtime_execution())
    payload["nonProofClaims"]["supportedFeaturePromoted"] = True  # type: ignore[index]

    assert not advise_intake_runtime_execution_is_valid(payload)


def test_advise_intake_runtime_execution_rejects_missing_replay_evidence() -> None:
    payload = deepcopy(valid_advise_intake_runtime_execution())
    payload["receiptEvidence"]["acceptedReplay"]["intakeStatus"] = "ACCEPTED"  # type: ignore[index]

    assert not advise_intake_runtime_execution_is_valid(payload)


def test_advise_intake_runtime_execution_rejects_contract_drift() -> None:
    payload = deepcopy(valid_advise_intake_runtime_execution())
    payload["evidenceRefs"] = ()
    assert not advise_intake_runtime_execution_is_valid(payload)

    payload = deepcopy(valid_advise_intake_runtime_execution())
    payload["aggregateBlockersSatisfied"] = ()
    assert not advise_intake_runtime_execution_is_valid(payload)

    payload = deepcopy(valid_advise_intake_runtime_execution())
    payload["remainingCertificationBlockers"] = ()
    assert not advise_intake_runtime_execution_is_valid(payload)

    payload = deepcopy(valid_advise_intake_runtime_execution())
    payload["producerCertificationBlockersRetained"] = ()
    assert not advise_intake_runtime_execution_is_valid(payload)


def test_advise_intake_runtime_execution_rejects_runtime_metadata_drift() -> None:
    payload = deepcopy(valid_advise_intake_runtime_execution())
    payload["runtimeMode"] = "manual_claim"
    assert not advise_intake_runtime_execution_is_valid(payload)

    payload = deepcopy(valid_advise_intake_runtime_execution())
    payload["generatedAtUtc"] = "2026-07-22T00:00:00"
    assert not advise_intake_runtime_execution_is_valid(payload)

    payload = deepcopy(valid_advise_intake_runtime_execution())
    payload["sourceAuthority"] = ()
    assert not advise_intake_runtime_execution_is_valid(payload)

    payload = deepcopy(valid_advise_intake_runtime_execution())
    payload["runtimeChecks"]["routeServingObserved"] = False  # type: ignore[index]
    assert not advise_intake_runtime_execution_is_valid(payload)


def test_advise_intake_runtime_execution_rejects_payload_and_receipt_shape_drift() -> None:
    payload = deepcopy(valid_advise_intake_runtime_execution())
    payload["unexpectedClaim"] = True
    assert not advise_intake_runtime_execution_is_valid(payload)

    payload = deepcopy(valid_advise_intake_runtime_execution())
    payload["receiptEvidence"]["accepted"]["unexpectedField"] = True  # type: ignore[index]
    assert not advise_intake_runtime_execution_is_valid(payload)


def test_load_advise_intake_runtime_execution_from_env_returns_payload_and_relative_ref(
    monkeypatch,
    tmp_path: Path,
) -> None:
    proof_path = tmp_path / "advise-proof.json"
    proof_path.write_text("{}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(ADVISE_INTAKE_RUNTIME_EXECUTION_ENV, str(proof_path))

    payload, artifact_ref = load_advise_intake_runtime_execution_from_env()

    assert payload == {}
    assert artifact_ref == "advise-proof.json"


def test_load_advise_intake_runtime_execution_from_env_rejects_non_object(
    monkeypatch,
    tmp_path: Path,
) -> None:
    proof_path = tmp_path / "advise-proof.json"
    proof_path.write_text("[]", encoding="utf-8")
    monkeypatch.setenv(ADVISE_INTAKE_RUNTIME_EXECUTION_ENV, str(proof_path))

    try:
        load_advise_intake_runtime_execution_from_env()
    except ValueError as exc:
        assert ADVISE_INTAKE_RUNTIME_EXECUTION_ENV in str(exc)
    else:  # pragma: no cover - defensive assertion path
        raise AssertionError("non-object proof payload must be rejected")


def test_load_advise_intake_runtime_execution_from_env_uses_env_ref_for_external_path(
    monkeypatch,
    tmp_path: Path,
) -> None:
    cwd = tmp_path / "repo"
    external = tmp_path / "external"
    cwd.mkdir()
    external.mkdir()
    proof_path = external / "advise-proof.json"
    proof_path.write_text("{}", encoding="utf-8")
    monkeypatch.chdir(cwd)
    monkeypatch.setenv(ADVISE_INTAKE_RUNTIME_EXECUTION_ENV, str(proof_path))

    payload, artifact_ref = load_advise_intake_runtime_execution_from_env()

    assert payload == {}
    assert artifact_ref == f"{ADVISE_INTAKE_RUNTIME_EXECUTION_ENV} artifact"
