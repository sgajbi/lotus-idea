from __future__ import annotations

from fastapi import FastAPI, Header, Path, Response, status
from fastapi.responses import JSONResponse

from app.api.caller_headers import CallerContextHeaders, caller_access_scope_filter
from app.api.durable_write_guard import (
    durable_repository_write_unavailable_metadata,
    durable_write_problem,
)
from app.api.idempotency import validate_idempotency_key
from app.api.presentation_receipt_models import (
    PresentationReceiptRequest,
    PresentationReceiptResponse,
)
from app.api.problem_details import (
    conflict_metadata,
    invalid_request_metadata,
    merged_problem_response_metadata,
    not_found_metadata,
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
from app.application.candidate_detail import (
    GetCandidateDetailCommand,
    get_candidate_detail,
)
from app.domain import (
    PresentationReceiptCandidateStateError,
    PresentationReceiptDecision,
)
from app.observability import (
    IdeaOperation,
    OperationEvent,
    OperationOutcome,
    OperationSupportability,
    emit_operation_event,
)
from app.ports.idea_repository import PresentationReceiptRepository
from app.security.caller_context import (
    CapabilityPolicy,
    PermissionDeniedError,
    require_role_and_capability,
)


_RECORD_PRESENTATION_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.presentation-receipt.record",
    allowed_roles=("advisor", "operator"),
)


async def record_candidate_presentation_receipt(
    request: PresentationReceiptRequest,
    response: Response,
    caller: CallerContextHeaders,
    candidate_id: str = Path(..., alias="candidateId"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> PresentationReceiptResponse | JSONResponse:
    try:
        require_role_and_capability(caller, _RECORD_PRESENTATION_POLICY)
        validate_idempotency_key(idempotency_key)
        if request.tenant_id not in caller.entitlement_scope.tenant_ids:
            raise PermissionDeniedError(_RECORD_PRESENTATION_POLICY.required_capability)

        repository = get_idea_repository()
        configuration_problem = durable_write_problem(repository)
        if configuration_problem is not None:
            _emit_presentation_receipt_event(OperationOutcome.BLOCKED)
            return configuration_problem
        if not isinstance(repository, PresentationReceiptRepository):
            _emit_presentation_receipt_event(OperationOutcome.BLOCKED)
            return _unavailable_response()

        scope_filter = caller_access_scope_filter(caller)
        candidate_result = get_candidate_detail(
            GetCandidateDetailCommand(
                candidate_id=candidate_id,
                access_scope_filter=scope_filter,
            ),
            repository=repository,
        )
        if candidate_result.access_scope_denied:
            raise PermissionDeniedError(_RECORD_PRESENTATION_POLICY.required_capability)
        if candidate_result.record is None:
            _emit_presentation_receipt_event(OperationOutcome.NOT_FOUND)
            return _not_found_response()

        result = repository.record_presentation_receipt(
            request.to_domain(candidate_id=candidate_id, receipt_id=idempotency_key)
        )
    except PermissionDeniedError:
        _emit_presentation_receipt_event(OperationOutcome.PERMISSION_DENIED)
        return _permission_denied_response()
    except PresentationReceiptCandidateStateError:
        _emit_presentation_receipt_event(OperationOutcome.INVALID_STATE)
        return _candidate_state_conflict_response()
    except ValueError:
        _emit_presentation_receipt_event(OperationOutcome.INVALID_REQUEST)
        return _invalid_request_response()
    except (RuntimeError, TypeError):
        _emit_presentation_receipt_event(OperationOutcome.BLOCKED)
        return _unavailable_response()

    durable_storage_backed = idea_repository_durable_storage_backed(repository)
    if result.decision is PresentationReceiptDecision.CONFLICT:
        _emit_presentation_receipt_event(
            OperationOutcome.CONFLICT,
            durable_storage_backed=durable_storage_backed,
        )
        return _identity_conflict_response()
    if result.decision is PresentationReceiptDecision.REPLAYED:
        response.status_code = status.HTTP_200_OK
        outcome = OperationOutcome.REPLAYED
    else:
        outcome = OperationOutcome.ACCEPTED
    _emit_presentation_receipt_event(
        outcome,
        durable_storage_backed=durable_storage_backed,
        visible_candidate_count=request.visible_candidate_count,
    )
    return PresentationReceiptResponse.from_result(
        result,
        durable_storage_backed=durable_storage_backed,
    )


def _permission_denied_response() -> JSONResponse:
    return problem_details_response(
        status_code=status.HTTP_403_FORBIDDEN,
        code="permission_denied",
        title="Permission denied",
        detail="The caller is not permitted to record this candidate presentation receipt.",
    )


def _not_found_response() -> JSONResponse:
    return problem_details_response(
        status_code=status.HTTP_404_NOT_FOUND,
        code="candidate_not_found",
        title="Candidate not found",
        detail="The idea candidate was not found.",
    )


def _candidate_state_conflict_response() -> JSONResponse:
    return problem_details_response(
        status_code=status.HTTP_409_CONFLICT,
        code="presentation_receipt_candidate_state_conflict",
        title="Presentation receipt candidate state conflict",
        detail="The receipt does not match the current candidate tenant, version, or chronology.",
    )


def _identity_conflict_response() -> JSONResponse:
    return problem_details_response(
        status_code=status.HTTP_409_CONFLICT,
        code="presentation_receipt_identity_conflict",
        title="Presentation receipt identity conflict",
        detail="The Idempotency-Key was already used for different presentation evidence.",
    )


def _invalid_request_response() -> JSONResponse:
    return problem_details_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        code="invalid_request",
        title="Invalid request",
        detail="Correct the bounded presentation receipt fields and retry.",
    )


def _unavailable_response() -> JSONResponse:
    return problem_details_response(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        code="presentation_receipt_unavailable",
        title="Presentation receipt unavailable",
        detail="Governed presentation receipt persistence is unavailable.",
    )


def _emit_presentation_receipt_event(
    outcome: OperationOutcome,
    *,
    durable_storage_backed: bool = False,
    visible_candidate_count: int | None = None,
) -> None:
    attributes = (
        {"visible_candidate_count_bucket": bounded_count_bucket(visible_candidate_count)}
        if visible_candidate_count is not None
        else {}
    )
    emit_operation_event(
        OperationEvent(
            operation=IdeaOperation.PRESENTATION_RECEIPT_RECORD,
            outcome=outcome,
            source_authority="lotus-idea",
            supportability_status=OperationSupportability.NOT_CERTIFIED,
            durable_storage_backed=durable_storage_backed,
            supported_feature_promoted=False,
            attributes=attributes,
        )
    )


PRESENTATION_RECEIPT_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-candidates/{candidateId}/presentation-receipts",
    "operation_id": "recordIdeaCandidatePresentationReceipt",
    "summary": "Record governed candidate presentation evidence",
    "description": (
        "Records immutable, bounded evidence that a specific candidate version was visibly "
        "rendered in the governed advisor review queue. Idempotency-Key is the stable receipt "
        "identity. The write is fenced by candidate, exact tenant, material version, evidence "
        "version, and UTC chronology. Idea global rank and Workbench visible-set size remain "
        "independent facts. Queue retrieval is not presentation evidence. This route "
        "does not promote effectiveness certification until Gateway pass-through and Workbench "
        "visible-render production are independently certified on main."
    ),
    "status_code": status.HTTP_201_CREATED,
    "response_model": PresentationReceiptResponse,
    "tags": ["Idea Candidates"],
    "responses": {
        200: {"description": "An exact immutable receipt replay was accepted."},
        201: {
            "description": "The presentation receipt was durably recorded.",
            "content": {
                "application/json": {
                    "example": {
                        "receipt": {
                            "receiptId": "receipt-presentation-001",
                            "candidateId": "candidate-presentation-001",
                            "tenantId": "tenant-private-bank-sg",
                            "presentedAtUtc": "2026-08-30T12:00:00Z",
                            "rankAtPresentation": 25,
                            "visibleCandidateCount": 1,
                            "queueSnapshotDigest": f"sha256:{'a' * 64}",
                            "queuePolicyVersion": "idea-review-queue-v1",
                            "rankingPolicyVersion": "idea-score-v2",
                            "candidateMaterialVersion": 1,
                            "candidateEvidenceVersion": 1,
                            "schemaVersion": ("lotus-idea.candidate-presentation-receipt.v1"),
                            "surface": "advisor_review_queue",
                            "producer": "lotus-workbench",
                        },
                        "persistenceDecision": "accepted",
                        "durableStorageBacked": True,
                        "effectivenessMeasurementStatus": ("stored_consumer_certification_pending"),
                        "certificationStatus": "not_certified",
                        "certificationBlockers": [
                            "gateway_presentation_receipt_pass_through_not_certified",
                            "workbench_visible_render_producer_not_certified",
                        ],
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **invalid_request_metadata(
            detail="Correct the bounded receipt fields, UTC timestamp, or Idempotency-Key."
        ),
        **permission_denied_metadata(
            detail="The caller lacks the required role, capability, or tenant entitlement.",
            description="Caller cannot record presentation evidence for this candidate.",
        ),
        **not_found_metadata(
            code="candidate_not_found",
            title="Candidate not found",
            detail="No idea candidate exists for the requested candidateId.",
            description="Candidate was not found.",
        ),
        **merged_problem_response_metadata(
            status_code=status.HTTP_409_CONFLICT,
            description="Receipt identity or candidate state conflicts with governed evidence.",
            responses=(
                conflict_metadata(
                    code="presentation_receipt_identity_conflict",
                    title="Presentation receipt identity conflict",
                    detail=(
                        "The Idempotency-Key was already used for different presentation evidence."
                    ),
                    description="Receipt identity conflicts with immutable evidence.",
                ),
                conflict_metadata(
                    code="presentation_receipt_candidate_state_conflict",
                    title="Presentation receipt candidate state conflict",
                    detail=(
                        "The receipt does not match the current candidate tenant, version, "
                        "or chronology."
                    ),
                    description="Receipt does not match the current governed candidate state.",
                ),
            ),
        ),
        **merged_problem_response_metadata(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            description="Presentation receipt persistence is not write-ready.",
            responses=(
                durable_repository_write_unavailable_metadata(),
                service_unavailable_metadata(
                    code="presentation_receipt_unavailable",
                    title="Presentation receipt unavailable",
                    detail="Governed presentation receipt persistence is unavailable.",
                    description="Presentation receipt persistence failed closed.",
                ),
            ),
        ),
    },
}


def register_presentation_receipt_routes(app: FastAPI) -> None:
    app.post(
        path=PRESENTATION_RECEIPT_ROUTE["path"],
        operation_id=PRESENTATION_RECEIPT_ROUTE["operation_id"],
        summary=PRESENTATION_RECEIPT_ROUTE["summary"],
        description=PRESENTATION_RECEIPT_ROUTE["description"],
        status_code=PRESENTATION_RECEIPT_ROUTE["status_code"],
        response_model=PRESENTATION_RECEIPT_ROUTE["response_model"],
        tags=PRESENTATION_RECEIPT_ROUTE["tags"],
        responses=PRESENTATION_RECEIPT_ROUTE["responses"],
    )(record_candidate_presentation_receipt)


__all__ = ["PRESENTATION_RECEIPT_ROUTE", "register_presentation_receipt_routes"]
