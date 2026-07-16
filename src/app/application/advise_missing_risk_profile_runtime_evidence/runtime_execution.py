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
from app.application.missing_risk_profile_signal import (
    DEFAULT_MISSING_RISK_PROFILE_POLICY,
    EvaluateMissingRiskProfileFromAdviseCommand,
    MissingRiskProfileSourceEvaluation,
    evaluate_missing_risk_profile_readiness_from_advise,
)
from app.application.runtime_evidence import format_utc, identity_hash, require_aware, sha256_json
from app.domain import (
    MissingRiskProfileSignalPolicy,
    SignalEvaluationOutcome,
    SourceSystem,
    risk_profile_posture_from_advise_diagnostic,
)
from app.domain.access_scope import ReviewAccessScope
from app.domain.proof_evidence import EvidenceClass
from app.ports.advise_sources import AdviseOpportunitySourcePort

ADVISE_MISSING_RISK_PROFILE_RUNTIME_EXECUTION_ENV = "LOTUS_IDEA_MISSING_RISK_PROFILE_LIVE_PROOF"
ADVISE_MISSING_RISK_PROFILE_RUNTIME_EXECUTION_SCHEMA_VERSION = (
    "lotus-idea.advise-missing-risk-profile.runtime-execution.v2"
)
ADVISE_MISSING_RISK_PROFILE_RUNTIME_BLOCKERS_SATISFIED = (
    "opportunity_archetype_advise_risk_profile_live_source_proof_missing",
)
ADVISE_MISSING_RISK_PROFILE_REMAINING_BLOCKERS = (
    "opportunity_archetype_typed_advise_risk_profile_source_product_missing",
    "opportunity_archetype_data_mesh_not_certified",
    "opportunity_archetype_workbench_product_proof_missing",
    "opportunity_archetype_client_publication_not_ready",
    "opportunity_archetype_supported_feature_promotion_missing",
    "deployment_certification_missing",
    "production_certification_missing",
)
ADVISE_MISSING_RISK_PROFILE_RUNTIME_EVIDENCE_REFS = (
    "src/app/application/advise_missing_risk_profile_runtime_evidence/runtime_execution.py",
    "src/app/application/advise_missing_risk_profile_runtime_evidence/contract.py",
    "src/app/application/missing_risk_profile_signal.py",
    "src/app/ports/advise_sources.py",
    "src/app/infrastructure/lotus_advise_sources.py",
    "scripts/advise_missing_risk_profile_runtime_evidence/generate_runtime_execution.py",
    "contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json",
    "make missing-risk-profile-live-proof-contract-gate",
)


@dataclass(frozen=True)
class EvaluateAdviseMissingRiskProfile(AdvisePolicyRuntimeEvidenceScope):
    pass


@dataclass(frozen=True)
class AdviseMissingRiskProfileResult:
    command: EvaluateAdviseMissingRiskProfile
    source_evaluation: MissingRiskProfileSourceEvaluation
    policy: MissingRiskProfileSignalPolicy


def evaluate_advise_missing_risk_profile(
    command: EvaluateAdviseMissingRiskProfile,
    *,
    advise_source: AdviseOpportunitySourcePort,
    policy: MissingRiskProfileSignalPolicy = DEFAULT_MISSING_RISK_PROFILE_POLICY,
) -> AdviseMissingRiskProfileResult:
    source_evaluation = evaluate_missing_risk_profile_readiness_from_advise(
        EvaluateMissingRiskProfileFromAdviseCommand(
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
    return AdviseMissingRiskProfileResult(command, source_evaluation, policy)


def build_advise_missing_risk_profile_runtime_execution(
    *,
    generated_at_utc: datetime,
    result: AdviseMissingRiskProfileResult,
) -> dict[str, Any]:
    require_aware(generated_at_utc, "generated_at_utc")
    evidence = result.source_evaluation.evidence
    workflow_receipt = build_advise_policy_workflow_receipt(
        evidence.workflow_runtime if evidence is not None else None,
        evidence=evidence,
    )
    blockers = list(_qualification_blockers(result))
    return {
        "schemaVersion": ADVISE_MISSING_RISK_PROFILE_RUNTIME_EXECUTION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "proofFamily": "missing_risk_profile",
        "proofType": "lotus_advise_policy_workflow_evaluation",
        "sourceAuthority": SourceSystem.LOTUS_ADVISE.value,
        "generatedAtUtc": format_utc(generated_at_utc),
        "execution": {
            "status": "completed" if evidence is not None else "blocked",
            "evaluatedAtUtc": format_utc(result.command.evaluated_at_utc),
            "requestReceipt": build_advise_policy_request_receipt(
                result.command,
                policy_version=result.policy.policy_version,
            ),
            "workflowReceipt": workflow_receipt,
            "evaluationReceipt": _evaluation_receipt(result, workflow_receipt=workflow_receipt),
            "qualificationBlockers": blockers,
        },
        "aggregateBlockersSatisfied": (
            list(ADVISE_MISSING_RISK_PROFILE_RUNTIME_BLOCKERS_SATISFIED) if not blockers else []
        ),
        "remainingCertificationBlockers": list(ADVISE_MISSING_RISK_PROFILE_REMAINING_BLOCKERS),
        "evidenceRefs": list(ADVISE_MISSING_RISK_PROFILE_RUNTIME_EVIDENCE_REFS),
        "nonProofClaims": {
            "policyWorkflowOwned": "lotus-advise",
            "opportunityDetectionOwned": "lotus-idea",
            "riskProfileApproved": False,
            "suitabilityApproved": False,
            "policyApproved": False,
            "proposalApproved": False,
            "signOffApproved": False,
            "clientPublicationApproved": False,
            "typedRiskProfileSourceProductCertified": False,
            "dataMeshRuntimeCertified": False,
            "gatewayWorkbenchRuntimeObserved": False,
            "deploymentCertified": False,
            "productionCertified": False,
            "supportedFeaturePromoted": False,
            "ideaPersistenceRequired": False,
        },
    }


def _evaluation_receipt(
    result: AdviseMissingRiskProfileResult,
    *,
    workflow_receipt: dict[str, Any] | None,
) -> dict[str, Any]:
    evaluation = result.source_evaluation.evaluation
    candidate = evaluation.candidate
    signal = evaluation.signal
    evidence = result.source_evaluation.evidence
    posture = risk_profile_posture_from_advise_diagnostic(
        evidence.advise_diagnostic if evidence is not None else None
    )
    material = {
        "family": evaluation.family.value,
        "outcome": evaluation.outcome.value,
        "reasonCodes": [code.value for code in evaluation.reason_codes],
        "unsupportedReasons": [reason.value for reason in evaluation.unsupported_reasons],
        "policyVersion": result.policy.policy_version,
        "candidateScore": str(result.policy.candidate_score),
        "riskProfilePosture": posture.value if posture is not None else None,
        "riskProfileReviewRequired": posture is not None and posture.value != "CURRENT",
        "candidateIdHash": identity_hash(candidate.candidate_id) if candidate else None,
        "signalIdHash": identity_hash(signal.signal_id) if signal else None,
        "evidencePacketIdHash": (
            identity_hash(candidate.evidence_packet.evidence_packet_id) if candidate else None
        ),
        "sourceRefsDigest": sha256_json([workflow_receipt] if workflow_receipt else []),
    }
    return {**material, "evaluationDigest": sha256_json(material)}


def _qualification_blockers(result: AdviseMissingRiskProfileResult) -> tuple[str, ...]:
    command = result.command
    evidence = result.source_evaluation.evidence
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
    if (
        risk_profile_posture_from_advise_diagnostic(
            evidence.advise_diagnostic if evidence is not None else None
        )
        is None
    ):
        blockers.append("advise_risk_profile_diagnostic_missing")
    if result.source_evaluation.evaluation.outcome not in {
        SignalEvaluationOutcome.CANDIDATE_CREATED,
        SignalEvaluationOutcome.NOT_ELIGIBLE,
    }:
        blockers.append("missing_risk_profile_evaluation_blocked")
    return tuple(dict.fromkeys(blockers))
