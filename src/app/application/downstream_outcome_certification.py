from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from app.application.downstream_realization.advise_intake_runtime_execution import (
    ADVISE_INTAKE_RUNTIME_BLOCKERS_SATISFIED,
    advise_intake_runtime_execution_is_valid,
)
from app.application.downstream_realization.manage_intake_runtime_execution import (
    MANAGE_INTAKE_RUNTIME_BLOCKERS_SATISFIED,
    manage_intake_runtime_execution_is_valid,
)
from app.application.proof_provenance import AGGREGATE_PROOF_PROVENANCE_KEY
from app.application.proof_payload_helpers import (
    non_empty_text_array,
    source_safe_mapping_digest,
)
from app.application.report.materialization_runtime_execution import (
    REPORT_MATERIALIZATION_RUNTIME_BLOCKERS_SATISFIED,
    report_materialization_runtime_execution_is_valid,
)
from app.application.source_safe_cross_repo_proof import (
    is_timezone_aware_datetime_text,
    required_file_evidence_present,
    required_make_target_evidence_present,
)
from app.domain.proof_evidence import EvidenceClass


DOWNSTREAM_OUTCOME_CERTIFICATION_ENV = "LOTUS_IDEA_DOWNSTREAM_OUTCOME_CERTIFICATION_PROOF"
DOWNSTREAM_OUTCOME_CERTIFICATION_SCHEMA_VERSION = "lotus-idea.downstream-outcome-certification.v1"

REQUIRED_DOWNSTREAM_OUTCOME_EVIDENCE_REFS = (
    "src/app/application/downstream_outcome_certification.py",
    "src/app/application/downstream_realization/submission_use_cases.py",
    "src/app/application/downstream_submission_reconciliation.py",
    "src/app/domain/downstream_submission.py",
    "scripts/generate_downstream_outcome_certification.py",
    "scripts/downstream_outcome_certification_gate.py",
    "tests/unit/test_downstream_outcome_certification.py",
    "tests/unit/test_downstream_realization_application.py",
    "tests/integration/test_downstream_realization_api.py",
    "tests/integration/test_downstream_submission_reconciliation_api.py",
    "tests/integration/test_postgres_downstream_submission_runtime.py",
    (
        "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
        "RFC-0002-slice-12-advise-and-manage-conversion-realization.md"
    ),
    (
        "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
        "RFC-0002-slice-13-report-render-archive-and-evidence-pack-materialization.md"
    ),
    "make downstream-outcome-certification-proof-gate",
)

REQUIRED_OWNER_PROOF_IDS = (
    "lotus-advise:proposal-intake",
    "lotus-manage:action-intake",
    "lotus-report:evidence-pack-materialization",
)

REQUIRED_IDEA_OUTCOME_WINDOWS = (
    "accepted",
    "rejected",
    "duplicate_or_idempotent_replay",
    "idempotency_conflict",
    "timeout_before_response",
    "response_before_local_commit",
    "restart_reconciliation",
    "operator_reconciliation_replay",
)

REQUIRED_DIAGNOSTIC_STATES = (
    "pending",
    "uncertain",
    "terminal_success",
    "terminal_rejection",
)

REMAINING_DOWNSTREAM_OUTCOME_CERTIFICATION_BLOCKERS = (
    "external_downstream_certification_blocked",
    "production_identity_not_certified",
    "supported_feature_promotion_missing",
    "client_publication_authority_blocked",
)

DOWNSTREAM_OUTCOME_NON_PROOF_CLAIMS = (
    "suitabilityAuthorityGranted",
    "rebalanceExecutionAuthorityGranted",
    "reportRenderingAuthorityGranted",
    "archiveAuthorityGranted",
    "clientPublicationAuthorized",
    "productionIdentityCertified",
    "productionCertificationGranted",
    "supportedFeaturePromoted",
    "certificationClosed",
)

EXPECTED_TOP_LEVEL_KEYS = frozenset(
    {
        "schemaVersion",
        "repository",
        "generatedAtUtc",
        "rfc",
        "sliceIds",
        "trackingIssues",
        "proofType",
        "proofScope",
        "evidenceClass",
        "sourceRepository",
        "aggregateOutcomeProofValid",
        "issue379ClosureReady",
        "evidenceRefs",
        "ownerRuntimeProofs",
        "ideaDurableSubmissionProof",
        "readinessAndDiagnosticsCoverage",
        "proofChecks",
        "aggregateBlockersSatisfied",
        "remainingCertificationBlockers",
        "nonProofClaims",
        AGGREGATE_PROOF_PROVENANCE_KEY,
    }
)

_OWNER_PROOF_FIELDS = frozenset(
    {
        "proofId",
        "ownerRepository",
        "proofRef",
        "proofDigest",
        "schemaVersion",
        "proofType",
        "proofScope",
        "evidenceClass",
        "runtimeProofValid",
        "downstreamAuthority",
        "targetRoute",
        "receiptWindows",
        "aggregateBlockersSatisfied",
        "remainingCertificationBlockers",
        "nonProofClaimsRetained",
    }
)

_IDEA_DURABLE_PROOF_FIELDS = frozenset(
    {
        "evidenceClass",
        "sourceAuthority",
        "coveredOutcomeWindows",
        "noAutomaticRetryAfterUncertainOutcome",
        "claimBeforeCallDurability",
        "responseBeforeLocalCommitRequiresReconciliation",
        "restartReconciliationProofRetained",
        "tenantActorCorrelationTraceLineageRetained",
        "sourceSafeSupportReference",
        "recordsDownstreamOutcome",
        "grantsDownstreamAuthority",
        "supportedFeaturePromoted",
        "evidenceRefs",
    }
)

_DIAGNOSTICS_FIELDS = frozenset(
    {
        "operatorDiagnosticStates",
        "operatorReadCapability",
        "operatorResolveCapability",
        "sourceSafeProjection",
        "boundedOperationEvents",
        "readinessEndpoint",
        "supportedFeaturePromoted",
        "evidenceRefs",
    }
)

_PROOF_CHECK_FIELDS = frozenset(
    {
        "timezoneAwareGeneratedAtUtc",
        "localEvidencePresent",
        "makeTargetEvidencePresent",
        "ownerRuntimeProofsValid",
        "ownerRuntimeProofsAreRuntimeExecution",
        "ideaOutcomeWindowsCovered",
        "uncertainOutcomeRequiresOperatorReconciliation",
        "operatorDiagnosticsCovered",
        "tenantActorCorrelationTraceLineageCovered",
        "noDownstreamAuthorityClaimed",
        "supportedFeatureNotPromoted",
        "issue379RemainsOpen",
    }
)


def build_downstream_outcome_certification_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
    advise_intake_runtime_execution_proof: Mapping[str, Any],
    advise_intake_runtime_execution_proof_ref: str,
    manage_intake_runtime_execution_proof: Mapping[str, Any],
    manage_intake_runtime_execution_proof_ref: str,
    report_materialization_runtime_execution_proof: Mapping[str, Any],
    report_materialization_runtime_execution_proof_ref: str,
) -> dict[str, Any]:
    _require_timezone_aware_generated_at(generated_at_utc)
    owner_runtime_proofs = _downstream_owner_runtime_proofs(
        advise_intake_runtime_execution_proof=advise_intake_runtime_execution_proof,
        advise_intake_runtime_execution_proof_ref=advise_intake_runtime_execution_proof_ref,
        manage_intake_runtime_execution_proof=manage_intake_runtime_execution_proof,
        manage_intake_runtime_execution_proof_ref=manage_intake_runtime_execution_proof_ref,
        report_materialization_runtime_execution_proof=report_materialization_runtime_execution_proof,
        report_materialization_runtime_execution_proof_ref=report_materialization_runtime_execution_proof_ref,
    )
    idea_durable_submission_proof = _idea_durable_submission_proof()
    diagnostics_coverage = _readiness_and_diagnostics_coverage()
    proof_checks = _downstream_outcome_proof_checks(
        repository_root=repository_root,
        owner_runtime_proofs=owner_runtime_proofs,
        idea_durable_submission_proof=idea_durable_submission_proof,
        diagnostics_coverage=diagnostics_coverage,
    )
    return _downstream_outcome_certification_payload(
        generated_at_utc=generated_at_utc,
        owner_runtime_proofs=owner_runtime_proofs,
        idea_durable_submission_proof=idea_durable_submission_proof,
        diagnostics_coverage=diagnostics_coverage,
        proof_checks=proof_checks,
    )


def _require_timezone_aware_generated_at(generated_at_utc: datetime) -> None:
    if generated_at_utc.tzinfo is None or generated_at_utc.utcoffset() is None:
        raise ValueError("generated_at_utc must be timezone-aware")


def _downstream_owner_runtime_proofs(
    *,
    advise_intake_runtime_execution_proof: Mapping[str, Any],
    advise_intake_runtime_execution_proof_ref: str,
    manage_intake_runtime_execution_proof: Mapping[str, Any],
    manage_intake_runtime_execution_proof_ref: str,
    report_materialization_runtime_execution_proof: Mapping[str, Any],
    report_materialization_runtime_execution_proof_ref: str,
) -> list[dict[str, Any]]:
    return [
        _owner_runtime_proof(
            proof_id="lotus-advise:proposal-intake",
            owner_repository="lotus-advise",
            proof=advise_intake_runtime_execution_proof,
            proof_ref=advise_intake_runtime_execution_proof_ref,
            validator=advise_intake_runtime_execution_is_valid,
            expected_blockers_satisfied=ADVISE_INTAKE_RUNTIME_BLOCKERS_SATISFIED,
        ),
        _owner_runtime_proof(
            proof_id="lotus-manage:action-intake",
            owner_repository="lotus-manage",
            proof=manage_intake_runtime_execution_proof,
            proof_ref=manage_intake_runtime_execution_proof_ref,
            validator=manage_intake_runtime_execution_is_valid,
            expected_blockers_satisfied=MANAGE_INTAKE_RUNTIME_BLOCKERS_SATISFIED,
        ),
        _owner_runtime_proof(
            proof_id="lotus-report:evidence-pack-materialization",
            owner_repository="lotus-report",
            proof=report_materialization_runtime_execution_proof,
            proof_ref=report_materialization_runtime_execution_proof_ref,
            validator=report_materialization_runtime_execution_is_valid,
            expected_blockers_satisfied=REPORT_MATERIALIZATION_RUNTIME_BLOCKERS_SATISFIED,
        ),
    ]


def _downstream_outcome_proof_checks(
    *,
    repository_root: Path,
    owner_runtime_proofs: Sequence[Mapping[str, Any]],
    idea_durable_submission_proof: Mapping[str, Any],
    diagnostics_coverage: Mapping[str, Any],
) -> dict[str, bool]:
    return {
        "timezoneAwareGeneratedAtUtc": True,
        "localEvidencePresent": required_file_evidence_present(
            repository_root=repository_root,
            sibling_roots={},
            evidence_refs=REQUIRED_DOWNSTREAM_OUTCOME_EVIDENCE_REFS,
            non_file_ref_prefixes=("make ",),
        ),
        "makeTargetEvidencePresent": required_make_target_evidence_present(
            repository_root=repository_root,
            evidence_refs=REQUIRED_DOWNSTREAM_OUTCOME_EVIDENCE_REFS,
        ),
        "ownerRuntimeProofsValid": all(
            proof["runtimeProofValid"] is True for proof in owner_runtime_proofs
        ),
        "ownerRuntimeProofsAreRuntimeExecution": all(
            proof["evidenceClass"] == EvidenceClass.RUNTIME_EXECUTION.value
            for proof in owner_runtime_proofs
        ),
        "ideaOutcomeWindowsCovered": _covered_windows_are_complete(
            idea_durable_submission_proof["coveredOutcomeWindows"]
        ),
        "uncertainOutcomeRequiresOperatorReconciliation": (
            idea_durable_submission_proof["noAutomaticRetryAfterUncertainOutcome"] is True
            and idea_durable_submission_proof["responseBeforeLocalCommitRequiresReconciliation"]
            is True
        ),
        "operatorDiagnosticsCovered": (
            tuple(diagnostics_coverage["operatorDiagnosticStates"]) == REQUIRED_DIAGNOSTIC_STATES
            and diagnostics_coverage["sourceSafeProjection"] is True
        ),
        "tenantActorCorrelationTraceLineageCovered": (
            idea_durable_submission_proof["tenantActorCorrelationTraceLineageRetained"] is True
        ),
        "noDownstreamAuthorityClaimed": (
            idea_durable_submission_proof["recordsDownstreamOutcome"] is False
            and idea_durable_submission_proof["grantsDownstreamAuthority"] is False
        ),
        "supportedFeatureNotPromoted": (
            idea_durable_submission_proof["supportedFeaturePromoted"] is False
            and diagnostics_coverage["supportedFeaturePromoted"] is False
        ),
        "issue379RemainsOpen": True,
    }


def _downstream_outcome_certification_payload(
    *,
    generated_at_utc: datetime,
    owner_runtime_proofs: list[dict[str, Any]],
    idea_durable_submission_proof: dict[str, Any],
    diagnostics_coverage: dict[str, Any],
    proof_checks: Mapping[str, bool],
) -> dict[str, Any]:
    aggregate_valid = all(value is True for value in proof_checks.values())
    return {
        "schemaVersion": DOWNSTREAM_OUTCOME_CERTIFICATION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "rfc": "RFC-0002",
        "sliceIds": ["RFC-0002/slice-12", "RFC-0002/slice-13"],
        "trackingIssues": ["sgajbi/lotus-idea#379"],
        "proofType": "downstream_outcome_certification",
        "proofScope": (
            "advise_manage_report_owner_runtime_receipts_and_idea_durable_reconciliation"
        ),
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "sourceRepository": "lotus-idea",
        "aggregateOutcomeProofValid": aggregate_valid,
        "issue379ClosureReady": False,
        "evidenceRefs": list(REQUIRED_DOWNSTREAM_OUTCOME_EVIDENCE_REFS),
        "ownerRuntimeProofs": owner_runtime_proofs,
        "ideaDurableSubmissionProof": idea_durable_submission_proof,
        "readinessAndDiagnosticsCoverage": diagnostics_coverage,
        "proofChecks": proof_checks,
        "aggregateBlockersSatisfied": [],
        "remainingCertificationBlockers": list(REMAINING_DOWNSTREAM_OUTCOME_CERTIFICATION_BLOCKERS),
        "nonProofClaims": {claim: False for claim in DOWNSTREAM_OUTCOME_NON_PROOF_CLAIMS},
    }


def downstream_outcome_certification_is_valid(payload: Mapping[str, Any]) -> bool:
    return not validate_downstream_outcome_certification(payload)


def validate_downstream_outcome_certification(payload: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    _validate_top_level(payload, errors)
    _validate_exact_sequence(
        payload,
        "sliceIds",
        ("RFC-0002/slice-12", "RFC-0002/slice-13"),
        errors,
    )
    _validate_exact_sequence(payload, "trackingIssues", ("sgajbi/lotus-idea#379",), errors)
    _validate_exact_sequence(
        payload,
        "remainingCertificationBlockers",
        REMAINING_DOWNSTREAM_OUTCOME_CERTIFICATION_BLOCKERS,
        errors,
    )
    _validate_owner_runtime_proofs(payload.get("ownerRuntimeProofs"), errors)
    _validate_idea_durable_submission(payload.get("ideaDurableSubmissionProof"), errors)
    _validate_diagnostics(payload.get("readinessAndDiagnosticsCoverage"), errors)
    _validate_proof_checks(payload.get("proofChecks"), errors)
    _validate_no_claims(payload.get("nonProofClaims"), errors)
    return errors


def validate_downstream_outcome_certification_contract(
    *,
    repository_root: Path,
    artifact_path: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    if not required_file_evidence_present(
        repository_root=repository_root,
        sibling_roots={},
        evidence_refs=REQUIRED_DOWNSTREAM_OUTCOME_EVIDENCE_REFS,
        non_file_ref_prefixes=("make ",),
    ):
        errors.append("downstream outcome certification evidence refs must exist")
    if not required_make_target_evidence_present(
        repository_root=repository_root,
        evidence_refs=REQUIRED_DOWNSTREAM_OUTCOME_EVIDENCE_REFS,
    ):
        errors.append("downstream outcome certification Make target must exist")
    if artifact_path is not None:
        try:
            payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{artifact_path} could not be read as a JSON proof artifact: {exc}")
        else:
            if not isinstance(payload, dict):
                errors.append(f"{artifact_path} must contain a JSON object")
            else:
                errors.extend(validate_downstream_outcome_certification(payload))
    return errors


def _owner_runtime_proof(
    *,
    proof_id: str,
    owner_repository: str,
    proof: Mapping[str, Any],
    proof_ref: str,
    validator: Callable[[Mapping[str, Any]], bool],
    expected_blockers_satisfied: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "proofId": proof_id,
        "ownerRepository": owner_repository,
        "proofRef": proof_ref,
        "proofDigest": source_safe_mapping_digest(proof),
        "schemaVersion": proof.get("schemaVersion"),
        "proofType": proof.get("proofType"),
        "proofScope": proof.get("proofScope"),
        "evidenceClass": proof.get("evidenceClass"),
        "runtimeProofValid": validator(proof),
        "downstreamAuthority": proof.get("downstreamAuthority"),
        "targetRoute": proof.get("targetRoute"),
        "receiptWindows": sorted(_receipt_windows(proof)),
        "aggregateBlockersSatisfied": list(expected_blockers_satisfied),
        "remainingCertificationBlockers": list(proof.get("remainingCertificationBlockers") or []),
        "nonProofClaimsRetained": _all_values_are_false(proof.get("nonProofClaims")),
    }


def _idea_durable_submission_proof() -> dict[str, Any]:
    return {
        "evidenceClass": EvidenceClass.TEST_EXECUTION.value,
        "sourceAuthority": "lotus-idea",
        "coveredOutcomeWindows": [
            {
                "window": window,
                "covered": True,
                "evidenceRefs": _window_evidence_refs(window),
            }
            for window in REQUIRED_IDEA_OUTCOME_WINDOWS
        ],
        "noAutomaticRetryAfterUncertainOutcome": True,
        "claimBeforeCallDurability": True,
        "responseBeforeLocalCommitRequiresReconciliation": True,
        "restartReconciliationProofRetained": True,
        "tenantActorCorrelationTraceLineageRetained": True,
        "sourceSafeSupportReference": True,
        "recordsDownstreamOutcome": False,
        "grantsDownstreamAuthority": False,
        "supportedFeaturePromoted": False,
        "evidenceRefs": [
            "src/app/application/downstream_realization/submission_use_cases.py",
            "src/app/domain/downstream_submission.py",
            "tests/unit/test_downstream_realization_application.py",
            "tests/integration/test_downstream_realization_api.py",
            "tests/integration/test_postgres_downstream_submission_runtime.py",
        ],
    }


def _readiness_and_diagnostics_coverage() -> dict[str, Any]:
    return {
        "operatorDiagnosticStates": list(REQUIRED_DIAGNOSTIC_STATES),
        "operatorReadCapability": "idea.downstream-reconciliation.read",
        "operatorResolveCapability": "idea.downstream-reconciliation.resolve",
        "sourceSafeProjection": True,
        "boundedOperationEvents": True,
        "readinessEndpoint": "GET /api/v1/downstream-realization/readiness",
        "supportedFeaturePromoted": False,
        "evidenceRefs": [
            "src/app/application/downstream_submission_reconciliation.py",
            "tests/integration/test_downstream_submission_reconciliation_api.py",
            "docs/operations/downstream-realization-readiness.md",
        ],
    }


def _window_evidence_refs(window: str) -> list[str]:
    common = ["src/app/application/downstream_realization/submission_use_cases.py"]
    if window in {"restart_reconciliation", "response_before_local_commit"}:
        return [*common, "tests/integration/test_postgres_downstream_submission_runtime.py"]
    if window == "operator_reconciliation_replay":
        return [*common, "tests/integration/test_downstream_submission_reconciliation_api.py"]
    return [*common, "tests/integration/test_downstream_realization_api.py"]


def _validate_top_level(payload: Mapping[str, Any], errors: list[str]) -> None:
    unknown_keys = sorted(set(payload) - EXPECTED_TOP_LEVEL_KEYS)
    if unknown_keys:
        errors.append(f"unknown downstream outcome certification fields: {unknown_keys}")
    required_without_provenance = EXPECTED_TOP_LEVEL_KEYS - {AGGREGATE_PROOF_PROVENANCE_KEY}
    missing_keys = sorted(required_without_provenance - set(payload))
    if missing_keys:
        errors.append(f"missing downstream outcome certification fields: {missing_keys}")
    if payload.get("schemaVersion") != DOWNSTREAM_OUTCOME_CERTIFICATION_SCHEMA_VERSION:
        errors.append("schemaVersion must be the downstream outcome certification schema")
    if payload.get("repository") != "lotus-idea":
        errors.append("repository must be lotus-idea")
    if not is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        errors.append("generatedAtUtc must be timezone-aware")
    if payload.get("rfc") != "RFC-0002":
        errors.append("rfc must be RFC-0002")
    if payload.get("proofType") != "downstream_outcome_certification":
        errors.append("proofType must be downstream_outcome_certification")
    if payload.get("proofScope") != (
        "advise_manage_report_owner_runtime_receipts_and_idea_durable_reconciliation"
    ):
        errors.append("proofScope must be the governed downstream outcome boundary")
    if payload.get("evidenceClass") != EvidenceClass.RUNTIME_EXECUTION.value:
        errors.append("evidenceClass must be runtime_execution")
    if payload.get("sourceRepository") != "lotus-idea":
        errors.append("sourceRepository must be lotus-idea")
    if payload.get("aggregateOutcomeProofValid") is not True:
        errors.append("aggregateOutcomeProofValid must be true")
    if payload.get("issue379ClosureReady") is not False:
        errors.append("issue379ClosureReady must stay false for this partial proof")
    _validate_exact_sequence(
        payload,
        "evidenceRefs",
        REQUIRED_DOWNSTREAM_OUTCOME_EVIDENCE_REFS,
        errors,
    )
    aggregate_cleared = payload.get("aggregateBlockersSatisfied")
    if aggregate_cleared != []:
        errors.append("aggregateBlockersSatisfied must be empty for partial #379 proof")


def _validate_owner_runtime_proofs(value: object, errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append("ownerRuntimeProofs must be a JSON array")
        return
    observed_ids: list[str] = []
    for item in value:
        if not isinstance(item, Mapping):
            errors.append("ownerRuntimeProofs entries must be objects")
            return
        if set(item) != _OWNER_PROOF_FIELDS:
            errors.append("ownerRuntimeProofs entries must match the governed summary shape")
            return
        proof_id = item.get("proofId")
        if not isinstance(proof_id, str):
            errors.append("ownerRuntimeProofs proofId must be text")
            return
        observed_ids.append(proof_id)
        if item.get("evidenceClass") != EvidenceClass.RUNTIME_EXECUTION.value:
            errors.append(f"{proof_id} evidenceClass must be runtime_execution")
        if item.get("runtimeProofValid") is not True:
            errors.append(f"{proof_id} runtime proof must be valid")
        if item.get("nonProofClaimsRetained") is not True:
            errors.append(f"{proof_id} must retain non-proof claims")
        if not _is_sha256_digest(item.get("proofDigest")):
            errors.append(f"{proof_id} proofDigest must be a sha256 digest")
        if not non_empty_text_array(item.get("receiptWindows")):
            errors.append(f"{proof_id} receiptWindows must be non-empty text")
    if tuple(observed_ids) != REQUIRED_OWNER_PROOF_IDS:
        errors.append("ownerRuntimeProofs must match Advise, Manage, and Report proof order")


def _validate_idea_durable_submission(value: object, errors: list[str]) -> None:
    if not isinstance(value, Mapping):
        errors.append("ideaDurableSubmissionProof must be an object")
        return
    if set(value) != _IDEA_DURABLE_PROOF_FIELDS:
        errors.append("ideaDurableSubmissionProof must match the governed shape")
        return
    if value.get("evidenceClass") != EvidenceClass.TEST_EXECUTION.value:
        errors.append("Idea durable submission evidenceClass must be test_execution")
    for field_name in (
        "noAutomaticRetryAfterUncertainOutcome",
        "claimBeforeCallDurability",
        "responseBeforeLocalCommitRequiresReconciliation",
        "restartReconciliationProofRetained",
        "tenantActorCorrelationTraceLineageRetained",
        "sourceSafeSupportReference",
    ):
        if value.get(field_name) is not True:
            errors.append(f"ideaDurableSubmissionProof.{field_name} must be true")
    for field_name in (
        "recordsDownstreamOutcome",
        "grantsDownstreamAuthority",
        "supportedFeaturePromoted",
    ):
        if value.get(field_name) is not False:
            errors.append(f"ideaDurableSubmissionProof.{field_name} must be false")
    if not _covered_windows_are_complete(value.get("coveredOutcomeWindows")):
        errors.append("Idea durable proof must cover every #379 outcome window")
    if not non_empty_text_array(value.get("evidenceRefs")):
        errors.append("ideaDurableSubmissionProof evidenceRefs must be non-empty")


def _validate_diagnostics(value: object, errors: list[str]) -> None:
    if not isinstance(value, Mapping):
        errors.append("readinessAndDiagnosticsCoverage must be an object")
        return
    if set(value) != _DIAGNOSTICS_FIELDS:
        errors.append("readinessAndDiagnosticsCoverage must match the governed shape")
        return
    if tuple(value.get("operatorDiagnosticStates") or ()) != REQUIRED_DIAGNOSTIC_STATES:
        errors.append("operatorDiagnosticStates must cover pending/uncertain/terminal states")
    for field_name in ("sourceSafeProjection", "boundedOperationEvents"):
        if value.get(field_name) is not True:
            errors.append(f"readinessAndDiagnosticsCoverage.{field_name} must be true")
    if value.get("supportedFeaturePromoted") is not False:
        errors.append("readiness diagnostics must not promote supported features")
    if not non_empty_text_array(value.get("evidenceRefs")):
        errors.append("readinessAndDiagnosticsCoverage evidenceRefs must be non-empty")


def _validate_proof_checks(value: object, errors: list[str]) -> None:
    if not isinstance(value, Mapping):
        errors.append("proofChecks must be an object")
        return
    unknown_checks = sorted(set(value) - _PROOF_CHECK_FIELDS)
    if unknown_checks:
        errors.append(f"unknown proofChecks fields: {unknown_checks}")
    missing_checks = sorted(_PROOF_CHECK_FIELDS - set(value))
    if missing_checks:
        errors.append(f"missing proofChecks fields: {missing_checks}")
    for check in _PROOF_CHECK_FIELDS:
        if value.get(check) is not True:
            errors.append(f"proofChecks.{check} must be true")


def _validate_no_claims(value: object, errors: list[str]) -> None:
    if not isinstance(value, Mapping):
        errors.append("nonProofClaims must be an object")
        return
    if set(value) != set(DOWNSTREAM_OUTCOME_NON_PROOF_CLAIMS):
        errors.append("nonProofClaims must match the governed no-claim fields")
    for claim in DOWNSTREAM_OUTCOME_NON_PROOF_CLAIMS:
        if value.get(claim) is not False:
            errors.append(f"nonProofClaims.{claim} must be false")


def _covered_windows_are_complete(value: object) -> bool:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return False
    observed: list[str] = []
    for item in value:
        if not isinstance(item, Mapping):
            return False
        window = item.get("window")
        if not isinstance(window, str):
            return False
        observed.append(window)
        if item.get("covered") is not True:
            return False
        if not non_empty_text_array(item.get("evidenceRefs")):
            return False
    return tuple(observed) == REQUIRED_IDEA_OUTCOME_WINDOWS


def _validate_exact_sequence(
    payload: Mapping[str, Any],
    field_name: str,
    expected: Sequence[object],
    errors: list[str],
) -> None:
    value = payload.get(field_name)
    if not isinstance(value, list):
        errors.append(f"{field_name} must be a JSON array")
        return
    if tuple(value) != tuple(expected):
        errors.append(f"{field_name} must match the governed downstream outcome contract")


def _receipt_windows(proof: Mapping[str, Any]) -> tuple[str, ...]:
    receipt_evidence = proof.get("receiptEvidence")
    if not isinstance(receipt_evidence, Mapping):
        return ()
    return tuple(str(name) for name in receipt_evidence if isinstance(name, str) and name)


def _all_values_are_false(value: object) -> bool:
    return (
        isinstance(value, Mapping) and bool(value) and all(item is False for item in value.values())
    )


def _is_sha256_digest(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        return False
    digest = value.removeprefix("sha256:")
    return len(digest) == 64 and all(character in "0123456789abcdef" for character in digest)
