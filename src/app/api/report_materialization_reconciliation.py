from __future__ import annotations

from typing import cast

from fastapi import FastAPI, Path, Request, status
from fastapi.responses import JSONResponse
from pydantic import Field

from app.api.base_model import CamelModel
from app.api.caller_headers import CallerContextHeaders, caller_access_scope_filter
from app.api.downstream_owner_receipt_models import DownstreamOwnerReceiptResponse
from app.api.durable_write_guard import (
    durable_repository_write_unavailable_metadata,
    durable_write_problem,
)
from app.api.problem_details import (
    conflict_metadata,
    not_found_metadata,
    permission_denied_metadata,
    problem_details_response,
    service_unavailable_metadata,
)
from app.api.realization_reconciliation_common import (
    emit_reconciliation_event,
    request_context_id,
    require_reconciliation_caller,
)
from app.api.route_metadata import RouteMetadata
from app.api.runtime_dependencies import (
    DownstreamRealizationClientsUnavailableError,
    get_idea_repository,
    get_report_evidence_pack_realization_client,
    get_trusted_clock,
    idea_repository_durable_storage_backed,
)
from app.application.report_materialization_reconciliation import (
    ReconcileReportMaterializationCommand,
    ReportMaterializationAccessScopeDenied,
    ReportMaterializationReconciliationResult,
    ReportMaterializationReconciliationStatus,
    reconcile_report_materialization_receipt,
)
from app.observability import OperationOutcome
from app.ports.downstream_realization import ReportEvidencePackMaterializationReader
from app.security.caller_context import PermissionDeniedError


class ReportMaterializationReconciliationResponse(CamelModel):
    reconciliation_status: ReportMaterializationReconciliationStatus = Field(
        alias="reconciliationStatus"
    )
    owner_receipt: DownstreamOwnerReceiptResponse = Field(alias="ownerReceipt")
    durable_storage_backed: bool = Field(alias="durableStorageBacked")
    grants_client_publication_authority: bool = Field(alias="grantsClientPublicationAuthority")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")


async def post_report_materialization_reconciliation(
    request: Request,
    caller: CallerContextHeaders,
    support_reference: str = Path(
        ...,
        alias="supportReference",
        pattern=r"^downstream-submission-[a-f0-9]{24}$",
    ),
) -> ReportMaterializationReconciliationResponse | JSONResponse:
    try:
        require_reconciliation_caller(caller)
    except PermissionDeniedError:
        emit_reconciliation_event(OperationOutcome.PERMISSION_DENIED, "permission_denied")
        return problem_details_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to recover Report materialization receipts.",
        )
    repository = get_idea_repository()
    configuration_problem = durable_write_problem(repository)
    if configuration_problem is not None:
        return configuration_problem
    access_scope_filter = caller_access_scope_filter(caller)
    assert access_scope_filter is not None
    try:
        report_reader = cast(
            ReportEvidencePackMaterializationReader,
            get_report_evidence_pack_realization_client(),
        )
    except DownstreamRealizationClientsUnavailableError:
        report_reader = None
    try:
        result = reconcile_report_materialization_receipt(
            ReconcileReportMaterializationCommand(
                support_reference=support_reference,
                actor_subject=caller.subject,
                access_scope_filter=access_scope_filter,
                accepted_at_utc=get_trusted_clock().now_utc(),
                correlation_id=request_context_id(request, "correlation_id"),
                trace_id=request_context_id(request, "trace_id"),
            ),
            repository=repository,
            report_reader=report_reader,
        )
    except ReportMaterializationAccessScopeDenied:
        emit_reconciliation_event(OperationOutcome.PERMISSION_DENIED, "permission_denied")
        return problem_details_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller scope does not cover this Report materialization.",
        )
    return _response(
        result,
        durable_storage_backed=idea_repository_durable_storage_backed(repository),
    )


def _response(
    result: ReportMaterializationReconciliationResult,
    *,
    durable_storage_backed: bool,
) -> ReportMaterializationReconciliationResponse | JSONResponse:
    if result.status is ReportMaterializationReconciliationStatus.NOT_FOUND:
        emit_reconciliation_event(OperationOutcome.NOT_FOUND, "downstream_submission_not_found")
        return problem_details_response(
            status_code=status.HTTP_404_NOT_FOUND,
            code="downstream_submission_not_found",
            title="Downstream submission not found",
            detail="No downstream submission matches the supplied support reference.",
        )
    if result.status in {
        ReportMaterializationReconciliationStatus.NOT_ELIGIBLE,
        ReportMaterializationReconciliationStatus.CONFLICT,
    }:
        emit_reconciliation_event(OperationOutcome.CONFLICT, result.blocker)
        return problem_details_response(
            status_code=status.HTTP_409_CONFLICT,
            code=result.blocker or "report_materialization_reconciliation_conflict",
            title="Report materialization reconciliation conflict",
            detail="The submission or recovered owner receipt failed exact validation.",
        )
    if result.status is ReportMaterializationReconciliationStatus.OWNER_UNAVAILABLE:
        emit_reconciliation_event(OperationOutcome.BLOCKED, result.blocker)
        return problem_details_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=result.blocker or "report_materialization_owner_unavailable",
            title="Report materialization owner unavailable",
            detail="The authoritative Report receipt could not be read; no evidence changed.",
        )
    assert result.owner_receipt is not None
    emit_reconciliation_event(
        OperationOutcome.REPLAYED
        if result.status is ReportMaterializationReconciliationStatus.REPLAYED
        else OperationOutcome.ACCEPTED,
        None,
    )
    return ReportMaterializationReconciliationResponse(
        reconciliationStatus=result.status,
        ownerReceipt=DownstreamOwnerReceiptResponse.from_domain(result.owner_receipt),
        durableStorageBacked=durable_storage_backed,
        grantsClientPublicationAuthority=result.grants_client_publication_authority,
        supportedFeaturePromoted=result.supported_feature_promoted,
    )


REPORT_MATERIALIZATION_RECONCILIATION_ROUTE: RouteMetadata = {
    "path": (
        "/api/v1/downstream-submissions/{supportReference}/report-materialization-reconciliation"
    ),
    "operation_id": "reconcileIdeaReportMaterializationReceipt",
    "summary": "Recover an uncertain Report materialization receipt",
    "description": (
        "Reads the exact trusted-scope Report materialization receipt for an uncertain "
        "Idea evidence-pack submission and finalizes the existing submission only after "
        "tenant, portfolio, candidate, conversion-intent, evidence and idempotency identity "
        "validation. It never repeats materialization POST and grants no client-publication "
        "or supported-feature authority."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": ReportMaterializationReconciliationResponse,
    "tags": ["Idea Downstream Realization"],
    "responses": {
        200: {
            "description": "Authoritative Report receipt accepted or exactly replayed.",
            "content": {
                "application/json": {
                    "example": {
                        "reconciliationStatus": "accepted",
                        "ownerReceipt": {
                            "ownerAuthority": "lotus-report",
                            "ownerRequestId": "report-request-001",
                            "ownerRealizationId": "report-job-001",
                            "ownerWorkId": None,
                            "sourceEventVersion": None,
                            "sourceEvidenceFingerprint": "sha256:idea-evidence-content",
                            "reportMaterialization": {
                                "status": "archived",
                                "materializationStatus": "archived",
                                "statusUrl": "/reports/jobs/report-job-001",
                                "reportEvidencePackId": "irep_001",
                                "conversionIntentId": "icnv_001",
                                "candidateId": "icand_001",
                                "evidencePacketId": "ievp_001",
                                "createsReportJob": True,
                                "createsRenderedOutput": True,
                                "createsArchiveRecord": True,
                                "renderJobId": "render-job-001",
                                "archiveDocumentId": "archive-document-001",
                                "supportabilityStatus": "not_certified",
                                "remainingBlockers": [
                                    "client_publication_authority_blocked",
                                    "supported_feature_promotion_missing",
                                ],
                            },
                        },
                        "durableStorageBacked": True,
                        "grantsClientPublicationAuthority": False,
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **permission_denied_metadata(
            detail="The caller cannot recover this Report materialization.",
            description="Caller capability or complete entitlement scope is missing.",
        ),
        **not_found_metadata(
            code="downstream_submission_not_found",
            title="Downstream submission not found",
            detail="No downstream submission matches the supplied support reference.",
            description="The source submission does not exist.",
        ),
        **conflict_metadata(
            code="report_materialization_reconciliation_conflict",
            title="Report materialization reconciliation conflict",
            detail="The submission or recovered owner receipt failed exact validation.",
            description="Scope, identity, posture or persistence conflict.",
        ),
        **service_unavailable_metadata(
            code="report_materialization_owner_unavailable",
            title="Report materialization owner unavailable",
            detail="The authoritative Report receipt could not be read; no evidence changed.",
            description="Report read configuration, availability or exact match prevented recovery.",
        ),
        **durable_repository_write_unavailable_metadata(),
    },
}


def register_report_materialization_reconciliation_routes(app: FastAPI) -> None:
    app.post(
        path=REPORT_MATERIALIZATION_RECONCILIATION_ROUTE["path"],
        operation_id=REPORT_MATERIALIZATION_RECONCILIATION_ROUTE["operation_id"],
        summary=REPORT_MATERIALIZATION_RECONCILIATION_ROUTE["summary"],
        description=REPORT_MATERIALIZATION_RECONCILIATION_ROUTE["description"],
        status_code=REPORT_MATERIALIZATION_RECONCILIATION_ROUTE["status_code"],
        response_model=REPORT_MATERIALIZATION_RECONCILIATION_ROUTE["response_model"],
        tags=REPORT_MATERIALIZATION_RECONCILIATION_ROUTE["tags"],
        responses=REPORT_MATERIALIZATION_RECONCILIATION_ROUTE["responses"],
    )(post_report_materialization_reconciliation)
