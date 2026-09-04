from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.application.downstream_realization.advise_intake_runtime_execution import (
    ADVISE_INTAKE_RUNTIME_EXECUTION_ENV,
    REMAINING_ADVISE_INTAKE_RUNTIME_BLOCKERS,
    _owner_realization_matches,
    _same_owner_identity,
    advise_intake_runtime_execution_is_valid,
    build_advise_intake_runtime_execution_payload,
    load_advise_intake_runtime_execution_from_env,
)
from tests.unit.downstream_realization.fixtures import (
    valid_advise_intake_runtime_execution,
)
from tests.unit.downstream_realization.runtime_execution_test_support import (
    nested_payload_section,
    receipt_evidence_for_builder,
    set_nested_payload_value,
    set_receipt_evidence_value,
)


def test_advise_intake_runtime_execution_accepts_bounded_live_receipts() -> None:
    payload = valid_advise_intake_runtime_execution()

    assert advise_intake_runtime_execution_is_valid(payload)
    assert payload["aggregateBlockersSatisfied"] == ("advise_live_contract_proof_missing",)
    assert payload["remainingCertificationBlockers"] == REMAINING_ADVISE_INTAKE_RUNTIME_BLOCKERS
    assert nested_payload_section(payload, "nonProofClaims")["supportedFeaturePromoted"] is False


def test_advise_intake_runtime_execution_builder_binds_contract_checks() -> None:
    baseline = valid_advise_intake_runtime_execution()

    payload = build_advise_intake_runtime_execution_payload(
        generated_at_utc=datetime(2026, 7, 22, 0, 0, tzinfo=UTC),
        repository_root=Path(__file__).resolve().parents[3],
        advise_root=None,
        runtime_mode="local_asgi_testclient",
        receipt_evidence=receipt_evidence_for_builder(baseline),
        submitted_intent_evidence=nested_payload_section(baseline, "submittedIntentEvidence"),
        owner_realization_evidence=nested_payload_section(baseline, "ownerRealizationEvidence"),
    )

    assert payload["runtimeChecks"]["acceptedReceiptObserved"] is True
    assert payload["runtimeChecks"]["tenantIsolationObserved"] is True
    assert payload["runtimeChecks"]["concurrentDuplicateConvergenceObserved"] is True
    assert payload["runtimeChecks"]["ownerRealizationReadbackObserved"] is True


@pytest.mark.parametrize(
    ("receipt_name", "field", "replacement"),
    (
        ("concurrentAccepted", "ownerIdentityDigest", "sha256:" + "1" * 64),
        ("concurrentReplay", "scopeDigest", "sha256:" + "2" * 64),
        ("acceptedReplay", "ownerIdentityDigest", "sha256:" + "3" * 64),
    ),
)
def test_advise_intake_runtime_execution_rejects_divergent_owner_identity(
    receipt_name: str,
    field: str,
    replacement: str,
) -> None:
    payload = deepcopy(valid_advise_intake_runtime_execution())
    set_receipt_evidence_value(payload, receipt_name, field, replacement)

    assert not advise_intake_runtime_execution_is_valid(payload)


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("ownerIdentityDigest", "sha256:" + "4" * 64),
        ("scopeDigest", "sha256:" + "5" * 64),
        ("sourceIntentDigest", "sha256:" + "6" * 64),
        ("currentSourceEventVersion", 2),
        ("currentStatus", "REJECTED"),
    ),
)
def test_advise_intake_runtime_execution_rejects_owner_readback_mismatch(
    field: str,
    replacement: object,
) -> None:
    payload = deepcopy(valid_advise_intake_runtime_execution())
    payload["ownerRealizationEvidence"][field] = replacement  # type: ignore[index]

    assert not advise_intake_runtime_execution_is_valid(payload)


def test_advise_intake_runtime_execution_builder_requires_aware_generation_time() -> None:
    baseline = valid_advise_intake_runtime_execution()

    try:
        build_advise_intake_runtime_execution_payload(
            generated_at_utc=datetime(2026, 7, 22, 0, 0),
            repository_root=Path(__file__).resolve().parents[3],
            advise_root=None,
            runtime_mode="local_asgi_testclient",
            receipt_evidence=receipt_evidence_for_builder(baseline),
            submitted_intent_evidence=nested_payload_section(baseline, "submittedIntentEvidence"),
            owner_realization_evidence=nested_payload_section(baseline, "ownerRealizationEvidence"),
        )
    except ValueError as exc:
        assert "timezone-aware" in str(exc)
    else:  # pragma: no cover - defensive assertion path
        raise AssertionError("naive generation time must be rejected")


def test_advise_intake_runtime_execution_rejects_supported_feature_overclaim() -> None:
    payload = deepcopy(valid_advise_intake_runtime_execution())
    set_nested_payload_value(payload, "nonProofClaims", "supportedFeaturePromoted", True)

    assert not advise_intake_runtime_execution_is_valid(payload)


def test_advise_intake_runtime_execution_rejects_missing_replay_evidence() -> None:
    payload = deepcopy(valid_advise_intake_runtime_execution())
    set_receipt_evidence_value(payload, "acceptedReplay", "intakeStatus", "ACCEPTED")

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
    payload["ownerReadRoute"] = "GET /untrusted/latest"
    assert not advise_intake_runtime_execution_is_valid(payload)

    payload = deepcopy(valid_advise_intake_runtime_execution())
    set_nested_payload_value(payload, "runtimeChecks", "routeServingObserved", False)
    assert not advise_intake_runtime_execution_is_valid(payload)


def test_advise_intake_runtime_execution_rejects_payload_and_receipt_shape_drift() -> None:
    payload = deepcopy(valid_advise_intake_runtime_execution())
    payload["unexpectedClaim"] = True
    assert not advise_intake_runtime_execution_is_valid(payload)

    payload = deepcopy(valid_advise_intake_runtime_execution())
    payload["submittedIntentEvidence"]["scopeDigest"] = "not-a-digest"  # type: ignore[index]
    assert not advise_intake_runtime_execution_is_valid(payload)

    payload = deepcopy(valid_advise_intake_runtime_execution())
    set_receipt_evidence_value(payload, "accepted", "unexpectedField", True)
    assert not advise_intake_runtime_execution_is_valid(payload)


@pytest.mark.parametrize(
    ("section", "replacement"),
    (
        ("ownerRealizationEvidence", None),
        ("submittedIntentEvidence", None),
    ),
)
def test_advise_intake_runtime_execution_rejects_non_object_causal_evidence(
    section: str,
    replacement: object,
) -> None:
    payload = deepcopy(valid_advise_intake_runtime_execution())
    payload[section] = replacement

    assert not advise_intake_runtime_execution_is_valid(payload)


def test_advise_intake_runtime_execution_rejects_invalid_owner_evidence_digest() -> None:
    payload = deepcopy(valid_advise_intake_runtime_execution())
    payload["ownerRealizationEvidence"]["sourceIntentDigest"] = "not-a-digest"  # type: ignore[index]

    assert not advise_intake_runtime_execution_is_valid(payload)


def test_owner_realization_comparison_rejects_non_object_accepted_receipt() -> None:
    baseline = valid_advise_intake_runtime_execution()

    assert not _owner_realization_matches(
        nested_payload_section(baseline, "ownerRealizationEvidence"),
        None,
        nested_payload_section(baseline, "submittedIntentEvidence"),
    )


def test_owner_identity_comparison_rejects_non_object_evidence() -> None:
    assert _same_owner_identity({}, None) is False


def test_load_advise_intake_runtime_execution_from_env_returns_payload_and_relative_ref(
    monkeypatch: pytest.MonkeyPatch,
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
    monkeypatch: pytest.MonkeyPatch,
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
    monkeypatch: pytest.MonkeyPatch,
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
