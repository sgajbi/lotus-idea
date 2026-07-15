from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.domain import (
    CandidateScorePolicyVersion,
    MandateHealthSignalInput,
    MandateHealthSignalPolicy,
    OpportunityFamily,
    ReasonCode,
    SignalEvaluationOutcome,
    SignalEvaluationResult,
    SourceRef,
    UnsupportedEvidenceReason,
    evaluate_mandate_health_signal,
)
from app.application.access_scope import tenant_portfolio_scope
from app.domain.access_scope import ReviewAccessScope
from app.ports.manage_sources import (
    ManageMandateHealthSourcePort,
    ManageMandateHealthEvidence,
    ManageMandateHealthEvidenceRequest,
    ManageSourceEntitlementDenied,
    ManageSourceUnavailable,
)


@dataclass(frozen=True)
class EvaluateMandateHealthSignalCommand:
    as_of_date: date
    workflow_decision_count: int | None
    lineage_edge_count: int | None
    manage_supportability_state: str | None
    portfolio_scope_confirmed: bool
    action_register_ref: SourceRef | None
    evaluated_at_utc: datetime
    mandate_performance_health_ref: SourceRef | None = None
    mandate_risk_health_ref: SourceRef | None = None
    entitlement_allowed: bool = True
    access_scope: ReviewAccessScope | None = None
    duplicate_of_candidate_id: str | None = None


@dataclass(frozen=True)
class EvaluateMandateHealthFromManageCommand:
    tenant_id: str
    portfolio_id: str
    as_of_date: date
    evaluated_at_utc: datetime
    duplicate_of_candidate_id: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None


DEFAULT_MANDATE_HEALTH_POLICY = MandateHealthSignalPolicy(
    policy_version=CandidateScorePolicyVersion.ALLOCATION_DRIFT.value,
    minimum_workflow_decision_count=1,
    minimum_lineage_edge_count=1,
    candidate_score=Decimal("70"),
)


def evaluate_mandate_health_signal_command(
    command: EvaluateMandateHealthSignalCommand,
    *,
    policy: MandateHealthSignalPolicy = DEFAULT_MANDATE_HEALTH_POLICY,
) -> SignalEvaluationResult:
    source_input = MandateHealthSignalInput(
        as_of_date=command.as_of_date,
        workflow_decision_count=command.workflow_decision_count,
        lineage_edge_count=command.lineage_edge_count,
        manage_supportability_state=command.manage_supportability_state,
        portfolio_scope_confirmed=command.portfolio_scope_confirmed,
        action_register_ref=command.action_register_ref,
        mandate_performance_health_ref=command.mandate_performance_health_ref,
        mandate_risk_health_ref=command.mandate_risk_health_ref,
        evaluated_at_utc=command.evaluated_at_utc,
        entitlement_allowed=command.entitlement_allowed,
        access_scope=command.access_scope,
        duplicate_of_candidate_id=command.duplicate_of_candidate_id,
    )
    return evaluate_mandate_health_signal(source_input, policy)


def evaluate_mandate_health_signal_from_manage(
    command: EvaluateMandateHealthFromManageCommand,
    *,
    manage_source: ManageMandateHealthSourcePort,
    policy: MandateHealthSignalPolicy = DEFAULT_MANDATE_HEALTH_POLICY,
) -> SignalEvaluationResult:
    try:
        evidence = manage_source.fetch_mandate_health_evidence(
            ManageMandateHealthEvidenceRequest(
                tenant_id=command.tenant_id,
                portfolio_id=command.portfolio_id,
                as_of_date=command.as_of_date,
                evaluated_at_utc=command.evaluated_at_utc,
                correlation_id=command.correlation_id,
                trace_id=command.trace_id,
            )
        )
    except ManageSourceEntitlementDenied:
        return evaluate_mandate_health_signal_command(
            EvaluateMandateHealthSignalCommand(
                as_of_date=command.as_of_date,
                workflow_decision_count=None,
                lineage_edge_count=None,
                manage_supportability_state=None,
                portfolio_scope_confirmed=False,
                action_register_ref=None,
                mandate_performance_health_ref=None,
                mandate_risk_health_ref=None,
                evaluated_at_utc=command.evaluated_at_utc,
                entitlement_allowed=False,
                access_scope=tenant_portfolio_scope(
                    tenant_id=command.tenant_id,
                    portfolio_id=command.portfolio_id,
                ),
                duplicate_of_candidate_id=command.duplicate_of_candidate_id,
            ),
            policy=policy,
        )
    except ManageSourceUnavailable:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.BLOCKED,
            family=OpportunityFamily.ALLOCATION_DRIFT,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.SOURCE_UNAVAILABLE,),
        )

    return _evaluate_mandate_health_evidence(command, evidence, policy=policy)


def _evaluate_mandate_health_evidence(
    command: EvaluateMandateHealthFromManageCommand,
    evidence: ManageMandateHealthEvidence,
    *,
    policy: MandateHealthSignalPolicy,
) -> SignalEvaluationResult:
    return evaluate_mandate_health_signal_command(
        EvaluateMandateHealthSignalCommand(
            as_of_date=command.as_of_date,
            workflow_decision_count=evidence.workflow_decision_count,
            lineage_edge_count=evidence.lineage_edge_count,
            manage_supportability_state=evidence.supportability_state,
            portfolio_scope_confirmed=evidence.portfolio_scope_confirmed,
            action_register_ref=evidence.action_register_ref,
            mandate_performance_health_ref=evidence.mandate_performance_health_ref,
            mandate_risk_health_ref=evidence.mandate_risk_health_ref,
            evaluated_at_utc=command.evaluated_at_utc,
            entitlement_allowed=evidence.entitlement_allowed,
            access_scope=tenant_portfolio_scope(
                tenant_id=command.tenant_id,
                portfolio_id=command.portfolio_id,
            ),
            duplicate_of_candidate_id=command.duplicate_of_candidate_id,
        ),
        policy=policy,
    )
