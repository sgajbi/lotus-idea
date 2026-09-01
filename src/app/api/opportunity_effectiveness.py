from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI, Query, status
from fastapi.responses import JSONResponse

from app.api.caller_headers import CallerContextHeaders
from app.api.opportunity_effectiveness_models import OpportunityEffectivenessResponse
from app.api.problem_details import (
    invalid_request_metadata,
    permission_denied_metadata,
    problem_details_response,
    service_unavailable_metadata,
)
from app.api.route_metadata import RouteMetadata
from app.api.runtime_dependencies import (
    get_idea_repository,
    idea_repository_durable_storage_backed,
)
from app.api.telemetry_buckets import bounded_count_bucket
from app.application.opportunity_effectiveness import (
    MAX_EFFECTIVENESS_OPPORTUNITIES,
    OpportunityEffectivenessBoundExceeded,
    OpportunityEffectivenessDataError,
    OpportunityEffectivenessScopeError,
    build_opportunity_effectiveness_snapshot,
    build_opportunity_effectiveness_snapshot_from_summary,
    validate_opportunity_effectiveness_scope,
)
from app.ports.idea_repository import OpportunityEffectivenessProjectionRepository
from app.observability import (
    IdeaOperation,
    OperationEvent,
    OperationOutcome,
    OperationSupportability,
    emit_operation_event,
)
from app.security.caller_context import (
    CapabilityPolicy,
    PermissionDeniedError,
    require_role_and_capability,
)


_READ_OPPORTUNITY_EFFECTIVENESS_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.opportunity-effectiveness.read",
    allowed_roles=("operator",),
)


async def get_opportunity_effectiveness(
    caller: CallerContextHeaders,
    tenant_id: str = Query(alias="tenantId"),
    window_start_utc: datetime = Query(alias="windowStartUtc"),
    window_end_utc: datetime = Query(alias="windowEndUtc"),
    evaluated_at_utc: datetime = Query(alias="evaluatedAtUtc"),
    max_opportunities: int = Query(
        default=MAX_EFFECTIVENESS_OPPORTUNITIES,
        alias="maxOpportunities",
    ),
) -> OpportunityEffectivenessResponse | JSONResponse:
    permission_error = _permission_error(caller, tenant_id=tenant_id)
    if permission_error is not None:
        _emit_effectiveness_event(OperationOutcome.PERMISSION_DENIED)
        return permission_error
    try:
        validate_opportunity_effectiveness_scope(
            tenant_id=tenant_id,
            window_start_utc=window_start_utc,
            window_end_utc=window_end_utc,
            evaluated_at_utc=evaluated_at_utc,
            max_opportunities=max_opportunities,
        )
        repository = get_idea_repository()
        if isinstance(repository, OpportunityEffectivenessProjectionRepository):
            summary = repository.opportunity_effectiveness_summary(
                tenant_id=tenant_id,
                window_start_utc=window_start_utc,
                window_end_utc=window_end_utc,
                evaluated_at_utc=evaluated_at_utc,
                max_opportunities=max_opportunities,
            )
            snapshot = build_opportunity_effectiveness_snapshot_from_summary(
                summary,
                tenant_id=tenant_id,
                window_start_utc=window_start_utc,
                window_end_utc=window_end_utc,
                evaluated_at_utc=evaluated_at_utc,
                max_opportunities=max_opportunities,
            )
        else:
            snapshot = build_opportunity_effectiveness_snapshot(
                repository.snapshot(),
                tenant_id=tenant_id,
                window_start_utc=window_start_utc,
                window_end_utc=window_end_utc,
                evaluated_at_utc=evaluated_at_utc,
                max_opportunities=max_opportunities,
            )
    except (
        OpportunityEffectivenessScopeError,
        OpportunityEffectivenessBoundExceeded,
        ValueError,
    ) as exc:
        if isinstance(exc, OpportunityEffectivenessDataError):
            _emit_effectiveness_event(OperationOutcome.BLOCKED)
            return _unavailable_response()
        _emit_effectiveness_event(OperationOutcome.INVALID_REQUEST)
        return problem_details_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail=str(exc),
        )
    except (RuntimeError, TypeError):
        _emit_effectiveness_event(OperationOutcome.BLOCKED)
        return _unavailable_response()
    _emit_effectiveness_event(
        OperationOutcome.ACCEPTED,
        durable_storage_backed=idea_repository_durable_storage_backed(repository),
        generated_opportunity_count=snapshot.generated_opportunity_count,
    )
    return OpportunityEffectivenessResponse.from_domain(snapshot)


def _permission_error(caller: CallerContextHeaders, *, tenant_id: str) -> JSONResponse | None:
    try:
        require_role_and_capability(caller, _READ_OPPORTUNITY_EFFECTIVENESS_POLICY)
    except PermissionDeniedError:
        return _permission_denied_response()
    if tenant_id not in caller.entitlement_scope.tenant_ids:
        return _permission_denied_response()
    return None


def _permission_denied_response() -> JSONResponse:
    return problem_details_response(
        status_code=status.HTTP_403_FORBIDDEN,
        code="permission_denied",
        title="Permission denied",
        detail="The caller is not permitted to read this tenant's opportunity effectiveness.",
    )


def _unavailable_response() -> JSONResponse:
    return problem_details_response(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        code="opportunity_effectiveness_unavailable",
        title="Opportunity effectiveness unavailable",
        detail="Governed opportunity-effectiveness facts are unavailable or inconsistent.",
    )


def _rate_example(numerator: int, denominator: int, value: str) -> dict[str, object]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": value,
        "zeroDenominatorBehavior": "null",
    }


def _duration_example(
    observation_count: int,
    minimum: str,
    median: str,
    maximum: str,
) -> dict[str, object]:
    return {
        "observationCount": observation_count,
        "minimumSeconds": minimum,
        "p50Seconds": median,
        "p95Seconds": maximum,
        "maximumSeconds": maximum,
    }


def _emit_effectiveness_event(
    outcome: OperationOutcome,
    *,
    durable_storage_backed: bool = False,
    generated_opportunity_count: int | None = None,
) -> None:
    attributes = (
        {"generated_opportunity_count_bucket": bounded_count_bucket(generated_opportunity_count)}
        if generated_opportunity_count is not None
        else {}
    )
    emit_operation_event(
        OperationEvent(
            operation=IdeaOperation.OPPORTUNITY_EFFECTIVENESS_READ,
            outcome=outcome,
            source_authority="lotus-idea",
            supportability_status=OperationSupportability.NOT_CERTIFIED,
            durable_storage_backed=durable_storage_backed,
            supported_feature_promoted=False,
            attributes=attributes,
        )
    )


OPPORTUNITY_EFFECTIVENESS_ROUTE: RouteMetadata = {
    "path": "/api/v1/operations/opportunity-effectiveness",
    "operation_id": "getIdeaOpportunityEffectiveness",
    "summary": "Get governed opportunity effectiveness",
    "description": (
        "Returns a bounded, single-tenant opportunity funnel for an economic-opportunity "
        "generation cohort. Outcomes are observed at or before evaluatedAtUtc, rates expose "
        "their exact numerators and denominators, zero denominators return null, and the "
        "response excludes raw tenant, client, portfolio, candidate, actor, correlation, and "
        "free-text data. PostgreSQL runtime execution uses repository-side aggregates. "
        "Presentation and ranked-quality measures use immutable Workbench receipts and exact-"
        "version governed judgments when available; incomplete exposure or judgment evidence "
        "remains explicit and queue retrieval is never treated as presentation."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": OpportunityEffectivenessResponse,
    "tags": ["Operations"],
    "responses": {
        200: {
            "description": "Privacy-safe opportunity-effectiveness snapshot returned.",
            "content": {
                "application/json": {
                    "example": {
                        "schemaVersion": "lotus-idea.opportunity-effectiveness.v3",
                        "methodologyPolicyVersion": "idea-opportunity-effectiveness-v5",
                        "window": {
                            "startUtcInclusive": "2026-06-21T00:00:00Z",
                            "endUtcExclusive": "2026-06-22T00:00:00Z",
                            "evaluatedAtUtc": "2026-06-23T00:00:00Z",
                            "population": ("economic_opportunities_first_generated_in_window"),
                            "outcomeObservation": (
                                "latest_governed_fact_at_or_before_evaluated_at"
                            ),
                        },
                        "counts": {
                            "generatedOpportunityCount": 24,
                            "reviewedOpportunityCount": 18,
                            "feedbackOpportunityCount": 12,
                            "conversionOpportunityCount": 7,
                            "conversionIntentCount": 7,
                            "staleEvidenceOpportunityCount": 2,
                            "unavailableEvidenceOpportunityCount": 1,
                            "unsupportedEvidenceOpportunityCount": 3,
                            "suppressedOpportunityCount": 4,
                            "duplicateSuppressedOpportunityCount": 2,
                            "recurrentOpportunityCount": 3,
                            "recurrentDetectionCount": 5,
                            "reconciledSubmissionCount": 1,
                        },
                        "presentation": {
                            "measurementStatus": ("unavailable_consumer_certification_pending"),
                            "presentedOpportunityCount": None,
                            "topRankedPresentedOpportunityCount": None,
                            "topRankedAcceptedOpportunityCount": None,
                            "presentationRate": None,
                            "topRankedAcceptanceRate": None,
                            "rankingQuality": {
                                "policyVersion": "idea-ranking-evaluation-v1",
                                "minimumReadySnapshotCount": 30,
                                "recallStatus": "unavailable_incomplete_relevant_set",
                                "cutoffs": [],
                                "stability": {
                                    "comparableSnapshotPairCount": 0,
                                    "meanNormalizedStability": None,
                                },
                            },
                        },
                        "familyEffectiveness": [],
                        "dimensions": {
                            "opportunityFamily": [
                                {"value": "high_cash", "count": 10},
                                {"value": "concentration", "count": 8},
                                {"value": "underperformance", "count": 6},
                            ],
                            "currentScoreBand": [
                                {"value": "critical", "count": 4},
                                {"value": "high", "count": 11},
                                {"value": "standard", "count": 7},
                                {"value": "watchlist", "count": 1},
                                {"value": "unranked", "count": 1},
                            ],
                            "latestReviewAction": [
                                {"value": "approve_for_conversion", "count": 7},
                                {"value": "reject", "count": 7},
                                {"value": "suppress", "count": 4},
                            ],
                            "feedbackReason": [
                                {"value": "relevant", "count": 8},
                                {"value": "wrong_timing", "count": 4},
                            ],
                            "currentDownstreamOutcome": [
                                {"value": "accepted", "count": 4},
                                {"value": "rejected", "count": 1},
                                {"value": "failed", "count": 1},
                                {"value": "requested", "count": 1},
                            ],
                            "downstreamSubmissionPosture": [
                                {"value": "accepted_by_downstream", "count": 4},
                                {"value": "reconciliation_required", "count": 1},
                            ],
                        },
                        "rates": {
                            "review": _rate_example(18, 24, "0.750000"),
                            "approval": _rate_example(7, 18, "0.388889"),
                            "rejection": _rate_example(7, 18, "0.388889"),
                            "suppression": _rate_example(4, 18, "0.222222"),
                            "feedback": _rate_example(12, 18, "0.666667"),
                            "conversion": _rate_example(7, 7, "1.000000"),
                            "downstreamAccepted": _rate_example(4, 7, "0.571429"),
                            "downstreamRejected": _rate_example(1, 7, "0.142857"),
                            "downstreamFailed": _rate_example(1, 7, "0.142857"),
                            "downstreamUncertain": _rate_example(1, 7, "0.142857"),
                        },
                        "timings": {
                            "detectionToReview": _duration_example(18, "900", "3600", "14400"),
                            "approvalToConversion": _duration_example(7, "300", "1800", "7200"),
                        },
                        "privacyBoundary": {
                            "scope": "single_tenant",
                            "containsRawTenantIdentifier": False,
                            "containsRawClientIdentifier": False,
                            "containsRawPortfolioIdentifier": False,
                            "containsRawCandidateIdentifier": False,
                            "containsBusinessIdentityIdentifier": False,
                            "containsActorSubject": False,
                            "containsCorrelationOrTraceIdentifier": False,
                            "containsFreeText": False,
                        },
                        "certificationStatus": "not_certified",
                        "certificationBlockers": [
                            "governed_presentation_receipt_consumer_proof_missing",
                            "gateway_workbench_end_to_end_proof_missing",
                        ],
                        "supportedFeaturePromoted": False,
                        "productionMutationAuthority": ("none_read_only_effectiveness_evidence"),
                        "snapshotDigest": f"sha256:{'a' * 64}",
                    }
                }
            },
        },
        **invalid_request_metadata(
            detail="Correct the tenant, UTC window, evaluation time, or bounded cohort size."
        ),
        **permission_denied_metadata(
            detail="The caller lacks operator capability or exact tenant entitlement.",
            description="Caller cannot read this tenant's effectiveness snapshot.",
        ),
        **service_unavailable_metadata(
            code="opportunity_effectiveness_unavailable",
            title="Opportunity effectiveness unavailable",
            detail="Governed opportunity-effectiveness facts are unavailable or inconsistent.",
            description="Durable effectiveness facts failed closed.",
        ),
    },
}


def register_opportunity_effectiveness_routes(app: FastAPI) -> None:
    app.get(
        path=OPPORTUNITY_EFFECTIVENESS_ROUTE["path"],
        operation_id=OPPORTUNITY_EFFECTIVENESS_ROUTE["operation_id"],
        summary=OPPORTUNITY_EFFECTIVENESS_ROUTE["summary"],
        description=OPPORTUNITY_EFFECTIVENESS_ROUTE["description"],
        status_code=OPPORTUNITY_EFFECTIVENESS_ROUTE["status_code"],
        response_model=OPPORTUNITY_EFFECTIVENESS_ROUTE["response_model"],
        tags=OPPORTUNITY_EFFECTIVENESS_ROUTE["tags"],
        responses=OPPORTUNITY_EFFECTIVENESS_ROUTE["responses"],
    )(get_opportunity_effectiveness)


__all__ = ["OPPORTUNITY_EFFECTIVENESS_ROUTE", "register_opportunity_effectiveness_routes"]
