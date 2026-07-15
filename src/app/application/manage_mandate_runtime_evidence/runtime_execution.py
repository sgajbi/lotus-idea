from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import re
from typing import Any

from app.application.core_runtime_evidence import (
    format_utc,
    identity_hash,
    require_aware,
    sha256_json,
    source_ref_receipt,
)
from app.application.mandate_health_signal import (
    DEFAULT_MANDATE_HEALTH_POLICY,
    EvaluateMandateHealthFromManageCommand,
    MandateHealthSourceEvaluation,
    evaluate_mandate_health_readiness_from_manage,
)
from app.domain import (
    EvidenceFreshness,
    MandateHealthSignalPolicy,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
)
from app.domain.proof_evidence import EvidenceClass
from app.ports.manage_sources import (
    ManageActionRegisterRuntimeEvidence,
    ManageMandateHealthEvidence,
    ManageMandateHealthSourcePort,
)

MANAGE_MANDATE_RUNTIME_EXECUTION_ENV = "LOTUS_IDEA_MANAGE_MANDATE_LIVE_PROOF"
MANAGE_MANDATE_RUNTIME_EXECUTION_SCHEMA_VERSION = (
    "lotus-idea.manage-mandate.runtime-execution.v2"
)
MANAGE_MANDATE_RUNTIME_BLOCKERS_SATISFIED = (
    "opportunity_archetype_portfolio_scoped_manage_source_proof_missing",
    "opportunity_archetype_mandate_performance_health_source_ref_missing",
    "opportunity_archetype_mandate_risk_health_source_ref_missing",
)
MANAGE_MANDATE_REMAINING_BLOCKERS = (
    "opportunity_archetype_core_portfolio_state_source_ref_missing",
    "opportunity_archetype_data_mesh_not_certified",
    "opportunity_archetype_workbench_product_proof_missing",
    "opportunity_archetype_client_publication_not_ready",
    "opportunity_archetype_supported_feature_promotion_missing",
    "deployment_certification_missing",
    "production_certification_missing",
)
MANAGE_MANDATE_RUNTIME_EVIDENCE_REFS = (
    "src/app/application/manage_mandate_runtime_evidence/runtime_execution.py",
    "src/app/application/manage_mandate_runtime_evidence/contract.py",
    "src/app/application/mandate_health_signal.py",
    "src/app/ports/manage_sources.py",
    "src/app/infrastructure/lotus_manage_sources.py",
    "scripts/manage_mandate_runtime_evidence/generate_runtime_execution.py",
    "contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json",
    "make manage-mandate-live-proof-contract-gate",
)

_ACTION_PRODUCT_ID = "lotus-manage:PortfolioActionRegister:v1"
_PERFORMANCE_PRODUCT_ID = "lotus-performance:MandatePerformanceHealthContext:v1"
_RISK_PRODUCT_ID = "lotus-risk:MandateRiskHealthContext:v1"
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class EvaluateManageMandateReadiness:
    tenant_id: str
    portfolio_id: str
    as_of_date: date
    evaluated_at_utc: datetime
    correlation_id: str | None = None
    trace_id: str | None = None

    def __post_init__(self) -> None:
        if not self.tenant_id.strip() or not self.portfolio_id.strip():
            raise ValueError("tenant_id and portfolio_id are required")
        require_aware(self.evaluated_at_utc, "evaluated_at_utc")
        if self.correlation_id is not None and not self.correlation_id.strip():
            raise ValueError("correlation_id must not be blank")


@dataclass(frozen=True)
class ManageMandateReadinessResult:
    command: EvaluateManageMandateReadiness
    source_evaluation: MandateHealthSourceEvaluation
    policy: MandateHealthSignalPolicy


def evaluate_manage_mandate_readiness(
    command: EvaluateManageMandateReadiness,
    *,
    manage_source: ManageMandateHealthSourcePort,
    policy: MandateHealthSignalPolicy = DEFAULT_MANDATE_HEALTH_POLICY,
) -> ManageMandateReadinessResult:
    source_evaluation = evaluate_mandate_health_readiness_from_manage(
        EvaluateMandateHealthFromManageCommand(
            tenant_id=command.tenant_id,
            portfolio_id=command.portfolio_id,
            as_of_date=command.as_of_date,
            evaluated_at_utc=command.evaluated_at_utc,
            correlation_id=command.correlation_id,
            trace_id=command.trace_id,
        ),
        manage_source=manage_source,
        policy=policy,
    )
    return ManageMandateReadinessResult(
        command=command,
        source_evaluation=source_evaluation,
        policy=policy,
    )


def build_manage_mandate_runtime_execution(
    *,
    generated_at_utc: datetime,
    result: ManageMandateReadinessResult,
) -> dict[str, Any]:
    require_aware(generated_at_utc, "generated_at_utc")
    evidence = result.source_evaluation.evidence
    blockers = _qualification_blockers(result)
    return _payload(
        generated_at_utc=generated_at_utc,
        command=result.command,
        policy_version=result.policy.policy_version,
        status="completed" if evidence is not None else "blocked",
        action_receipt=_action_register_receipt(evidence),
        performance_receipt=_source_receipt(
            evidence.mandate_performance_health_ref if evidence else None
        ),
        risk_receipt=_source_receipt(evidence.mandate_risk_health_ref if evidence else None),
        evaluation_receipt=_evaluation_receipt(result),
        qualification_blockers=blockers,
    )


def build_blocked_manage_mandate_runtime_execution(
    *,
    generated_at_utc: datetime,
    command: EvaluateManageMandateReadiness,
    error_code: str,
) -> dict[str, Any]:
    require_aware(generated_at_utc, "generated_at_utc")
    return _payload(
        generated_at_utc=generated_at_utc,
        command=command,
        policy_version=DEFAULT_MANDATE_HEALTH_POLICY.policy_version,
        status="blocked",
        action_receipt=None,
        performance_receipt=None,
        risk_receipt=None,
        evaluation_receipt=None,
        qualification_blockers=("manage_source_execution_blocked", error_code),
    )


def _payload(
    *,
    generated_at_utc: datetime,
    command: EvaluateManageMandateReadiness,
    policy_version: str,
    status: str,
    action_receipt: dict[str, Any] | None,
    performance_receipt: dict[str, Any] | None,
    risk_receipt: dict[str, Any] | None,
    evaluation_receipt: dict[str, Any] | None,
    qualification_blockers: tuple[str, ...],
) -> dict[str, Any]:
    blockers = tuple(dict.fromkeys(qualification_blockers))
    return {
        "schemaVersion": MANAGE_MANDATE_RUNTIME_EXECUTION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "proofFamily": "allocation_drift_mandate_review",
        "proofType": "lotus_manage_mandate_health_evaluation",
        "sourceAuthority": SourceSystem.LOTUS_MANAGE.value,
        "generatedAtUtc": format_utc(generated_at_utc),
        "execution": {
            "status": status,
            "evaluatedAtUtc": format_utc(command.evaluated_at_utc),
            "requestReceipt": _request_receipt(command, policy_version=policy_version),
            "actionRegisterReceipt": action_receipt,
            "mandatePerformanceHealthReceipt": performance_receipt,
            "mandateRiskHealthReceipt": risk_receipt,
            "evaluationReceipt": evaluation_receipt,
            "qualificationBlockers": list(blockers),
        },
        "aggregateBlockersSatisfied": (
            list(MANAGE_MANDATE_RUNTIME_BLOCKERS_SATISFIED) if not blockers else []
        ),
        "remainingCertificationBlockers": list(MANAGE_MANDATE_REMAINING_BLOCKERS),
        "evidenceRefs": list(MANAGE_MANDATE_RUNTIME_EVIDENCE_REFS),
        "nonProofClaims": {
            "mandateFactsOwned": "lotus-manage",
            "performanceFactsOwned": "lotus-performance",
            "riskFactsOwned": "lotus-risk",
            "opportunityDetectionOwned": "lotus-idea",
            "mandateComplianceApproved": False,
            "rebalanceActionCreated": False,
            "orderCreated": False,
            "executionReady": False,
            "suitabilityCertified": False,
            "dataMeshRuntimeCertified": False,
            "gatewayWorkbenchRuntimeObserved": False,
            "clientPublicationApproved": False,
            "deploymentCertified": False,
            "productionCertified": False,
            "supportedFeaturePromoted": False,
            "ideaPersistenceRequired": False,
        },
    }


def _qualification_blockers(result: ManageMandateReadinessResult) -> tuple[str, ...]:
    evidence = result.source_evaluation.evidence
    if evidence is None:
        return (
            "manage_source_evidence_missing",
            result.source_evaluation.source_error_code or "manage_source_execution_blocked",
        )
    blockers: list[str] = []
    runtime = evidence.action_register_runtime
    if runtime is None:
        blockers.append("manage_action_register_runtime_receipt_missing")
    else:
        blockers.extend(_runtime_blockers(result.command, runtime))
    blockers.extend(
        _source_ref_blockers(
            evidence.action_register_ref,
            product_id=_ACTION_PRODUCT_ID,
            source_system=SourceSystem.LOTUS_MANAGE,
            command=result.command,
            prefix="manage_action_register",
        )
    )
    blockers.extend(
        _source_ref_blockers(
            evidence.mandate_performance_health_ref,
            product_id=_PERFORMANCE_PRODUCT_ID,
            source_system=SourceSystem.LOTUS_PERFORMANCE,
            command=result.command,
            prefix="mandate_performance_health",
        )
    )
    blockers.extend(
        _source_ref_blockers(
            evidence.mandate_risk_health_ref,
            product_id=_RISK_PRODUCT_ID,
            source_system=SourceSystem.LOTUS_RISK,
            command=result.command,
            prefix="mandate_risk_health",
        )
    )
    if not evidence.entitlement_allowed:
        blockers.append("manage_source_entitlement_denied")
    if not evidence.portfolio_scope_confirmed:
        blockers.append("manage_portfolio_scope_not_confirmed")
    if (evidence.supportability_state or "").lower() != "ready":
        blockers.append("manage_action_register_not_ready")
    if evidence.supportability_reason != "supportability_summary_ready":
        blockers.append("manage_supportability_reason_not_ready")
    if (evidence.freshness_bucket or "").lower() not in {"current", "same_day"}:
        blockers.append("manage_supportability_not_current")
    blockers.extend(_count_and_outcome_blockers(result, evidence))
    return tuple(dict.fromkeys(blockers))


def _runtime_blockers(
    command: EvaluateManageMandateReadiness,
    runtime: ManageActionRegisterRuntimeEvidence,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if runtime.product_id != _ACTION_PRODUCT_ID or runtime.product_version != "v1":
        blockers.append("manage_action_register_product_mismatch")
    if runtime.tenant_id_hash != identity_hash(command.tenant_id):
        blockers.append("manage_action_register_tenant_scope_mismatch")
    if runtime.portfolio_id != command.portfolio_id or runtime.as_of_date != command.as_of_date:
        blockers.append("manage_action_register_scope_mismatch")
    if (
        runtime.generated_at_utc.tzinfo is None
        or runtime.generated_at_utc.utcoffset() is None
        or runtime.generated_at_utc > command.evaluated_at_utc
    ):
        blockers.append("manage_action_register_future_evidence")
    if runtime.correlation_id != command.correlation_id:
        blockers.append("manage_action_register_correlation_mismatch")
    if runtime.run_count < 0 or runtime.operation_count < 0:
        blockers.append("manage_action_register_counts_invalid")
    if not _is_sha256(runtime.source_batch_fingerprint):
        blockers.append("manage_action_register_fingerprint_invalid")
    return tuple(blockers)


def _source_ref_blockers(
    ref: SourceRef | None,
    *,
    product_id: str,
    source_system: SourceSystem,
    command: EvaluateManageMandateReadiness,
    prefix: str,
) -> tuple[str, ...]:
    if ref is None or ref.product_id != product_id or ref.source_system is not source_system:
        return (f"{prefix}_source_ref_missing",)
    blockers: list[str] = []
    if ref.product_version != "v1":
        blockers.append(f"{prefix}_version_mismatch")
    if ref.as_of_date != command.as_of_date:
        blockers.append(f"{prefix}_scope_mismatch")
    if ref.generated_at_utc > command.evaluated_at_utc:
        blockers.append(f"{prefix}_future_evidence")
    if ref.freshness is not EvidenceFreshness.CURRENT:
        blockers.append(f"{prefix}_evidence_not_current")
    if not _is_sha256(ref.content_hash):
        blockers.append(f"{prefix}_content_hash_invalid")
    return tuple(blockers)


def _count_and_outcome_blockers(
    result: ManageMandateReadinessResult,
    evidence: ManageMandateHealthEvidence,
) -> tuple[str, ...]:
    workflow_count = evidence.workflow_decision_count
    lineage_count = evidence.lineage_edge_count
    if (
        not isinstance(workflow_count, int)
        or isinstance(workflow_count, bool)
        or workflow_count < 0
        or not isinstance(lineage_count, int)
        or isinstance(lineage_count, bool)
        or lineage_count < 0
    ):
        return ("manage_evidence_counts_invalid",)
    evaluation = result.source_evaluation.evaluation
    should_create = (
        workflow_count >= result.policy.minimum_workflow_decision_count
        and lineage_count >= result.policy.minimum_lineage_edge_count
    )
    if should_create:
        if (
            evaluation.outcome is not SignalEvaluationOutcome.CANDIDATE_CREATED
            or evaluation.candidate is None
            or evaluation.signal is None
        ):
            return ("manage_candidate_outcome_mismatch",)
    elif (
        evaluation.outcome is not SignalEvaluationOutcome.NOT_ELIGIBLE
        or evaluation.candidate is not None
        or evaluation.signal is not None
    ):
        return ("manage_no_opportunity_outcome_mismatch",)
    return ()


def _request_receipt(
    command: EvaluateManageMandateReadiness,
    *,
    policy_version: str,
) -> dict[str, Any]:
    material = {
        "tenantIdHash": identity_hash(command.tenant_id),
        "portfolioIdHash": identity_hash(command.portfolio_id),
        "asOfDate": command.as_of_date.isoformat(),
        "evaluatedAtUtc": format_utc(command.evaluated_at_utc),
        "consumerSystem": "lotus-idea",
        "correlationIdHash": (
            identity_hash(command.correlation_id) if command.correlation_id else None
        ),
        "policyVersion": policy_version,
    }
    return {**material, "requestDigest": sha256_json(material)}


def _action_register_receipt(
    evidence: ManageMandateHealthEvidence | None,
) -> dict[str, Any] | None:
    if evidence is None or evidence.action_register_runtime is None:
        return None
    base = source_ref_receipt(evidence.action_register_ref)
    if base is None:
        return None
    runtime = evidence.action_register_runtime
    upstream = [
        receipt
        for receipt in (
            source_ref_receipt(evidence.mandate_performance_health_ref),
            source_ref_receipt(evidence.mandate_risk_health_ref),
        )
        if receipt is not None
    ]
    material = {key: value for key, value in base.items() if key != "receiptDigest"}
    material.update(
        {
            "responseTenantIdHash": runtime.tenant_id_hash,
            "responsePortfolioIdHash": identity_hash(runtime.portfolio_id),
            "responseAsOfDate": runtime.as_of_date.isoformat(),
            "responseGeneratedAtUtc": format_utc(runtime.generated_at_utc),
            "sourceBatchFingerprint": runtime.source_batch_fingerprint,
            "runCount": runtime.run_count,
            "operationCount": runtime.operation_count,
            "workflowDecisionCount": evidence.workflow_decision_count,
            "lineageEdgeCount": evidence.lineage_edge_count,
            "supportabilityState": evidence.supportability_state,
            "supportabilityReason": evidence.supportability_reason,
            "freshnessBucket": evidence.freshness_bucket,
            "portfolioScopeConfirmed": evidence.portfolio_scope_confirmed,
            "sourceCorrelationIdHash": (
                identity_hash(runtime.correlation_id) if runtime.correlation_id else None
            ),
            "upstreamSourceRefsDigest": sha256_json(upstream),
        }
    )
    return {**material, "receiptDigest": sha256_json(material)}


def _source_receipt(ref: SourceRef | None) -> dict[str, Any] | None:
    return source_ref_receipt(ref)


def _evaluation_receipt(result: ManageMandateReadinessResult) -> dict[str, Any]:
    evaluation = result.source_evaluation.evaluation
    evidence = result.source_evaluation.evidence
    material = {
        "family": evaluation.family.value,
        "outcome": evaluation.outcome.value,
        "reasonCodes": [value.value for value in evaluation.reason_codes],
        "unsupportedReasons": [value.value for value in evaluation.unsupported_reasons],
        "policyVersion": result.policy.policy_version,
        "minimumWorkflowDecisionCount": result.policy.minimum_workflow_decision_count,
        "minimumLineageEdgeCount": result.policy.minimum_lineage_edge_count,
        "candidateScore": str(result.policy.candidate_score),
        "candidateIdHash": (
            identity_hash(evaluation.candidate.candidate_id) if evaluation.candidate else None
        ),
        "signalIdHash": identity_hash(evaluation.signal.signal_id) if evaluation.signal else None,
        "evidencePacketIdHash": (
            identity_hash(evaluation.candidate.evidence_packet.evidence_packet_id)
            if evaluation.candidate
            else None
        ),
        "sourceRefsDigest": sha256_json(
            [
                receipt
                for receipt in (
                    source_ref_receipt(evidence.action_register_ref) if evidence else None,
                    source_ref_receipt(evidence.mandate_performance_health_ref)
                    if evidence
                    else None,
                    source_ref_receipt(evidence.mandate_risk_health_ref) if evidence else None,
                )
                if receipt is not None
            ]
        ),
    }
    return {**material, "evaluationDigest": sha256_json(material)}


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_PATTERN.fullmatch(value) is not None
