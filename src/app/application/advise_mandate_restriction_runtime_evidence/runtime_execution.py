from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Any
from urllib.parse import quote

from app.application.mandate_restriction_signal import (
    DEFAULT_MANDATE_RESTRICTION_POLICY,
    EvaluateMandateRestrictionFromAdviseCommand,
    MandateRestrictionSourceEvaluation,
    evaluate_mandate_restriction_readiness_from_advise,
)
from app.application.runtime_evidence import (
    RuntimeEvidenceScope,
    format_utc,
    identity_hash,
    require_aware,
    sha256_json,
)
from app.domain import MandateRestrictionSignalPolicy, SignalEvaluationOutcome, SourceSystem
from app.domain.access_scope import ReviewAccessScope
from app.domain.proof_evidence import EvidenceClass
from app.ports.advise_sources import (
    ADVISE_POLICY_EVALUATION_PRODUCT_ID,
    ADVISE_POLICY_EVALUATION_WORKFLOW_ROUTE_TEMPLATE,
    AdviseOpportunitySourcePort,
    AdvisePolicyEvaluationEvidence,
    AdvisePolicyEvaluationRuntimeEvidence,
)

ADVISE_MANDATE_RESTRICTION_RUNTIME_EXECUTION_ENV = (
    "LOTUS_IDEA_MANDATE_RESTRICTION_LIVE_PROOF"
)
ADVISE_MANDATE_RESTRICTION_RUNTIME_EXECUTION_SCHEMA_VERSION = (
    "lotus-idea.advise-mandate-restriction.runtime-execution.v2"
)
ADVISE_MANDATE_RESTRICTION_RUNTIME_BLOCKERS_SATISFIED = (
    "opportunity_archetype_live_restriction_source_proof_missing",
)
ADVISE_MANDATE_RESTRICTION_REMAINING_BLOCKERS = (
    "opportunity_archetype_typed_restriction_source_product_missing",
    "opportunity_archetype_data_mesh_not_certified",
    "opportunity_archetype_workbench_product_proof_missing",
    "opportunity_archetype_client_publication_not_ready",
    "opportunity_archetype_supported_feature_promotion_missing",
    "deployment_certification_missing",
    "production_certification_missing",
)
ADVISE_MANDATE_RESTRICTION_RUNTIME_EVIDENCE_REFS = (
    "src/app/application/advise_mandate_restriction_runtime_evidence/runtime_execution.py",
    "src/app/application/advise_mandate_restriction_runtime_evidence/contract.py",
    "src/app/application/mandate_restriction_signal.py",
    "src/app/ports/advise_sources.py",
    "src/app/infrastructure/lotus_advise_sources.py",
    "scripts/advise_mandate_restriction_runtime_evidence/generate_runtime_execution.py",
    "contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json",
    "make mandate-restriction-live-proof-contract-gate",
)
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class EvaluateAdviseMandateRestriction(RuntimeEvidenceScope):
    book_id: str = ""
    client_id: str = ""
    evaluation_id: str = ""

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.book_id.strip() or not self.client_id.strip() or not self.evaluation_id.strip():
            raise ValueError("book_id, client_id, and evaluation_id are required")
        if self.correlation_id is None or self.trace_id is None:
            raise ValueError("correlation_id and trace_id are required")
        if not self.trace_id.strip():
            raise ValueError("trace_id must not be blank")


@dataclass(frozen=True)
class AdviseMandateRestrictionResult:
    command: EvaluateAdviseMandateRestriction
    source_evaluation: MandateRestrictionSourceEvaluation
    policy: MandateRestrictionSignalPolicy


def evaluate_advise_mandate_restriction(
    command: EvaluateAdviseMandateRestriction,
    *,
    advise_source: AdviseOpportunitySourcePort,
    policy: MandateRestrictionSignalPolicy = DEFAULT_MANDATE_RESTRICTION_POLICY,
) -> AdviseMandateRestrictionResult:
    source_evaluation = evaluate_mandate_restriction_readiness_from_advise(
        EvaluateMandateRestrictionFromAdviseCommand(
            evaluation_id=command.evaluation_id,
            as_of_date=command.as_of_date,
            evaluated_at_utc=command.evaluated_at_utc,
            access_scope=ReviewAccessScope(
                tenant_id=command.tenant_id,
                book_id=command.book_id,
                portfolio_id=command.portfolio_id,
                client_id=command.client_id,
            ),
            correlation_id=command.correlation_id,
            trace_id=command.trace_id,
        ),
        advise_source=advise_source,
        policy=policy,
    )
    return AdviseMandateRestrictionResult(command, source_evaluation, policy)


def build_advise_mandate_restriction_runtime_execution(
    *, generated_at_utc: datetime, result: AdviseMandateRestrictionResult
) -> dict[str, Any]:
    require_aware(generated_at_utc, "generated_at_utc")
    evidence = result.source_evaluation.evidence
    runtime = evidence.workflow_runtime if evidence is not None else None
    blockers = _qualification_blockers(result, runtime)
    request_receipt = _request_receipt(result)
    workflow_receipt = _workflow_receipt(
        runtime,
        evidence=evidence,
    )
    return {
        "schemaVersion": ADVISE_MANDATE_RESTRICTION_RUNTIME_EXECUTION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "proofFamily": "mandate_restriction_review",
        "proofType": "lotus_advise_policy_workflow_evaluation",
        "sourceAuthority": SourceSystem.LOTUS_ADVISE.value,
        "generatedAtUtc": format_utc(generated_at_utc),
        "execution": {
            "status": "completed" if evidence is not None else "blocked",
            "evaluatedAtUtc": format_utc(result.command.evaluated_at_utc),
            "requestReceipt": request_receipt,
            "workflowReceipt": workflow_receipt,
            "evaluationReceipt": _evaluation_receipt(
                result,
                workflow_receipt=workflow_receipt,
            ),
            "qualificationBlockers": list(blockers),
        },
        "aggregateBlockersSatisfied": (
            list(ADVISE_MANDATE_RESTRICTION_RUNTIME_BLOCKERS_SATISFIED)
            if not blockers
            else []
        ),
        "remainingCertificationBlockers": list(
            ADVISE_MANDATE_RESTRICTION_REMAINING_BLOCKERS
        ),
        "evidenceRefs": list(ADVISE_MANDATE_RESTRICTION_RUNTIME_EVIDENCE_REFS),
        "nonProofClaims": {
            "policyWorkflowOwned": "lotus-advise",
            "opportunityDetectionOwned": "lotus-idea",
            "restrictionCleared": False,
            "suitabilityApproved": False,
            "policyApproved": False,
            "proposalApproved": False,
            "rebalanceAuthorized": False,
            "orderAuthorized": False,
            "clientPublicationApproved": False,
            "dataMeshRuntimeCertified": False,
            "gatewayWorkbenchRuntimeObserved": False,
            "deploymentCertified": False,
            "productionCertified": False,
            "supportedFeaturePromoted": False,
            "ideaPersistenceRequired": False,
        },
    }


def _request_receipt(result: AdviseMandateRestrictionResult) -> dict[str, Any]:
    command = result.command
    material = {
        "tenantIdHash": identity_hash(command.tenant_id),
        "bookIdHash": identity_hash(command.book_id),
        "portfolioIdHash": identity_hash(command.portfolio_id),
        "clientIdHash": identity_hash(command.client_id),
        "evaluationIdHash": identity_hash(command.evaluation_id),
        "asOfDate": command.as_of_date.isoformat(),
        "evaluatedAtUtc": format_utc(command.evaluated_at_utc),
        "consumerSystem": "lotus-idea",
        "correlationIdHash": (
            identity_hash(command.correlation_id) if command.correlation_id else None
        ),
        "traceIdHash": identity_hash(command.trace_id) if command.trace_id else None,
        "policyVersion": result.policy.policy_version,
    }
    return {**material, "requestDigest": sha256_json(material)}


def _workflow_receipt(
    runtime: AdvisePolicyEvaluationRuntimeEvidence | None,
    *,
    evidence: AdvisePolicyEvaluationEvidence | None,
) -> dict[str, Any] | None:
    if runtime is None:
        return None
    material = {
        "productId": runtime.product_id,
        "sourceSystem": SourceSystem.LOTUS_ADVISE.value,
        "productVersion": runtime.product_version,
        "routeTemplate": ADVISE_POLICY_EVALUATION_WORKFLOW_ROUTE_TEMPLATE,
        "evaluationIdHash": identity_hash(runtime.evaluation_id) if runtime.evaluation_id else None,
        "tenantScopeHash": runtime.tenant_scope_hash,
        "portfolioIdHash": identity_hash(runtime.portfolio_id) if runtime.portfolio_id else None,
        "sourceCorrelationIdHash": (
            identity_hash(runtime.correlation_id) if runtime.correlation_id else None
        ),
        "sourceTraceIdHash": identity_hash(runtime.trace_id) if runtime.trace_id else None,
        "asOfDate": runtime.as_of_date.isoformat() if runtime.as_of_date else None,
        "generatedAtUtc": format_utc(runtime.generated_at_utc) if runtime.generated_at_utc else None,
        "contentHash": runtime.content_hash,
        "sourceEvidenceHash": runtime.source_evidence_hash,
        "policyContentHash": runtime.policy_content_hash,
        "policyPackId": runtime.policy_pack_id,
        "policyVersion": runtime.policy_version,
        "evaluationStatus": runtime.evaluation_status,
        "openRequirementCount": runtime.open_requirement_count,
        "blockedRequirementCount": runtime.blocked_requirement_count,
        "signOffStatus": runtime.sign_off_status,
        "signOffBlockerCount": runtime.sign_off_blocker_count,
        "clientReadyPublication": runtime.client_ready_publication,
        "dataQualityStatus": runtime.data_quality_status,
        "freshness": runtime.freshness,
        "adviseDiagnostic": evidence.advise_diagnostic if evidence is not None else None,
    }
    return {**material, "receiptDigest": sha256_json(material)}


def _evaluation_receipt(
    result: AdviseMandateRestrictionResult,
    *,
    workflow_receipt: dict[str, Any] | None,
) -> dict[str, Any]:
    evaluation = result.source_evaluation.evaluation
    candidate = evaluation.candidate
    signal = evaluation.signal
    material = {
        "family": evaluation.family.value,
        "outcome": evaluation.outcome.value,
        "reasonCodes": [code.value for code in evaluation.reason_codes],
        "unsupportedReasons": [reason.value for reason in evaluation.unsupported_reasons],
        "policyVersion": result.policy.policy_version,
        "candidateScore": str(result.policy.candidate_score),
        "restrictionReviewRequired": candidate is not None,
        "candidateIdHash": identity_hash(candidate.candidate_id) if candidate else None,
        "signalIdHash": identity_hash(signal.signal_id) if signal else None,
        "evidencePacketIdHash": (
            identity_hash(candidate.evidence_packet.evidence_packet_id) if candidate else None
        ),
        "sourceRefsDigest": sha256_json([workflow_receipt] if workflow_receipt else []),
    }
    return {**material, "evaluationDigest": sha256_json(material)}


def _qualification_blockers(
    result: AdviseMandateRestrictionResult,
    runtime: AdvisePolicyEvaluationRuntimeEvidence | None,
) -> tuple[str, ...]:
    blockers: list[str] = []
    evidence = result.source_evaluation.evidence
    if evidence is None:
        blockers.append(result.source_evaluation.source_error_code or "advise_source_evidence_missing")
        return tuple(blockers)
    if runtime is None:
        return ("advise_workflow_runtime_receipt_missing",)
    command = result.command
    required = {
        "advise_evaluation_identity_missing": runtime.evaluation_id,
        "advise_tenant_scope_missing": runtime.tenant_scope_hash,
        "advise_portfolio_scope_missing": runtime.portfolio_id,
        "advise_source_correlation_missing": runtime.correlation_id,
        "advise_source_trace_missing": runtime.trace_id,
        "advise_as_of_date_missing": runtime.as_of_date,
        "advise_generated_at_missing": runtime.generated_at_utc,
        "advise_evaluation_hash_missing": runtime.content_hash,
        "advise_source_evidence_hash_missing": runtime.source_evidence_hash,
        "advise_policy_content_hash_missing": runtime.policy_content_hash,
        "advise_policy_pack_identity_missing": runtime.policy_pack_id,
        "advise_policy_version_missing": runtime.policy_version,
        "advise_evaluation_status_missing": runtime.evaluation_status,
        "advise_sign_off_status_missing": runtime.sign_off_status,
        "advise_client_publication_posture_missing": runtime.client_ready_publication,
    }
    blockers.extend(code for code, value in required.items() if value is None)
    if runtime.evaluation_id and runtime.evaluation_id != command.evaluation_id:
        blockers.append("advise_evaluation_scope_mismatch")
    if runtime.tenant_scope_hash and runtime.tenant_scope_hash != identity_hash(command.tenant_id):
        blockers.append("advise_tenant_scope_mismatch")
    if runtime.portfolio_id and runtime.portfolio_id != command.portfolio_id:
        blockers.append("advise_portfolio_scope_mismatch")
    if runtime.correlation_id and runtime.correlation_id != command.correlation_id:
        blockers.append("advise_source_correlation_mismatch")
    if runtime.trace_id and runtime.trace_id != command.trace_id:
        blockers.append("advise_source_trace_mismatch")
    if runtime.as_of_date and runtime.as_of_date != command.as_of_date:
        blockers.append("advise_as_of_date_mismatch")
    if runtime.generated_at_utc and runtime.generated_at_utc > command.evaluated_at_utc:
        blockers.append("advise_evidence_from_future")
    if runtime.product_id != ADVISE_POLICY_EVALUATION_PRODUCT_ID:
        blockers.append("advise_source_product_mismatch")
    if runtime.product_version != "v1":
        blockers.append("advise_source_product_version_mismatch")
    expected_route = ADVISE_POLICY_EVALUATION_WORKFLOW_ROUTE_TEMPLATE.format(
        evaluation_id=quote(command.evaluation_id, safe="")
    )
    if runtime.route != expected_route:
        blockers.append("advise_source_route_mismatch")
    if evidence.policy_ref is None:
        blockers.append("advise_policy_source_ref_missing")
    elif (
        evidence.policy_ref.product_id != runtime.product_id
        or evidence.policy_ref.route != runtime.route
        or evidence.policy_ref.as_of_date != runtime.as_of_date
        or evidence.policy_ref.generated_at_utc != runtime.generated_at_utc
        or evidence.policy_ref.content_hash != runtime.content_hash
        or evidence.policy_ref.freshness.value != runtime.freshness
        or evidence.policy_ref.data_quality_status != runtime.data_quality_status
    ):
        blockers.append("advise_policy_source_ref_mismatch")
    if runtime.freshness != "current":
        blockers.append("advise_source_evidence_not_current")
    if runtime.data_quality_status.lower() not in {"ready", "complete", "quality_passed"}:
        blockers.append("advise_source_quality_not_ready")
    if any(
        not _is_sha256(value)
        for value in (
            runtime.content_hash,
            runtime.source_evidence_hash,
            runtime.policy_content_hash,
        )
    ):
        blockers.append("advise_workflow_hash_invalid")
    counts: tuple[object, ...] = (
        runtime.open_requirement_count,
        runtime.blocked_requirement_count,
        runtime.sign_off_blocker_count,
    )
    if any(
        not isinstance(value, int) or isinstance(value, bool) or value < 0
        for value in counts
    ):
        blockers.append("advise_workflow_counts_invalid")
    elif (
        evidence.open_requirement_count != runtime.open_requirement_count
        or evidence.blocked_requirement_count != runtime.blocked_requirement_count
        or evidence.sign_off_blocker_count != runtime.sign_off_blocker_count
        or evidence.evaluation_status != runtime.evaluation_status
        or evidence.sign_off_status != runtime.sign_off_status
        or evidence.client_ready_publication != runtime.client_ready_publication
    ):
        blockers.append("advise_workflow_posture_mismatch")
    if result.source_evaluation.evaluation.outcome not in {
        SignalEvaluationOutcome.CANDIDATE_CREATED,
        SignalEvaluationOutcome.NOT_ELIGIBLE,
    }:
        blockers.append("mandate_restriction_evaluation_blocked")
    return tuple(dict.fromkeys(blockers))


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None
