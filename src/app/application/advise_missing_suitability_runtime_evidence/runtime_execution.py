from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.application.advise_policy_runtime_evidence import (
    AdvisePolicyRuntimeEvidenceScope,
    AdvisePolicyWorkflowScope,
    advise_policy_workflow_qualification_blockers,
    build_advise_policy_request_receipt,
    build_advise_policy_workflow_receipt,
)
from app.application.missing_suitability_signal import (
    DEFAULT_MISSING_SUITABILITY_CONTEXT_POLICY,
    EvaluateMissingSuitabilityContextFromAdviseCommand,
    MissingSuitabilitySourceEvaluation,
    evaluate_missing_suitability_context_readiness_from_advise,
)
from app.application.runtime_evidence import (
    format_utc,
    identity_hash,
    require_aware,
    sha256_json,
)
from app.domain import MissingSuitabilityContextSignalPolicy, SignalEvaluationOutcome, SourceSystem
from app.domain.access_scope import ReviewAccessScope
from app.domain.proof_evidence import EvidenceClass
from app.ports.advise_sources import AdviseOpportunitySourcePort

ADVISE_MISSING_SUITABILITY_RUNTIME_EXECUTION_ENV = "LOTUS_IDEA_MISSING_SUITABILITY_LIVE_PROOF"
ADVISE_MISSING_SUITABILITY_RUNTIME_EXECUTION_SCHEMA_VERSION = (
    "lotus-idea.advise-missing-suitability.runtime-execution.v2"
)
ADVISE_MISSING_SUITABILITY_RUNTIME_BLOCKERS_SATISFIED = (
    "opportunity_archetype_advise_policy_live_source_proof_missing",
)
ADVISE_MISSING_SUITABILITY_REMAINING_BLOCKERS = (
    "opportunity_archetype_data_mesh_not_certified",
    "opportunity_archetype_workbench_product_proof_missing",
    "opportunity_archetype_client_publication_not_ready",
    "opportunity_archetype_supported_feature_promotion_missing",
    "deployment_certification_missing",
    "production_certification_missing",
)
ADVISE_MISSING_SUITABILITY_RUNTIME_EVIDENCE_REFS = (
    "src/app/application/advise_missing_suitability_runtime_evidence/runtime_execution.py",
    "src/app/application/advise_missing_suitability_runtime_evidence/contract.py",
    "src/app/application/missing_suitability_signal.py",
    "src/app/ports/advise_sources.py",
    "src/app/infrastructure/lotus_advise_sources.py",
    "scripts/advise_missing_suitability_runtime_evidence/generate_runtime_execution.py",
    "contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json",
    "make missing-suitability-live-proof-contract-gate",
)


@dataclass(frozen=True)
class EvaluateAdviseMissingSuitability(AdvisePolicyRuntimeEvidenceScope):
    pass


@dataclass(frozen=True)
class AdviseMissingSuitabilityResult:
    command: EvaluateAdviseMissingSuitability
    source_evaluation: MissingSuitabilitySourceEvaluation
    policy: MissingSuitabilityContextSignalPolicy


def evaluate_advise_missing_suitability(
    command: EvaluateAdviseMissingSuitability,
    *,
    advise_source: AdviseOpportunitySourcePort,
    policy: MissingSuitabilityContextSignalPolicy = DEFAULT_MISSING_SUITABILITY_CONTEXT_POLICY,
) -> AdviseMissingSuitabilityResult:
    source_evaluation = evaluate_missing_suitability_context_readiness_from_advise(
        EvaluateMissingSuitabilityContextFromAdviseCommand(
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
    return AdviseMissingSuitabilityResult(command, source_evaluation, policy)


def build_advise_missing_suitability_runtime_execution(
    *,
    generated_at_utc: datetime,
    result: AdviseMissingSuitabilityResult,
) -> dict[str, Any]:
    require_aware(generated_at_utc, "generated_at_utc")
    evidence = result.source_evaluation.evidence
    workflow_receipt = build_advise_policy_workflow_receipt(
        evidence.workflow_runtime if evidence is not None else None,
        evidence=evidence,
    )
    blockers = list(_qualification_blockers(result))
    request_receipt = build_advise_policy_request_receipt(
        result.command,
        policy_version=result.policy.policy_version,
    )
    return {
        "schemaVersion": ADVISE_MISSING_SUITABILITY_RUNTIME_EXECUTION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "proofFamily": "missing_suitability_context",
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
            "qualificationBlockers": blockers,
        },
        "aggregateBlockersSatisfied": (
            list(ADVISE_MISSING_SUITABILITY_RUNTIME_BLOCKERS_SATISFIED) if not blockers else []
        ),
        "remainingCertificationBlockers": list(ADVISE_MISSING_SUITABILITY_REMAINING_BLOCKERS),
        "evidenceRefs": list(ADVISE_MISSING_SUITABILITY_RUNTIME_EVIDENCE_REFS),
        "nonProofClaims": {
            "policyWorkflowOwned": "lotus-advise",
            "opportunityDetectionOwned": "lotus-idea",
            "suitabilityApproved": False,
            "policyApproved": False,
            "proposalApproved": False,
            "signOffApproved": False,
            "clientPublicationApproved": False,
            "dataMeshRuntimeCertified": False,
            "gatewayWorkbenchRuntimeObserved": False,
            "deploymentCertified": False,
            "productionCertified": False,
            "supportedFeaturePromoted": False,
            "ideaPersistenceRequired": False,
        },
    }


def _evaluation_receipt(
    result: AdviseMissingSuitabilityResult,
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
        "minimumOpenRequirementCount": result.policy.minimum_open_requirement_count,
        "candidateScore": str(result.policy.candidate_score),
        "suitabilityContextMissing": candidate is not None,
        "candidateIdHash": identity_hash(candidate.candidate_id) if candidate else None,
        "signalIdHash": identity_hash(signal.signal_id) if signal else None,
        "evidencePacketIdHash": (
            identity_hash(candidate.evidence_packet.evidence_packet_id) if candidate else None
        ),
        "sourceRefsDigest": sha256_json([workflow_receipt] if workflow_receipt else []),
    }
    return {**material, "evaluationDigest": sha256_json(material)}


def _qualification_blockers(result: AdviseMissingSuitabilityResult) -> tuple[str, ...]:
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
            evidence=result.source_evaluation.evidence,
            source_error_code=result.source_evaluation.source_error_code,
        )
    )
    if result.source_evaluation.evaluation.outcome not in {
        SignalEvaluationOutcome.CANDIDATE_CREATED,
        SignalEvaluationOutcome.NOT_ELIGIBLE,
    }:
        blockers.append("missing_suitability_evaluation_blocked")
    return tuple(dict.fromkeys(blockers))
