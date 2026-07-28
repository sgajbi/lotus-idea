from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

import pytest

from app.application.downstream_outcome_certification import (
    DOWNSTREAM_OUTCOME_NON_PROOF_CLAIMS,
    REQUIRED_IDEA_OUTCOME_WINDOWS,
    build_downstream_outcome_certification_payload,
    downstream_outcome_certification_is_valid,
    validate_downstream_outcome_certification,
    validate_downstream_outcome_certification_contract,
)
from app.domain.proof_evidence import EvidenceClass
from tests.unit.downstream_realization.fixtures import (
    valid_advise_intake_runtime_execution,
    valid_manage_intake_runtime_execution,
    valid_report_materialization_runtime_execution,
)


GENERATED_AT = datetime(2026, 7, 22, 0, 0, tzinfo=UTC)


def test_downstream_outcome_certification_aggregates_owner_receipts_without_closure() -> None:
    payload = _valid_payload()

    assert downstream_outcome_certification_is_valid(payload)
    assert payload["aggregateOutcomeProofValid"] is True
    assert payload["issue379ClosureReady"] is False
    assert payload["aggregateBlockersSatisfied"] == []
    assert payload["remainingCertificationBlockers"] == [
        "external_downstream_certification_blocked",
        "production_identity_not_certified",
        "supported_feature_promotion_missing",
        "client_publication_authority_blocked",
    ]
    assert [proof["proofId"] for proof in payload["ownerRuntimeProofs"]] == [
        "lotus-advise:proposal-intake",
        "lotus-manage:action-intake",
        "lotus-report:evidence-pack-materialization",
    ]
    assert all(
        proof["evidenceClass"] == EvidenceClass.RUNTIME_EXECUTION.value
        and proof["runtimeProofValid"] is True
        and proof["nonProofClaimsRetained"] is True
        for proof in payload["ownerRuntimeProofs"]
    )
    assert [
        window["window"]
        for window in payload["ideaDurableSubmissionProof"]["coveredOutcomeWindows"]
    ] == list(REQUIRED_IDEA_OUTCOME_WINDOWS)
    assert payload["ideaDurableSubmissionProof"]["recordsDownstreamOutcome"] is False
    assert payload["ideaDurableSubmissionProof"]["grantsDownstreamAuthority"] is False
    assert payload["readinessAndDiagnosticsCoverage"]["operatorDiagnosticStates"] == [
        "pending",
        "uncertain",
        "terminal_success",
        "terminal_rejection",
    ]
    assert tuple(payload["nonProofClaims"]) == DOWNSTREAM_OUTCOME_NON_PROOF_CLAIMS
    assert all(value is False for value in payload["nonProofClaims"].values())


def test_downstream_outcome_certification_rejects_static_or_invalid_owner_proof() -> None:
    invalid_report = deepcopy(valid_report_materialization_runtime_execution())
    invalid_report["evidenceClass"] = EvidenceClass.SOURCE_CONTRACT.value

    payload = _valid_payload(report_materialization_runtime_execution_proof=invalid_report)

    errors = validate_downstream_outcome_certification(payload)
    assert "lotus-report:evidence-pack-materialization evidenceClass must be runtime_execution" in (
        errors
    )
    assert "lotus-report:evidence-pack-materialization runtime proof must be valid" in errors
    assert "proofChecks.ownerRuntimeProofsValid must be true" in errors
    assert "proofChecks.ownerRuntimeProofsAreRuntimeExecution must be true" in errors


def test_downstream_outcome_certification_rejects_partial_idea_windows() -> None:
    payload = _valid_payload()
    payload["ideaDurableSubmissionProof"]["coveredOutcomeWindows"].pop()

    errors = validate_downstream_outcome_certification(payload)

    assert "Idea durable proof must cover every #379 outcome window" in errors


def test_downstream_outcome_certification_rejects_promotion_claims() -> None:
    payload = _valid_payload()
    payload["nonProofClaims"]["supportedFeaturePromoted"] = True
    payload["ideaDurableSubmissionProof"]["supportedFeaturePromoted"] = True

    errors = validate_downstream_outcome_certification(payload)

    assert "nonProofClaims.supportedFeaturePromoted must be false" in errors
    assert "ideaDurableSubmissionProof.supportedFeaturePromoted must be false" in errors


def test_downstream_outcome_certification_contract_gate_has_local_evidence() -> None:
    assert (
        validate_downstream_outcome_certification_contract(
            repository_root=Path.cwd(),
        )
        == []
    )


def test_downstream_outcome_certification_requires_timezone_aware_generation_time() -> None:
    with pytest.raises(ValueError, match="generated_at_utc must be timezone-aware"):
        build_downstream_outcome_certification_payload(
            generated_at_utc=datetime(2026, 7, 22, 0, 0),
            repository_root=Path.cwd(),
            advise_intake_runtime_execution_proof=valid_advise_intake_runtime_execution(),
            advise_intake_runtime_execution_proof_ref=(
                "output/downstream/advise-intake-runtime-execution-proof.json"
            ),
            manage_intake_runtime_execution_proof=valid_manage_intake_runtime_execution(),
            manage_intake_runtime_execution_proof_ref=(
                "output/downstream/manage-intake-runtime-execution-proof.json"
            ),
            report_materialization_runtime_execution_proof=(
                valid_report_materialization_runtime_execution()
            ),
            report_materialization_runtime_execution_proof_ref=(
                "output/report/materialization-runtime-execution-proof.json"
            ),
        )


def test_downstream_outcome_certification_rejects_top_level_contract_drift() -> None:
    payload = _valid_payload()
    payload["unexpectedField"] = "drift"
    payload.pop("schemaVersion")
    payload["repository"] = "lotus-core"
    payload["generatedAtUtc"] = "2026-07-22T00:00:00"
    payload["rfc"] = "RFC-9999"
    payload["proofType"] = "static_claim"
    payload["proofScope"] = "unsupported_scope"
    payload["evidenceClass"] = EvidenceClass.SOURCE_CONTRACT.value
    payload["sourceRepository"] = "lotus-report"
    payload["aggregateOutcomeProofValid"] = False
    payload["issue379ClosureReady"] = True
    payload["evidenceRefs"] = []
    payload["sliceIds"] = ["RFC-0002/slice-12"]
    payload["trackingIssues"] = ["sgajbi/lotus-idea#999"]
    payload["aggregateBlockersSatisfied"] = ["client_publication_authority_blocked"]
    payload["remainingCertificationBlockers"] = ["production_identity_not_certified"]

    errors = validate_downstream_outcome_certification(payload)

    assert "unknown downstream outcome certification fields: ['unexpectedField']" in errors
    assert "missing downstream outcome certification fields: ['schemaVersion']" in errors
    assert "schemaVersion must be the downstream outcome certification schema" in errors
    assert "repository must be lotus-idea" in errors
    assert "generatedAtUtc must be timezone-aware" in errors
    assert "rfc must be RFC-0002" in errors
    assert "proofType must be downstream_outcome_certification" in errors
    assert "proofScope must be the governed downstream outcome boundary" in errors
    assert "evidenceClass must be runtime_execution" in errors
    assert "sourceRepository must be lotus-idea" in errors
    assert "aggregateOutcomeProofValid must be true" in errors
    assert "issue379ClosureReady must stay false for this partial proof" in errors
    assert "evidenceRefs must match the governed downstream outcome contract" in errors
    assert "sliceIds must match the governed downstream outcome contract" in errors
    assert "trackingIssues must match the governed downstream outcome contract" in errors
    assert "aggregateBlockersSatisfied must be empty for partial #379 proof" in errors
    assert (
        "remainingCertificationBlockers must match the governed downstream outcome contract"
        in errors
    )


def test_downstream_outcome_certification_rejects_non_array_contract_sequences() -> None:
    payload = _valid_payload()
    payload["sliceIds"] = "RFC-0002/slice-12"
    payload["trackingIssues"] = "sgajbi/lotus-idea#379"
    payload["evidenceRefs"] = "src/app/application/downstream_outcome_certification.py"
    payload["remainingCertificationBlockers"] = "production_identity_not_certified"

    errors = validate_downstream_outcome_certification(payload)

    assert "sliceIds must be a JSON array" in errors
    assert "trackingIssues must be a JSON array" in errors
    assert "evidenceRefs must be a JSON array" in errors
    assert "remainingCertificationBlockers must be a JSON array" in errors


def test_downstream_outcome_certification_rejects_malformed_owner_runtime_proofs() -> None:
    payload = _valid_payload()
    payload["ownerRuntimeProofs"] = "not-a-list"

    assert validate_downstream_outcome_certification(payload) == [
        "ownerRuntimeProofs must be a JSON array"
    ]

    payload = _valid_payload()
    payload["ownerRuntimeProofs"] = ["not-an-object"]

    assert validate_downstream_outcome_certification(payload) == [
        "ownerRuntimeProofs entries must be objects"
    ]

    payload = _valid_payload()
    payload["ownerRuntimeProofs"][0]["unexpected"] = "drift"

    assert validate_downstream_outcome_certification(payload) == [
        "ownerRuntimeProofs entries must match the governed summary shape"
    ]

    payload = _valid_payload()
    payload["ownerRuntimeProofs"][0]["proofId"] = 123

    assert validate_downstream_outcome_certification(payload) == [
        "ownerRuntimeProofs proofId must be text",
    ]


def test_downstream_outcome_certification_rejects_weak_owner_runtime_evidence() -> None:
    payload = _valid_payload()
    owner_proof = payload["ownerRuntimeProofs"][0]
    owner_proof["evidenceClass"] = EvidenceClass.SOURCE_CONTRACT.value
    owner_proof["runtimeProofValid"] = False
    owner_proof["nonProofClaimsRetained"] = False
    owner_proof["proofDigest"] = "not-a-sha256-digest"
    owner_proof["receiptWindows"] = []

    errors = validate_downstream_outcome_certification(payload)

    assert "lotus-advise:proposal-intake evidenceClass must be runtime_execution" in errors
    assert "lotus-advise:proposal-intake runtime proof must be valid" in errors
    assert "lotus-advise:proposal-intake must retain non-proof claims" in errors
    assert "lotus-advise:proposal-intake proofDigest must be a sha256 digest" in errors
    assert "lotus-advise:proposal-intake receiptWindows must be non-empty text" in errors


def test_downstream_outcome_certification_rejects_malformed_window_entries() -> None:
    payload = _valid_payload()
    payload["ideaDurableSubmissionProof"]["coveredOutcomeWindows"] = "not-a-list"

    errors = validate_downstream_outcome_certification(payload)

    assert "Idea durable proof must cover every #379 outcome window" in errors

    payload = _valid_payload()
    payload["ideaDurableSubmissionProof"]["coveredOutcomeWindows"] = ["not-an-object"]

    errors = validate_downstream_outcome_certification(payload)

    assert "Idea durable proof must cover every #379 outcome window" in errors

    payload = _valid_payload()
    payload["ideaDurableSubmissionProof"]["coveredOutcomeWindows"][0]["window"] = 123

    errors = validate_downstream_outcome_certification(payload)

    assert "Idea durable proof must cover every #379 outcome window" in errors

    payload = _valid_payload()
    payload["ideaDurableSubmissionProof"]["coveredOutcomeWindows"][0]["evidenceRefs"] = []

    errors = validate_downstream_outcome_certification(payload)

    assert "Idea durable proof must cover every #379 outcome window" in errors


def test_downstream_outcome_certification_rejects_owner_runtime_order_drift() -> None:
    payload = _valid_payload()
    payload["ownerRuntimeProofs"] = list(reversed(payload["ownerRuntimeProofs"]))

    errors = validate_downstream_outcome_certification(payload)

    assert "ownerRuntimeProofs must match Advise, Manage, and Report proof order" in errors


def test_downstream_outcome_certification_rejects_malformed_idea_durable_proof() -> None:
    payload = _valid_payload()
    payload["ideaDurableSubmissionProof"] = "not-an-object"

    assert validate_downstream_outcome_certification(payload) == [
        "ideaDurableSubmissionProof must be an object"
    ]

    payload = _valid_payload()
    payload["ideaDurableSubmissionProof"]["unexpected"] = "drift"

    assert validate_downstream_outcome_certification(payload) == [
        "ideaDurableSubmissionProof must match the governed shape"
    ]

    payload = _valid_payload()
    durable_proof = payload["ideaDurableSubmissionProof"]
    durable_proof["evidenceClass"] = EvidenceClass.SOURCE_CONTRACT.value
    durable_proof["noAutomaticRetryAfterUncertainOutcome"] = False
    durable_proof["claimBeforeCallDurability"] = False
    durable_proof["responseBeforeLocalCommitRequiresReconciliation"] = False
    durable_proof["restartReconciliationProofRetained"] = False
    durable_proof["tenantActorCorrelationTraceLineageRetained"] = False
    durable_proof["sourceSafeSupportReference"] = False
    durable_proof["recordsDownstreamOutcome"] = True
    durable_proof["grantsDownstreamAuthority"] = True
    durable_proof["supportedFeaturePromoted"] = True
    durable_proof["coveredOutcomeWindows"][0]["covered"] = False
    durable_proof["evidenceRefs"] = []

    errors = validate_downstream_outcome_certification(payload)

    assert "Idea durable submission evidenceClass must be test_execution" in errors
    assert "ideaDurableSubmissionProof.noAutomaticRetryAfterUncertainOutcome must be true" in (
        errors
    )
    assert "ideaDurableSubmissionProof.claimBeforeCallDurability must be true" in errors
    assert (
        "ideaDurableSubmissionProof.responseBeforeLocalCommitRequiresReconciliation must be true"
        in errors
    )
    assert "ideaDurableSubmissionProof.restartReconciliationProofRetained must be true" in errors
    assert (
        "ideaDurableSubmissionProof.tenantActorCorrelationTraceLineageRetained must be true"
        in errors
    )
    assert "ideaDurableSubmissionProof.sourceSafeSupportReference must be true" in errors
    assert "ideaDurableSubmissionProof.recordsDownstreamOutcome must be false" in errors
    assert "ideaDurableSubmissionProof.grantsDownstreamAuthority must be false" in errors
    assert "ideaDurableSubmissionProof.supportedFeaturePromoted must be false" in errors
    assert "Idea durable proof must cover every #379 outcome window" in errors
    assert "ideaDurableSubmissionProof evidenceRefs must be non-empty" in errors


def test_downstream_outcome_certification_rejects_malformed_diagnostics() -> None:
    payload = _valid_payload()
    payload["readinessAndDiagnosticsCoverage"] = "not-an-object"

    assert validate_downstream_outcome_certification(payload) == [
        "readinessAndDiagnosticsCoverage must be an object"
    ]

    payload = _valid_payload()
    payload["readinessAndDiagnosticsCoverage"]["unexpected"] = "drift"

    assert validate_downstream_outcome_certification(payload) == [
        "readinessAndDiagnosticsCoverage must match the governed shape"
    ]

    payload = _valid_payload()
    diagnostics = payload["readinessAndDiagnosticsCoverage"]
    diagnostics["operatorDiagnosticStates"] = ["pending"]
    diagnostics["sourceSafeProjection"] = False
    diagnostics["boundedOperationEvents"] = False
    diagnostics["supportedFeaturePromoted"] = True
    diagnostics["evidenceRefs"] = []

    errors = validate_downstream_outcome_certification(payload)

    assert "operatorDiagnosticStates must cover pending/uncertain/terminal states" in errors
    assert "readinessAndDiagnosticsCoverage.sourceSafeProjection must be true" in errors
    assert "readinessAndDiagnosticsCoverage.boundedOperationEvents must be true" in errors
    assert "readiness diagnostics must not promote supported features" in errors
    assert "readinessAndDiagnosticsCoverage evidenceRefs must be non-empty" in errors


def test_downstream_outcome_certification_rejects_proof_check_drift() -> None:
    payload = _valid_payload()
    payload["proofChecks"] = "not-an-object"

    assert validate_downstream_outcome_certification(payload) == ["proofChecks must be an object"]

    payload = _valid_payload()
    payload["proofChecks"]["unknownCheck"] = True
    payload["proofChecks"].pop("localEvidencePresent")
    payload["proofChecks"]["ownerRuntimeProofsValid"] = False

    errors = validate_downstream_outcome_certification(payload)

    assert "unknown proofChecks fields: ['unknownCheck']" in errors
    assert "missing proofChecks fields: ['localEvidencePresent']" in errors
    assert "proofChecks.localEvidencePresent must be true" in errors
    assert "proofChecks.ownerRuntimeProofsValid must be true" in errors


def test_downstream_outcome_certification_rejects_no_claim_contract_drift() -> None:
    payload = _valid_payload()
    payload["nonProofClaims"] = "not-an-object"

    assert validate_downstream_outcome_certification(payload) == [
        "nonProofClaims must be an object"
    ]

    payload = _valid_payload()
    payload["nonProofClaims"].pop("archiveAuthorityGranted")
    payload["nonProofClaims"]["clientPublicationAuthorized"] = True

    errors = validate_downstream_outcome_certification(payload)

    assert "nonProofClaims must match the governed no-claim fields" in errors
    assert "nonProofClaims.archiveAuthorityGranted must be false" in errors
    assert "nonProofClaims.clientPublicationAuthorized must be false" in errors


def test_downstream_outcome_certification_contract_gate_validates_artifact_file(
    tmp_path: Path,
) -> None:
    missing_artifact = tmp_path / "missing.json"

    errors = validate_downstream_outcome_certification_contract(
        repository_root=Path.cwd(),
        artifact_path=missing_artifact,
    )

    assert any("could not be read as a JSON proof artifact" in error for error in errors)

    invalid_json_artifact = tmp_path / "invalid.json"
    invalid_json_artifact.write_text("{not-json", encoding="utf-8")

    errors = validate_downstream_outcome_certification_contract(
        repository_root=Path.cwd(),
        artifact_path=invalid_json_artifact,
    )

    assert any("could not be read as a JSON proof artifact" in error for error in errors)

    array_artifact = tmp_path / "array.json"
    array_artifact.write_text("[]", encoding="utf-8")

    errors = validate_downstream_outcome_certification_contract(
        repository_root=Path.cwd(),
        artifact_path=array_artifact,
    )

    assert f"{array_artifact} must contain a JSON object" in errors

    invalid_payload_artifact = tmp_path / "invalid-payload.json"
    invalid_payload = _valid_payload()
    invalid_payload["aggregateOutcomeProofValid"] = False
    invalid_payload_artifact.write_text(json.dumps(invalid_payload), encoding="utf-8")

    errors = validate_downstream_outcome_certification_contract(
        repository_root=Path.cwd(),
        artifact_path=invalid_payload_artifact,
    )

    assert "aggregateOutcomeProofValid must be true" in errors


def test_downstream_outcome_certification_contract_gate_reports_missing_local_evidence(
    tmp_path: Path,
) -> None:
    errors = validate_downstream_outcome_certification_contract(repository_root=tmp_path)

    assert "downstream outcome certification evidence refs must exist" in errors
    assert "downstream outcome certification Make target must exist" in errors


def test_downstream_outcome_certification_requires_owner_receipt_evidence() -> None:
    invalid_advise = deepcopy(valid_advise_intake_runtime_execution())
    invalid_advise.pop("receiptEvidence")

    payload = _valid_payload(advise_intake_runtime_execution_proof=invalid_advise)

    errors = validate_downstream_outcome_certification(payload)

    assert "lotus-advise:proposal-intake runtime proof must be valid" in errors
    assert "lotus-advise:proposal-intake receiptWindows must be non-empty text" in errors
    assert "proofChecks.ownerRuntimeProofsValid must be true" in errors


def _valid_payload(
    *,
    advise_intake_runtime_execution_proof: dict[str, Any] | None = None,
    report_materialization_runtime_execution_proof: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return build_downstream_outcome_certification_payload(
        generated_at_utc=GENERATED_AT,
        repository_root=Path.cwd(),
        advise_intake_runtime_execution_proof=(
            advise_intake_runtime_execution_proof or valid_advise_intake_runtime_execution()
        ),
        advise_intake_runtime_execution_proof_ref=(
            "output/downstream/advise-intake-runtime-execution-proof.json"
        ),
        manage_intake_runtime_execution_proof=valid_manage_intake_runtime_execution(),
        manage_intake_runtime_execution_proof_ref=(
            "output/downstream/manage-intake-runtime-execution-proof.json"
        ),
        report_materialization_runtime_execution_proof=(
            report_materialization_runtime_execution_proof
            or valid_report_materialization_runtime_execution()
        ),
        report_materialization_runtime_execution_proof_ref=(
            "output/report/materialization-runtime-execution-proof.json"
        ),
    )
