from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Header, Path, Query, status
from fastapi.responses import JSONResponse

from app.api.caller_headers import TRUSTED_CALLER_CONTEXT_HEADER, caller_context_from_headers
from app.api.durable_write_guard import durable_write_problem
from app.api.idempotency import IDEMPOTENCY_KEY_REQUIRED_MESSAGE, validate_idempotency_key
from app.api.outbox_recovery_models import (
    OutboxDeadLetterListResponse,
    OutboxDeadLetterSummaryResponse,
    OutboxRecoveryRequest,
    OutboxRecoveryResponse,
)
from app.api.problem_details import (
    conflict_metadata,
    not_found_metadata,
    permission_denied_metadata,
    problem_details_response,
)
from app.api.route_metadata import RouteMetadata
from app.api.runtime_dependencies import (
    build_outbox_publisher_from_environment,
    get_idea_repository,
    idea_repository_durable_storage_backed,
)
from app.application.outbox_recovery import (
    OutboxRecoveryRunSummary,
    OutboxRecoveryRunStatus,
    run_outbox_dead_letter_recovery,
)
from app.observability import (
    IdeaOperation,
    OperationEvent,
    OperationOutcome,
    OperationSupportability,
    emit_operation_event,
)
from app.security.caller_context import CapabilityPolicy, PermissionDeniedError, require_role_and_capability


_READ_DEAD_LETTER_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.outbox-recovery.read",
    allowed_roles=("operator",),
)
_REDRIVE_DEAD_LETTER_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.outbox-recovery.redrive",
    allowed_roles=("operator",),
)


async def get_outbox_dead_letters(
    limit: int = Query(default=100, ge=1, le=100),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
    x_lotus_trusted_caller_context: str | None = Header(
        default=None,
        alias=TRUSTED_CALLER_CONTEXT_HEADER,
    ),
) -> OutboxDeadLetterListResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
        trusted_caller_context=x_lotus_trusted_caller_context,
    )
    try:
        require_role_and_capability(caller, _READ_DEAD_LETTER_POLICY)
    except PermissionDeniedError:
        _emit_recovery_event(IdeaOperation.OUTBOX_DEAD_LETTER_READ, OperationOutcome.PERMISSION_DENIED)
        return problem_details_response(**_permission_denied_args("inspect"))
    repository = get_idea_repository()
    summaries = repository.dead_letter_summaries(limit=limit)
    _emit_recovery_event(
        IdeaOperation.OUTBOX_DEAD_LETTER_READ,
        OperationOutcome.ACCEPTED,
        durable_storage_backed=idea_repository_durable_storage_backed(repository),
    )
    items = tuple(OutboxDeadLetterSummaryResponse.from_domain(item) for item in summaries)
    return OutboxDeadLetterListResponse(
        repository="lotus-idea",
        supportabilityStatus="not_certified",
        items=items,
        returnedCount=len(items),
        supportedFeaturePromoted=False,
    )


async def post_outbox_dead_letter_redrive(
    request: OutboxRecoveryRequest,
    support_reference: str = Path(
        ...,
        alias="supportReference",
        min_length=12,
        max_length=64,
        pattern=r"^outbox-dlq-[a-f0-9]{24}$",
    ),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
    x_lotus_trusted_caller_context: str | None = Header(
        default=None,
        alias=TRUSTED_CALLER_CONTEXT_HEADER,
    ),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> OutboxRecoveryResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
        trusted_caller_context=x_lotus_trusted_caller_context,
    )
    try:
        require_role_and_capability(caller, _REDRIVE_DEAD_LETTER_POLICY)
    except PermissionDeniedError:
        _emit_recovery_event(IdeaOperation.OUTBOX_DEAD_LETTER_REDRIVE, OperationOutcome.PERMISSION_DENIED)
        return problem_details_response(**_permission_denied_args("re-drive"))
    validated_idempotency_key = idempotency_key or ""
    try:
        validate_idempotency_key(validated_idempotency_key)
    except ValueError:
        _emit_recovery_event(IdeaOperation.OUTBOX_DEAD_LETTER_REDRIVE, OperationOutcome.INVALID_REQUEST)
        return problem_details_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail=IDEMPOTENCY_KEY_REQUIRED_MESSAGE,
        )
    repository = get_idea_repository()
    configuration_problem = durable_write_problem(repository)
    if configuration_problem is not None:
        return configuration_problem
    publisher = build_outbox_publisher_from_environment()
    if isinstance(publisher, str):
        _emit_recovery_event(
            IdeaOperation.OUTBOX_DEAD_LETTER_REDRIVE,
            OperationOutcome.BLOCKED,
            publisher,
            durable_storage_backed=idea_repository_durable_storage_backed(repository),
        )
        return problem_details_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code=publisher,
            title="Outbox recovery unavailable",
            detail="A governed outbox publisher must be configured before re-drive.",
        )
    try:
        summary = run_outbox_dead_letter_recovery(
            repository,
            publisher,
            support_reference=support_reference,
            idempotency_key=validated_idempotency_key,
            reason=request.reason,
            change_reference=request.change_reference,
            actor_subject=caller.subject,
        )
    finally:
        close = getattr(publisher, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                _emit_recovery_event(
                    IdeaOperation.OUTBOX_DEAD_LETTER_REDRIVE,
                    OperationOutcome.SUPPRESSED,
                    "publisher_cleanup_failed",
                    durable_storage_backed=idea_repository_durable_storage_backed(repository),
                )
    return _recovery_response(summary, idea_repository_durable_storage_backed(repository))


def _recovery_response(
    summary: OutboxRecoveryRunSummary,
    durable_storage_backed: bool,
) -> OutboxRecoveryResponse | JSONResponse:
    outcome_by_status = {
        OutboxRecoveryRunStatus.PUBLISHED: OperationOutcome.ACCEPTED,
        OutboxRecoveryRunStatus.REPLAYED: OperationOutcome.REPLAYED,
        OutboxRecoveryRunStatus.CONFLICT: OperationOutcome.CONFLICT,
        OutboxRecoveryRunStatus.NOT_FOUND: OperationOutcome.NOT_FOUND,
        OutboxRecoveryRunStatus.QUARANTINED: OperationOutcome.NOT_ELIGIBLE,
        OutboxRecoveryRunStatus.DEAD_LETTERED: OperationOutcome.BLOCKED,
        OutboxRecoveryRunStatus.LEASE_LOST: OperationOutcome.CONFLICT,
    }
    _emit_recovery_event(
        IdeaOperation.OUTBOX_DEAD_LETTER_REDRIVE,
        outcome_by_status[summary.run_status],
        summary.blocker,
        durable_storage_backed=durable_storage_backed,
    )
    if summary.run_status is OutboxRecoveryRunStatus.CONFLICT:
        return problem_details_response(
            status_code=status.HTTP_409_CONFLICT,
            code="idempotency_conflict",
            title="Idempotency conflict",
            detail="The idempotency key was already used for a different recovery request.",
        )
    if summary.run_status is OutboxRecoveryRunStatus.NOT_FOUND:
        return problem_details_response(
            status_code=status.HTTP_404_NOT_FOUND,
            code="dead_letter_not_found",
            title="Dead letter not found",
            detail="No outbox dead letter matches the supplied support reference.",
        )
    if summary.run_status in {OutboxRecoveryRunStatus.QUARANTINED, OutboxRecoveryRunStatus.LEASE_LOST}:
        return problem_details_response(
            status_code=status.HTTP_409_CONFLICT,
            code=summary.blocker or "recovery_not_eligible",
            title="Outbox recovery not eligible",
            detail="The event remains quarantined for Lotus Idea operations review.",
        )
    return OutboxRecoveryResponse.from_domain(summary)


def _permission_denied_args(action: str) -> dict[str, Any]:
    return {
        "status_code": status.HTTP_403_FORBIDDEN,
        "code": "permission_denied",
        "title": "Permission denied",
        "detail": f"The caller is not permitted to {action} Idea outbox dead letters.",
    }


def _emit_recovery_event(
    operation: IdeaOperation,
    outcome: OperationOutcome,
    error_code: str | None = None,
    *,
    durable_storage_backed: bool = False,
) -> None:
    emit_operation_event(
        OperationEvent(
            operation=operation,
            outcome=outcome,
            supportability_status=OperationSupportability.NOT_CERTIFIED,
            durable_storage_backed=durable_storage_backed,
            supported_feature_promoted=False,
            error_code=error_code,
        )
    )


OUTBOX_DEAD_LETTER_LIST_ROUTE: RouteMetadata = {
    "path": "/api/v1/outbox-delivery/dead-letters",
    "operation_id": "listIdeaOutboxDeadLetters",
    "summary": "List quarantined idea outbox dead letters",
    "description": (
        "Returns a bounded, operator-only projection of quarantined local outbox events. "
        "Responses include opaque support references and bounded failure posture only; payloads, "
        "aggregate identifiers, client or portfolio identifiers, and idempotency material are omitted."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": OutboxDeadLetterListResponse,
    "tags": ["Operations"],
    "responses": permission_denied_metadata(
        detail="The caller is not permitted to inspect Idea outbox dead letters.",
        description="Caller lacks dead-letter inspection permission.",
    ),
}

OUTBOX_DEAD_LETTER_REDRIVE_ROUTE: RouteMetadata = {
    "path": "/api/v1/outbox-delivery/dead-letters/{supportReference}/redrive",
    "operation_id": "redriveIdeaOutboxDeadLetter",
    "summary": "Re-drive one quarantined idea outbox event",
    "description": (
        "Performs one explicit, idempotent operator re-drive after event-family and schema "
        "eligibility checks. The operation records actor, reason, change reference, original "
        "failure history, and a new fenced lease before publication. Rejected or exhausted "
        "events remain quarantined; no automatic infinite retry is introduced."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": OutboxRecoveryResponse,
    "tags": ["Operations"],
    "responses": {
        **permission_denied_metadata(
            detail="The caller is not permitted to re-drive Idea outbox dead letters.",
            description="Caller lacks dead-letter re-drive permission.",
        ),
        **not_found_metadata(
            code="dead_letter_not_found",
            title="Dead letter not found",
            detail="No outbox dead letter matches the supplied support reference.",
            description="The opaque support reference does not identify a recoverable record.",
        ),
        **conflict_metadata(
            code="recovery_not_eligible",
            title="Outbox recovery not eligible",
            detail="The event remains quarantined for Lotus Idea operations review.",
            description="Recovery conflicts with idempotency, lease, eligibility, or poison safeguards.",
        ),
    },
}


def register_outbox_recovery_routes(app: FastAPI) -> None:
    app.get(**OUTBOX_DEAD_LETTER_LIST_ROUTE)(get_outbox_dead_letters)
    app.post(**OUTBOX_DEAD_LETTER_REDRIVE_ROUTE)(post_outbox_dead_letter_redrive)
