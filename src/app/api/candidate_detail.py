from __future__ import annotations

from fastapi import FastAPI, Header, Path, status
from fastapi.responses import JSONResponse

from app.api.caller_headers import (
    INVALID_CALLER_SCOPE_DETAIL,
    TRUSTED_CALLER_CONTEXT_HEADER,
    caller_access_scope_filter,
    caller_context_from_headers,
)
from app.api.candidate_detail_models import (
    AuditSummaryResponse,
    CandidateDetailCandidateResponse,
    CandidateDetailResponse,
    CandidateEvidenceResponse,
    ConversionIntentSummaryResponse,
    ConversionOutcomeSummaryResponse,
    FeedbackSummaryResponse,
    LifecycleHistoryResponse,
    RedactedSourceRefResponse,
    ReportEvidencePackSummaryResponse,
    ReviewDecisionSummaryResponse,
)
from app.api.problem_details import (
    invalid_request_metadata,
    not_found_metadata,
    permission_denied_metadata,
)
from app.api.route_metadata import RouteMetadata
from app.api.runtime_dependencies import (
    get_idea_repository,
    idea_repository_durable_storage_backed,
)
from app.application.candidate_detail import GetCandidateDetailCommand, get_candidate_detail
from app.api.problem_details import problem_details_response as problem_response
from app.observability import IdeaOperation, OperationOutcome, emit_foundation_operation_event
from app.security.caller_context import (
    CapabilityPolicy,
    PermissionDeniedError,
    require_role_and_capability,
)

__all__ = (
    "AuditSummaryResponse",
    "CandidateDetailCandidateResponse",
    "CandidateDetailResponse",
    "CandidateEvidenceResponse",
    "ConversionIntentSummaryResponse",
    "ConversionOutcomeSummaryResponse",
    "FeedbackSummaryResponse",
    "LifecycleHistoryResponse",
    "RedactedSourceRefResponse",
    "ReportEvidencePackSummaryResponse",
    "ReviewDecisionSummaryResponse",
    "get_idea_candidate_detail",
    "register_candidate_detail_routes",
)

_READ_CANDIDATE_DETAIL_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.candidate.detail.read",
    allowed_roles=("advisor", "operator"),
)


async def get_idea_candidate_detail(
    candidate_id: str = Path(..., alias="candidateId"),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
    x_caller_tenant_ids: str | None = Header(default=None, alias="X-Caller-Tenant-Ids"),
    x_caller_book_ids: str | None = Header(default=None, alias="X-Caller-Book-Ids"),
    x_caller_portfolio_ids: str | None = Header(default=None, alias="X-Caller-Portfolio-Ids"),
    x_caller_client_ids: str | None = Header(default=None, alias="X-Caller-Client-Ids"),
    x_lotus_trusted_caller_context: str | None = Header(
        default=None,
        alias=TRUSTED_CALLER_CONTEXT_HEADER,
    ),
) -> CandidateDetailResponse | JSONResponse:
    try:
        caller = caller_context_from_headers(
            subject=x_caller_subject,
            roles=x_caller_roles,
            capabilities=x_caller_capabilities,
            tenant_ids=x_caller_tenant_ids,
            book_ids=x_caller_book_ids,
            portfolio_ids=x_caller_portfolio_ids,
            client_ids=x_caller_client_ids,
            trusted_caller_context=x_lotus_trusted_caller_context,
        )
    except ValueError:
        _emit_candidate_detail_operation_event(
            OperationOutcome.INVALID_REQUEST,
            "invalid_request",
        )
        return problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail=INVALID_CALLER_SCOPE_DETAIL,
        )
    try:
        require_role_and_capability(caller, _READ_CANDIDATE_DETAIL_POLICY)
        result = get_candidate_detail(
            GetCandidateDetailCommand(
                candidate_id=candidate_id,
                access_scope_filter=caller_access_scope_filter(caller),
            ),
            repository=get_idea_repository(),
        )
    except PermissionDeniedError:
        _emit_candidate_detail_operation_event(
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return problem_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to read idea candidate detail.",
        )
    except ValueError:
        _emit_candidate_detail_operation_event(
            OperationOutcome.INVALID_REQUEST,
            "invalid_request",
        )
        return problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail="candidateId is required.",
        )

    if result.access_scope_denied:
        _emit_candidate_detail_operation_event(
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return problem_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to read idea candidate detail.",
        )

    if result.record is None:
        _emit_candidate_detail_operation_event(
            OperationOutcome.NOT_FOUND,
            "candidate_not_found",
        )
        return problem_response(
            status_code=status.HTTP_404_NOT_FOUND,
            code="candidate_not_found",
            title="Candidate not found",
            detail="The idea candidate was not found.",
        )

    durable_storage_backed = idea_repository_durable_storage_backed(get_idea_repository())
    _emit_candidate_detail_operation_event(
        OperationOutcome.ACCEPTED,
        durable_storage_backed=durable_storage_backed,
    )
    return CandidateDetailResponse.from_record(
        result.record,
        durable_storage_backed=durable_storage_backed,
    )


def _emit_candidate_detail_operation_event(
    outcome: OperationOutcome,
    error_code: str | None = None,
    durable_storage_backed: bool = False,
) -> None:
    emit_foundation_operation_event(
        IdeaOperation.CANDIDATE_DETAIL_READ,
        outcome,
        source_authority="lotus-idea",
        error_code=error_code,
        durable_storage_backed=durable_storage_backed,
    )


CANDIDATE_DETAIL_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-candidates/{candidateId}",
    "operation_id": "getIdeaCandidateDetail",
    "summary": "Get source-safe idea candidate detail",
    "description": (
        "Returns a source-safe internal detail projection for a persisted idea candidate, "
        "including redacted source evidence, lifecycle history, review, feedback, "
        "conversion, report-evidence, and audit summary posture. When platform "
        "caller-context scope headers are present, the route applies those entitlements "
        "fail-closed before returning detail. This is an RFC-0002 Slice 10 and Slice 11 "
        "API foundation for evidence-drawer use; it is not a Workbench product proof, "
        "data-product certification, or supported-feature promotion."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": CandidateDetailResponse,
    "tags": ["Idea Candidates"],
    "responses": {
        200: {
            "description": "Source-safe candidate detail returned.",
            "content": {
                "application/json": {
                    "example": {
                        "candidate": {
                            "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                            "family": "high_cash",
                            "lifecycleStatus": "converted_to_report",
                            "reviewPosture": "approved_for_conversion",
                            "evidencePacketId": "iep_high_cash_8d57adbf52f7f5a7",
                            "supportability": "ready",
                            "score": "82",
                            "scorePolicyVersion": "idle-liquidity-v1",
                            "sourceSignalIds": ["signal_high_cash_8d57adbf52f7f5a7"],
                            "reasonCodes": ["high_cash_ratio", "review_required"],
                            "unsupportedReasons": [],
                            "suppressionReason": None,
                            "createdAtUtc": "2026-06-21T10:00:00Z",
                            "updatedAtUtc": "2026-06-21T10:15:00Z",
                        },
                        "evidence": {
                            "evidencePacketId": "iep_high_cash_8d57adbf52f7f5a7",
                            "evidenceContentHash": "sha256:evidence-lineage",
                            "supportability": "ready",
                            "lineageId": "lineage_high_cash_8d57adbf52f7f5a7",
                            "createdAtUtc": "2026-06-21T10:00:00Z",
                            "sourceRefs": [
                                {
                                    "productId": "lotus-core:PortfolioStateSnapshot:v1",
                                    "sourceSystem": "lotus-core",
                                    "productVersion": "v1",
                                    "asOfDate": "2026-06-21",
                                    "generatedAtUtc": "2026-06-21T10:00:00Z",
                                    "dataQualityStatus": "complete",
                                    "freshness": "current",
                                }
                            ],
                        },
                        "lifecycleHistory": [],
                        "reviewDecisions": [],
                        "feedbackEvents": [],
                        "conversionIntents": [],
                        "conversionOutcomes": [],
                        "reportEvidencePacks": [],
                        "auditSummary": {
                            "eventCount": 1,
                            "latestEventType": "idea.candidate.persisted",
                            "latestEventOutcome": "accepted",
                            "latestOccurredAtUtc": "2026-06-21T10:00:00Z",
                        },
                        "durableStorageBacked": False,
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **invalid_request_metadata(
            detail="Correct the candidate detail request and retry.",
        ),
        **permission_denied_metadata(
            detail=(
                "The caller is not permitted to read this idea candidate detail or "
                "requested a candidate outside their entitlements."
            ),
            description=(
                "Caller lacks candidate detail permission or the candidate is outside "
                "caller entitlements."
            ),
        ),
        **not_found_metadata(
            code="candidate_not_found",
            title="Candidate not found",
            detail="No idea candidate exists for the requested candidateId.",
            description="Candidate was not found.",
        ),
    },
}


def register_candidate_detail_routes(app: FastAPI) -> None:
    app.get(
        path=CANDIDATE_DETAIL_ROUTE["path"],
        operation_id=CANDIDATE_DETAIL_ROUTE["operation_id"],
        summary=CANDIDATE_DETAIL_ROUTE["summary"],
        description=CANDIDATE_DETAIL_ROUTE["description"],
        status_code=CANDIDATE_DETAIL_ROUTE["status_code"],
        response_model=CANDIDATE_DETAIL_ROUTE["response_model"],
        tags=CANDIDATE_DETAIL_ROUTE["tags"],
        responses=CANDIDATE_DETAIL_ROUTE["responses"],
    )(get_idea_candidate_detail)
