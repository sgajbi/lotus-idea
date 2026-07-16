from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.application.advise_policy_runtime_evidence import (
    AdvisePolicyRuntimeEvidenceScope,
    AdvisePolicyWorkflowScope,
    advise_policy_workflow_qualification_blockers,
    build_advise_policy_workflow_receipt,
)
from app.application.mandate_restriction_signal import (
    DEFAULT_MANDATE_RESTRICTION_POLICY,
    EvaluateMandateRestrictionFromAdviseCommand,
    MandateRestrictionSourceEvaluation,
    evaluate_mandate_restriction_readiness_from_advise,
)
from app.application.runtime_evidence import (
    format_utc,
    identity_hash,
    require_aware,
    sha256_json,
)
from app.domain import MandateRestrictionSignalPolicy, SignalEvaluationOutcome, SourceSystem
from app.domain.access_scope import ReviewAccessScope
from app.domain.proof_evidence import EvidenceClass
from app.ports.advise_sources import (
    AdviseOpportunitySourcePort,
    AdvisePolicyEvaluationRuntimeEvidence,
)

ADVISE_MANDATE_RESTRICTION_RUNTIME_EXECUTION_ENV = "LOTUS_IDEA_MANDATE_RESTRICTION_LIVE_PROOF"
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


@dataclass(frozen=True)
class EvaluateAdviseMandateRestriction(AdvisePolicyRuntimeEvidenceScope):
    pass


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
    workflow_receipt = build_advise_policy_workflow_receipt(
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
            list(ADVISE_MANDATE_RESTRICTION_RUNTIME_BLOCKERS_SATISFIED) if not blockers else []
        ),
        "remainingCertificationBlockers": list(ADVISE_MANDATE_RESTRICTION_REMAINING_BLOCKERS),
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
    evidence = result.source_evaluation.evidence
    command = result.command
    blockers = list(
        advise_policy_workflow_qualification_blockers(
            scope=AdvisePolicyWorkflowScope(
                tenant_id=command.tenant_id,
                portfolio_id=command.portfolio_id,
                evaluation_id=command.evaluation_id,
                as_of_date=command.as_of_date,
                evaluated_at_utc=command.evaluated_at_utc,
                correlation_id=command.correlation_id or "",
                trace_id=command.trace_id or "",
            ),
            evidence=evidence,
            source_error_code=result.source_evaluation.source_error_code,
        )
    )
    if result.source_evaluation.evaluation.outcome not in {
        SignalEvaluationOutcome.CANDIDATE_CREATED,
        SignalEvaluationOutcome.NOT_ELIGIBLE,
    }:
        blockers.append("mandate_restriction_evaluation_blocked")
    return tuple(dict.fromkeys(blockers))
