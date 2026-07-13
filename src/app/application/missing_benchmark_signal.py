from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.domain import (
    CandidateScorePolicyVersion,
    MissingBenchmarkSignalInput,
    MissingBenchmarkSignalPolicy,
    OpportunityFamily,
    ReasonCode,
    SignalEvaluationOutcome,
    SignalEvaluationResult,
    SourceRef,
    UnsupportedEvidenceReason,
    evaluate_missing_benchmark_signal,
)
from app.application.access_scope import tenant_portfolio_scope
from app.domain.access_scope import ReviewAccessScope
from app.ports.core_sources import (
    CoreBenchmarkAssignmentEvidence,
    CoreBenchmarkAssignmentEvidenceRequest,
    CoreBenchmarkAssignmentSourcePort,
    CoreSourceEntitlementDenied,
    CoreSourceUnavailable,
)


@dataclass(frozen=True)
class EvaluateMissingBenchmarkSignalCommand:
    as_of_date: date
    benchmark_assignment_ref: SourceRef | None
    benchmark_identity_resolved: bool
    assignment_effective_for_as_of_date: bool
    assignment_status: str | None
    assignment_version_present: bool
    evaluated_at_utc: datetime
    entitlement_allowed: bool = True
    access_scope: ReviewAccessScope | None = None
    duplicate_of_candidate_id: str | None = None


@dataclass(frozen=True)
class EvaluateMissingBenchmarkFromCoreCommand:
    portfolio_id: str
    tenant_id: str
    as_of_date: date
    evaluated_at_utc: datetime
    reporting_currency: str | None = None
    duplicate_of_candidate_id: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None


DEFAULT_MISSING_BENCHMARK_POLICY = MissingBenchmarkSignalPolicy(
    policy_version=CandidateScorePolicyVersion.MISSING_BENCHMARK.value,
    candidate_score=Decimal("68"),
)


def evaluate_missing_benchmark_signal_command(
    command: EvaluateMissingBenchmarkSignalCommand,
    *,
    policy: MissingBenchmarkSignalPolicy = DEFAULT_MISSING_BENCHMARK_POLICY,
) -> SignalEvaluationResult:
    return evaluate_missing_benchmark_signal(
        MissingBenchmarkSignalInput(
            as_of_date=command.as_of_date,
            benchmark_assignment_ref=command.benchmark_assignment_ref,
            benchmark_identity_resolved=command.benchmark_identity_resolved,
            assignment_effective_for_as_of_date=(command.assignment_effective_for_as_of_date),
            assignment_status=command.assignment_status,
            assignment_version_present=command.assignment_version_present,
            evaluated_at_utc=command.evaluated_at_utc,
            entitlement_allowed=command.entitlement_allowed,
            access_scope=command.access_scope,
            duplicate_of_candidate_id=command.duplicate_of_candidate_id,
        ),
        policy,
    )


def evaluate_missing_benchmark_signal_from_core(
    command: EvaluateMissingBenchmarkFromCoreCommand,
    *,
    core_source: CoreBenchmarkAssignmentSourcePort,
    policy: MissingBenchmarkSignalPolicy = DEFAULT_MISSING_BENCHMARK_POLICY,
) -> SignalEvaluationResult:
    try:
        evidence = core_source.fetch_benchmark_assignment_evidence(
            CoreBenchmarkAssignmentEvidenceRequest(
                portfolio_id=command.portfolio_id,
                tenant_id=command.tenant_id,
                as_of_date=command.as_of_date,
                evaluated_at_utc=command.evaluated_at_utc,
                reporting_currency=command.reporting_currency,
                correlation_id=command.correlation_id,
                trace_id=command.trace_id,
            )
        )
    except CoreSourceEntitlementDenied:
        return evaluate_missing_benchmark_signal_command(
            EvaluateMissingBenchmarkSignalCommand(
                as_of_date=command.as_of_date,
                benchmark_assignment_ref=None,
                benchmark_identity_resolved=False,
                assignment_effective_for_as_of_date=False,
                assignment_status=None,
                assignment_version_present=False,
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
    except CoreSourceUnavailable:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.BLOCKED,
            family=OpportunityFamily.MISSING_BENCHMARK,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.SOURCE_UNAVAILABLE,),
        )

    return _evaluate_missing_benchmark_core_evidence(command, evidence, policy=policy)


def _evaluate_missing_benchmark_core_evidence(
    command: EvaluateMissingBenchmarkFromCoreCommand,
    evidence: CoreBenchmarkAssignmentEvidence,
    *,
    policy: MissingBenchmarkSignalPolicy,
) -> SignalEvaluationResult:
    return evaluate_missing_benchmark_signal_command(
        EvaluateMissingBenchmarkSignalCommand(
            as_of_date=command.as_of_date,
            benchmark_assignment_ref=evidence.benchmark_assignment_ref,
            benchmark_identity_resolved=evidence.benchmark_identity_resolved,
            assignment_effective_for_as_of_date=evidence.assignment_effective_for_as_of_date,
            assignment_status=evidence.assignment_status,
            assignment_version_present=evidence.assignment_version_present,
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
