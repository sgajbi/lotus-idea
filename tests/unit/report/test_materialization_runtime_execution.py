from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, cast

import pytest

from app.application.report.materialization_runtime_execution import (
    REMAINING_REPORT_MATERIALIZATION_RUNTIME_BLOCKERS,
    REPORT_RENDER_ARCHIVE_OWNER_MAINLINE_EVIDENCE,
    REPORT_MATERIALIZATION_RUNTIME_BLOCKERS_SATISFIED,
    REPORT_MATERIALIZATION_RUNTIME_EXECUTION_ENV,
    REPORT_MATERIALIZATION_RUNTIME_EXECUTION_SCHEMA_VERSION,
    build_report_materialization_runtime_execution_payload,
    load_report_materialization_runtime_execution_from_env,
    report_materialization_runtime_execution_is_valid,
)
from tests.unit.downstream_realization.fixtures import (
    valid_report_materialization_runtime_execution,
)


def test_report_materialization_runtime_execution_accepts_receipt_bound_runtime_proof() -> None:
    payload = valid_report_materialization_runtime_execution()

    assert report_materialization_runtime_execution_is_valid(payload)
    assert payload["schemaVersion"] == REPORT_MATERIALIZATION_RUNTIME_EXECUTION_SCHEMA_VERSION
    assert payload["aggregateBlockersSatisfied"] == (
        REPORT_MATERIALIZATION_RUNTIME_BLOCKERS_SATISFIED
    )
    assert payload["remainingCertificationBlockers"] == (
        REMAINING_REPORT_MATERIALIZATION_RUNTIME_BLOCKERS
    )
    assert payload["ownerMainlineEvidence"] == REPORT_RENDER_ARCHIVE_OWNER_MAINLINE_EVIDENCE
    assert "rendered_output_creation_missing" in payload["aggregateBlockersSatisfied"]
    assert "archive_record_creation_missing" in payload["aggregateBlockersSatisfied"]
    assert "client_publication_authority_blocked" in payload["remainingCertificationBlockers"]
    assert payload["nonProofClaims"]["supportedFeaturePromoted"] is False  # type: ignore[index]
    assert payload["nonProofClaims"]["clientPublicationAuthorized"] is False  # type: ignore[index]
    assert payload["nonProofClaims"]["renderedOutputCertified"] is False  # type: ignore[index]
    assert payload["nonProofClaims"]["archiveRecordCertified"] is False  # type: ignore[index]


def test_report_materialization_runtime_execution_builder_binds_runtime_checks() -> None:
    baseline = valid_report_materialization_runtime_execution()

    payload = build_report_materialization_runtime_execution_payload(
        generated_at_utc=datetime(2026, 7, 22, 0, 0, tzinfo=UTC),
        repository_root=Path(__file__).resolve().parents[3],
        report_root=None,
        runtime_mode="local_asgi_testclient",
        receipt_evidence=baseline["receiptEvidence"],  # type: ignore[arg-type]
    )

    assert payload["runtimeChecks"]["acceptedArchivedReceiptObserved"] is True
    assert payload["runtimeChecks"]["archiveFailureReceiptObserved"] is True
    assert payload["runtimeChecks"]["clientPublicationDeniedObserved"] is True
    assert payload["runtimeChecks"]["renderedOutputCreationObserved"] is True
    assert payload["runtimeChecks"]["archiveRecordCreationObserved"] is True
    assert payload["runtimeChecks"]["renderOwnerMainlineEvidenceConsumed"] is True
    assert payload["runtimeChecks"]["archiveOwnerMainlineEvidenceConsumed"] is True


def test_report_materialization_runtime_execution_builder_requires_aware_generation_time() -> None:
    baseline = valid_report_materialization_runtime_execution()

    with pytest.raises(ValueError, match="timezone-aware"):
        build_report_materialization_runtime_execution_payload(
            generated_at_utc=datetime(2026, 7, 22, 0, 0),
            repository_root=Path(__file__).resolve().parents[3],
            report_root=None,
            runtime_mode="local_asgi_testclient",
            receipt_evidence=baseline["receiptEvidence"],  # type: ignore[arg-type]
        )


def test_report_materialization_runtime_execution_rejects_publication_overclaim() -> None:
    payload = deepcopy(valid_report_materialization_runtime_execution())
    payload["nonProofClaims"]["clientPublicationAuthorized"] = True  # type: ignore[index]

    assert not report_materialization_runtime_execution_is_valid(payload)


def test_report_materialization_runtime_execution_rejects_supported_feature_promotion() -> None:
    payload = deepcopy(valid_report_materialization_runtime_execution())
    payload["receiptEvidence"]["acceptedArchived"]["supportedFeaturePromoted"] = True  # type: ignore[index]

    assert not report_materialization_runtime_execution_is_valid(payload)


def test_report_materialization_runtime_execution_rejects_render_archive_certification_overclaim() -> (
    None
):
    payload = deepcopy(valid_report_materialization_runtime_execution())
    payload["nonProofClaims"]["renderedOutputCertified"] = True  # type: ignore[index]

    assert not report_materialization_runtime_execution_is_valid(payload)


def test_report_materialization_runtime_execution_rejects_owner_evidence_drift() -> None:
    payload = deepcopy(valid_report_materialization_runtime_execution())
    owner_mainline_evidence = payload["ownerMainlineEvidence"]
    assert isinstance(owner_mainline_evidence, tuple)
    owner_evidence = [dict(cast(dict[str, Any], item)) for item in owner_mainline_evidence]
    owner_evidence[0] = dict(owner_evidence[0], mergedMainCommitSha="0" * 40)
    payload["ownerMainlineEvidence"] = owner_evidence

    assert not report_materialization_runtime_execution_is_valid(payload)


def test_report_materialization_runtime_execution_rejects_missing_receipt_path() -> None:
    payload = deepcopy(valid_report_materialization_runtime_execution())
    receipt_evidence = cast(dict[str, Any], payload["receiptEvidence"])
    del receipt_evidence["archiveFailure"]

    assert not report_materialization_runtime_execution_is_valid(payload)


def test_report_materialization_runtime_execution_rejects_receipt_digest_drift() -> None:
    payload = deepcopy(valid_report_materialization_runtime_execution())
    receipt_evidence = cast(dict[str, Any], payload["receiptEvidence"])
    json_only_accepted = cast(dict[str, Any], receipt_evidence["jsonOnlyAccepted"])
    json_only_accepted["materializationStatus"] = "archived"

    assert not report_materialization_runtime_execution_is_valid(payload)


def test_report_materialization_runtime_execution_rejects_source_authority_drift() -> None:
    payload = deepcopy(valid_report_materialization_runtime_execution())
    payload["sourceAuthority"] = ()

    assert not report_materialization_runtime_execution_is_valid(payload)


def test_load_report_materialization_runtime_execution_from_env_returns_payload_and_ref(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    proof_path = tmp_path / "report-runtime-proof.json"
    proof_path.write_text(json.dumps(valid_report_materialization_runtime_execution()))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(REPORT_MATERIALIZATION_RUNTIME_EXECUTION_ENV, str(proof_path))

    payload, artifact_ref = load_report_materialization_runtime_execution_from_env()

    assert payload is not None
    assert report_materialization_runtime_execution_is_valid(payload)
    assert artifact_ref == "report-runtime-proof.json"


def test_load_report_materialization_runtime_execution_from_env_rejects_non_object(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    proof_path = tmp_path / "report-runtime-proof.json"
    proof_path.write_text("[]", encoding="utf-8")
    monkeypatch.setenv(REPORT_MATERIALIZATION_RUNTIME_EXECUTION_ENV, str(proof_path))

    with pytest.raises(ValueError, match=REPORT_MATERIALIZATION_RUNTIME_EXECUTION_ENV):
        load_report_materialization_runtime_execution_from_env()
