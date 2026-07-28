from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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


def _valid_payload(
    *,
    report_materialization_runtime_execution_proof: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return build_downstream_outcome_certification_payload(
        generated_at_utc=GENERATED_AT,
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
            report_materialization_runtime_execution_proof
            or valid_report_materialization_runtime_execution()
        ),
        report_materialization_runtime_execution_proof_ref=(
            "output/report/materialization-runtime-execution-proof.json"
        ),
    )
