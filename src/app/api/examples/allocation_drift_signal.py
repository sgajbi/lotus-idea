from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from app.api.allocation_drift_signals import (
    EvaluateAllocationDriftSignalRequest,
    EvaluateAllocationDriftSignalResponse,
)
from app.api.examples.openapi import (
    apply_named_response_examples,
    build_named_openapi_examples,
)
from app.api.examples.signal_evaluation import (
    build_source_ref_request,
    return_or_raise_example_evidence,
    serialize_signal_evaluation,
)
from app.api.signal_models import SourceRefRequest
from app.application.mandate_health_signal import (
    EvaluateMandateHealthFromManageCommand,
    evaluate_mandate_health_signal_command,
    evaluate_mandate_health_signal_from_manage,
)
from app.domain import EvidenceFreshness, SignalEvaluationResult, SourceSystem
from app.ports.manage_sources import (
    ManageMandateHealthEvidence,
    ManageMandateHealthEvidenceRequest,
    ManageMandateHealthSourcePort,
    ManageSourceUnavailable,
)


ALLOCATION_DRIFT_EVALUATE_OPERATION_PATH = "/api/v1/idea-signals/allocation-drift/evaluate"
ALLOCATION_DRIFT_EVALUATE_FROM_SOURCE_OPERATION_PATH = (
    "/api/v1/idea-signals/allocation-drift/evaluate-from-source"
)
ALLOCATION_DRIFT_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES = {
    "candidateCreated": "Manage action-register posture creates a PM-review candidate",
    "blocked": "Incomplete, stale, denied, or unavailable source evidence blocks evaluation",
    "suppressed": "A known duplicate suppresses candidate creation",
    "notEligible": "No material portfolio workflow activity creates no candidate",
}

_AS_OF_DATE = date(2026, 6, 21)
_EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
_SOURCE_AUTHORITY = SourceSystem.LOTUS_MANAGE
_TENANT_ID = "tenant-a"
_PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"


def build_allocation_drift_evaluation_response_examples() -> dict[str, dict[str, Any]]:
    return {
        "candidateCreated": _caller_evaluation_response(),
        "blocked": _caller_evaluation_response(freshness=EvidenceFreshness.STALE),
        "suppressed": _caller_evaluation_response(
            duplicate_of_candidate_id="idea_allocation_drift_existing"
        ),
        "notEligible": _caller_evaluation_response(workflow_decision_count=0),
    }


def build_source_backed_allocation_drift_evaluation_response_examples() -> dict[
    str, dict[str, Any]
]:
    return {
        "candidateCreated": _source_evaluation_response(),
        "blocked": _source_evaluation_response(source_error=ManageSourceUnavailable()),
        "suppressed": _source_evaluation_response(
            duplicate_of_candidate_id="idea_allocation_drift_existing"
        ),
        "notEligible": _source_evaluation_response(workflow_decision_count=0),
    }


def apply_allocation_drift_signal_openapi_examples(
    openapi_schema: dict[str, Any],
) -> dict[str, Any]:
    for operation_path, examples in (
        (
            ALLOCATION_DRIFT_EVALUATE_OPERATION_PATH,
            build_allocation_drift_evaluation_response_examples(),
        ),
        (
            ALLOCATION_DRIFT_EVALUATE_FROM_SOURCE_OPERATION_PATH,
            build_source_backed_allocation_drift_evaluation_response_examples(),
        ),
    ):
        apply_named_response_examples(
            openapi_schema,
            operation_path=operation_path,
            examples=build_named_openapi_examples(
                examples,
                ALLOCATION_DRIFT_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES,
            ),
        )
    return openapi_schema


def _caller_evaluation_response(
    *,
    workflow_decision_count: int = 2,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    duplicate_of_candidate_id: str | None = None,
) -> dict[str, Any]:
    request = EvaluateAllocationDriftSignalRequest(
        asOfDate=_AS_OF_DATE,
        evaluatedAtUtc=_EVALUATED_AT,
        workflowDecisionCount=workflow_decision_count,
        lineageEdgeCount=4,
        manageSupportabilityState="ready",
        portfolioScopeConfirmed=True,
        actionRegisterRef=_source_ref(
            "lotus-manage:PortfolioActionRegister:v1",
            SourceSystem.LOTUS_MANAGE,
            freshness=freshness,
        ),
        entitlementAllowed=True,
        duplicateOfCandidateId=duplicate_of_candidate_id,
    )
    return _serialized(evaluate_mandate_health_signal_command(request.to_command()))


def _source_evaluation_response(
    *,
    workflow_decision_count: int = 2,
    duplicate_of_candidate_id: str | None = None,
    source_error: ManageSourceUnavailable | None = None,
) -> dict[str, Any]:
    result = evaluate_mandate_health_signal_from_manage(
        EvaluateMandateHealthFromManageCommand(
            tenant_id=_TENANT_ID,
            portfolio_id=_PORTFOLIO_ID,
            as_of_date=_AS_OF_DATE,
            evaluated_at_utc=_EVALUATED_AT,
            duplicate_of_candidate_id=duplicate_of_candidate_id,
        ),
        manage_source=_ExampleManageMandateHealthSource(
            evidence=_manage_evidence(workflow_decision_count),
            error=source_error,
        ),
    )
    return _serialized(result)


def _manage_evidence(workflow_decision_count: int) -> ManageMandateHealthEvidence:
    return ManageMandateHealthEvidence(
        workflow_decision_count=workflow_decision_count,
        lineage_edge_count=4,
        supportability_state="ready",
        supportability_reason="supportability_summary_ready",
        freshness_bucket="current",
        portfolio_scope_confirmed=True,
        action_register_ref=_source_ref(
            "lotus-manage:PortfolioActionRegister:v1", SourceSystem.LOTUS_MANAGE
        ).to_domain(),
        mandate_performance_health_ref=_source_ref(
            "lotus-performance:MandatePerformanceHealthContext:v1",
            SourceSystem.LOTUS_PERFORMANCE,
        ).to_domain(),
        mandate_risk_health_ref=_source_ref(
            "lotus-risk:MandateRiskHealthContext:v1", SourceSystem.LOTUS_RISK
        ).to_domain(),
        manage_diagnostic="example_not_exposed",
    )


def _source_ref(
    product_id: str,
    source_system: SourceSystem,
    *,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
) -> SourceRefRequest:
    return build_source_ref_request(
        product_id,
        source_system=source_system,
        as_of_date=_AS_OF_DATE,
        generated_at_utc=_EVALUATED_AT,
        freshness=freshness,
        data_quality_status="ready",
    )


def _serialized(result: SignalEvaluationResult) -> dict[str, Any]:
    return serialize_signal_evaluation(
        result,
        response_model=EvaluateAllocationDriftSignalResponse,
        source_authority=_SOURCE_AUTHORITY,
    )


@dataclass(frozen=True)
class _ExampleManageMandateHealthSource(ManageMandateHealthSourcePort):
    evidence: ManageMandateHealthEvidence
    error: ManageSourceUnavailable | None = None

    def fetch_mandate_health_evidence(
        self, request: ManageMandateHealthEvidenceRequest
    ) -> ManageMandateHealthEvidence:
        del request
        return return_or_raise_example_evidence(self.evidence, self.error)


__all__ = [
    "ALLOCATION_DRIFT_EVALUATE_FROM_SOURCE_OPERATION_PATH",
    "ALLOCATION_DRIFT_EVALUATE_OPERATION_PATH",
    "ALLOCATION_DRIFT_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES",
    "apply_allocation_drift_signal_openapi_examples",
    "build_allocation_drift_evaluation_response_examples",
    "build_source_backed_allocation_drift_evaluation_response_examples",
]
