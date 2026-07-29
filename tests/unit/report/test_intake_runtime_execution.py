from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, cast

import pytest

from app.application.report.intake_runtime_execution import (
    REMAINING_REPORT_INTAKE_RUNTIME_BLOCKERS,
    REPORT_INTAKE_RUNTIME_BLOCKERS_SATISFIED,
    REPORT_INTAKE_RUNTIME_EXECUTION_ENV,
    REPORT_INTAKE_RUNTIME_EXECUTION_SCHEMA_VERSION,
    build_report_intake_runtime_execution_payload,
    load_report_intake_runtime_execution_from_env,
    report_intake_runtime_execution_is_valid,
)
from tests.unit.downstream_realization.fixtures import valid_report_intake_runtime_execution


def test_report_intake_runtime_execution_accepts_receipt_bound_runtime_proof() -> None:
    payload = valid_report_intake_runtime_execution()

    assert report_intake_runtime_execution_is_valid(payload)
    assert payload["schemaVersion"] == REPORT_INTAKE_RUNTIME_EXECUTION_SCHEMA_VERSION
    assert payload["aggregateBlockersSatisfied"] == REPORT_INTAKE_RUNTIME_BLOCKERS_SATISFIED
    assert payload["remainingCertificationBlockers"] == REMAINING_REPORT_INTAKE_RUNTIME_BLOCKERS
    assert "lotus_report_live_intake_route_proof_missing" in (payload["aggregateBlockersSatisfied"])
    assert (
        "report_evidence_pack_live_materialization_proof_missing"
        in (payload["remainingCertificationBlockers"])
    )
    assert payload["nonProofClaims"]["materializationCertified"] is False  # type: ignore[index]
    assert payload["nonProofClaims"]["clientPublicationAuthorized"] is False  # type: ignore[index]
    assert payload["nonProofClaims"]["supportedFeaturePromoted"] is False  # type: ignore[index]


def test_report_intake_runtime_execution_builder_binds_runtime_checks() -> None:
    baseline = valid_report_intake_runtime_execution()

    payload = build_report_intake_runtime_execution_payload(
        generated_at_utc=datetime(2026, 7, 22, 0, 0, tzinfo=UTC),
        repository_root=Path(__file__).resolve().parents[3],
        report_root=None,
        runtime_mode="local_asgi_testclient",
        receipt_evidence=baseline["receiptEvidence"],  # type: ignore[arg-type]
    )

    assert payload["runtimeChecks"]["acceptedReceiptObserved"] is True
    assert payload["runtimeChecks"]["acceptedReplayReceiptObserved"] is True
    assert payload["runtimeChecks"]["idempotencyConflictObserved"] is True
    assert payload["runtimeChecks"]["missingIdempotencyKeyObserved"] is True
    assert payload["runtimeChecks"]["clientPublicationDeniedObserved"] is True
    assert payload["runtimeChecks"]["renderClaimDeniedObserved"] is True
    assert payload["runtimeChecks"]["materializationAuthorityRetained"] is True
    assert payload["runtimeChecks"]["renderArchiveAuthorityRetained"] is True


def test_report_intake_runtime_execution_builder_requires_aware_generation_time() -> None:
    baseline = valid_report_intake_runtime_execution()

    with pytest.raises(ValueError, match="timezone-aware"):
        build_report_intake_runtime_execution_payload(
            generated_at_utc=datetime(2026, 7, 22, 0, 0),
            repository_root=Path(__file__).resolve().parents[3],
            report_root=None,
            runtime_mode="local_asgi_testclient",
            receipt_evidence=baseline["receiptEvidence"],  # type: ignore[arg-type]
        )


def test_report_intake_runtime_execution_rejects_materialization_overclaim() -> None:
    payload = deepcopy(valid_report_intake_runtime_execution())
    payload["nonProofClaims"]["materializationCertified"] = True  # type: ignore[index]

    assert not report_intake_runtime_execution_is_valid(payload)


def test_report_intake_runtime_execution_rejects_supported_feature_promotion() -> None:
    payload = deepcopy(valid_report_intake_runtime_execution())
    receipt_evidence = cast(dict[str, Any], payload["receiptEvidence"])
    accepted = cast(dict[str, Any], receipt_evidence["accepted"])
    accepted["supportedFeaturePromoted"] = True

    assert not report_intake_runtime_execution_is_valid(payload)


def test_report_intake_runtime_execution_rejects_receipt_digest_drift() -> None:
    payload = deepcopy(valid_report_intake_runtime_execution())
    receipt_evidence = cast(dict[str, Any], payload["receiptEvidence"])
    accepted = cast(dict[str, Any], receipt_evidence["accepted"])
    accepted["reportJobCreated"] = True

    assert not report_intake_runtime_execution_is_valid(payload)


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("schemaVersion", "lotus-idea.report-intake.runtime-execution.v0"),
        ("runtimeMode", "caller_asserted"),
        ("generatedAtUtc", "2026-07-22T00:00:00"),
        ("evidenceRefs", []),
        ("aggregateBlockersSatisfied", []),
        ("remainingCertificationBlockers", []),
        ("sourceAuthority", {}),
        ("nonProofClaims", {}),
        ("runtimeChecks", {}),
        ("receiptEvidence", {}),
    ],
)
def test_report_intake_runtime_execution_rejects_malformed_proof_fields(
    field: str,
    invalid_value: object,
) -> None:
    payload = deepcopy(valid_report_intake_runtime_execution())
    payload[field] = invalid_value

    assert not report_intake_runtime_execution_is_valid(payload)


def test_report_intake_runtime_execution_rejects_unknown_top_level_field() -> None:
    payload = deepcopy(valid_report_intake_runtime_execution())
    payload["unsupportedClaim"] = True

    assert not report_intake_runtime_execution_is_valid(payload)


def test_report_intake_runtime_execution_rejects_non_mapping_receipt() -> None:
    payload = deepcopy(valid_report_intake_runtime_execution())
    receipt_evidence = cast(dict[str, Any], payload["receiptEvidence"])
    receipt_evidence["accepted"] = "not-a-receipt"

    assert not report_intake_runtime_execution_is_valid(payload)


def test_load_report_intake_runtime_execution_from_env_returns_empty_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(REPORT_INTAKE_RUNTIME_EXECUTION_ENV, raising=False)

    assert load_report_intake_runtime_execution_from_env() == (None, None)


def test_load_report_intake_runtime_execution_from_env_returns_payload_and_ref(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    proof_path = tmp_path / "report-intake-runtime-proof.json"
    proof_path.write_text(json.dumps(valid_report_intake_runtime_execution()))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(REPORT_INTAKE_RUNTIME_EXECUTION_ENV, str(proof_path))

    payload, artifact_ref = load_report_intake_runtime_execution_from_env()

    assert payload is not None
    assert report_intake_runtime_execution_is_valid(payload)
    assert artifact_ref == "report-intake-runtime-proof.json"


def test_load_report_intake_runtime_execution_from_env_rejects_non_object(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    proof_path = tmp_path / "report-intake-runtime-proof.json"
    proof_path.write_text(json.dumps(["not", "an", "object"]))
    monkeypatch.setenv(REPORT_INTAKE_RUNTIME_EXECUTION_ENV, str(proof_path))

    with pytest.raises(ValueError, match="must reference a JSON object"):
        load_report_intake_runtime_execution_from_env()


def test_load_report_intake_runtime_execution_from_env_uses_safe_external_ref(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    proof_path = tmp_path / "external-report-intake-runtime-proof.json"
    proof_path.write_text(json.dumps(valid_report_intake_runtime_execution()))
    monkeypatch.chdir(Path(__file__).resolve().parents[3])
    monkeypatch.setenv(REPORT_INTAKE_RUNTIME_EXECUTION_ENV, str(proof_path))

    payload, artifact_ref = load_report_intake_runtime_execution_from_env()

    assert payload is not None
    assert artifact_ref == f"{REPORT_INTAKE_RUNTIME_EXECUTION_ENV} artifact"


def test_report_intake_runtime_generator_uses_isolated_intake_ledger() -> None:
    generator_source = (
        Path(__file__)
        .resolve()
        .parents[3]
        .joinpath("scripts/report/generate_intake_runtime_execution.py")
        .read_text(encoding="utf-8")
    )

    assert generator_source.count("TestClient(app)") == 1
    assert "IdeaEvidenceIntakeLedger(Path(tmp_path)" in generator_source
    assert 'headers.pop("Idempotency-Key")' in generator_source
    assert "client_publication_denied = client.post" in generator_source
    assert "render_claim_denied = client.post" in generator_source
    assert "app.dependency_overrides.clear()" in generator_source
