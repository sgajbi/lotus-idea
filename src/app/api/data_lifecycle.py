from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI, Header, Path, Request, status
from fastapi.responses import JSONResponse

from app.api.caller_headers import TRUSTED_CALLER_CONTEXT_HEADER, caller_context_from_headers
from app.api.data_lifecycle_models import (
    DataLifecycleActionRequest,
    DataLifecycleActionResponse,
)
from app.api.durable_write_guard import (
    durable_repository_write_unavailable_metadata,
    durable_write_problem,
)
from app.api.event_lineage import event_lineage_from_request
from app.api.idempotency import validate_idempotency_key
from app.api.operation_events import emit_api_foundation_operation_event as _emit_event
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
    get_lifecycle_authority_dependencies,
    get_idea_repository,
    idea_repository_durable_storage_backed,
    load_runtime_settings,
)
from app.application.lifecycle_authority_verification import (
    verify_lifecycle_authority_decision,
)
from app.application.data_lifecycle import ExecuteDataLifecycle
from app.domain.data_lifecycle import (
    DataLifecycleBlocker,
    DataLifecycleDecision,
    DataLifecycleOperationResult,
)
from app.domain.data_lifecycle.authority import (
    ExpectedLifecycleAuthorityDecision,
    VerifiedLifecycleAuthorityReceipt,
)
from app.observability import IdeaOperation, OperationOutcome
from app.ports.data_lifecycle import DataLifecycleRepository
from app.security.caller_context import (
    CapabilityPolicy,
    PermissionDeniedError,
    require_role_and_capability,
)

_MANAGE_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.data-lifecycle.manage",
    allowed_roles=("privacy_officer", "records_manager"),
)
_LIFECYCLE_AUTHORITY_UNAVAILABLE_DETAIL = "Signed lifecycle authority could not be verified."


async def post_data_lifecycle_action(
    request: DataLifecycleActionRequest,
    http_request: Request,
    candidate_id: str = Path(..., alias="candidateId", pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]+$"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
    x_caller_tenant_ids: str | None = Header(default=None, alias="X-Caller-Tenant-Ids"),
    x_lotus_trusted_caller_context: str | None = Header(
        default=None,
        alias=TRUSTED_CALLER_CONTEXT_HEADER,
    ),
) -> DataLifecycleActionResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
        tenant_ids=x_caller_tenant_ids,
        trusted_caller_context=x_lotus_trusted_caller_context,
    )
    try:
        require_role_and_capability(caller, _MANAGE_POLICY)
        if request.tenant_id not in caller.entitlement_scope.tenant_ids:
            raise PermissionDeniedError(_MANAGE_POLICY.required_capability)
    except PermissionDeniedError:
        _emit_event(IdeaOperation.DATA_LIFECYCLE_ACTION, OperationOutcome.PERMISSION_DENIED)
        return problem_details_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to manage this tenant's data lifecycle.",
        )
    try:
        validate_idempotency_key(idempotency_key)
        authority_required = (
            load_runtime_settings().runtime_profile.requires_durable_write_repository
        )
        authority_receipt = _verify_authority_decision(
            request=request,
            candidate_id=candidate_id,
            required=authority_required,
        )
        command = request.to_command(
            candidate_id=candidate_id,
            caller=caller,
            idempotency_key=idempotency_key,
            event_lineage=event_lineage_from_request(http_request),
            authority_verification_required=authority_required,
            authority_receipt=authority_receipt,
        )
    except RuntimeError:
        _emit_event(IdeaOperation.DATA_LIFECYCLE_ACTION, OperationOutcome.BLOCKED)
        return problem_details_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="lifecycle_authority_unavailable",
            title="Lifecycle authority unavailable",
            detail=_LIFECYCLE_AUTHORITY_UNAVAILABLE_DETAIL,
        )
    except ValueError:
        _emit_event(IdeaOperation.DATA_LIFECYCLE_ACTION, OperationOutcome.INVALID_REQUEST)
        return problem_details_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail="The lifecycle action or Idempotency-Key is invalid.",
        )
    repository = get_idea_repository()
    configuration_problem = durable_write_problem(repository)
    if configuration_problem is not None:
        return configuration_problem
    if not isinstance(repository, DataLifecycleRepository):
        return problem_details_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="data_lifecycle_repository_unavailable",
            title="Data lifecycle repository unavailable",
            detail="The durable repository does not expose governed data lifecycle operations.",
        )
    result = ExecuteDataLifecycle(repository).execute(command)
    return _action_response(
        result,
        request=request,
        durable_storage_backed=idea_repository_durable_storage_backed(repository),
    )


def _verify_authority_decision(
    *,
    request: DataLifecycleActionRequest,
    candidate_id: str,
    required: bool,
) -> VerifiedLifecycleAuthorityReceipt | None:
    if request.authority_decision is None:
        if required:
            raise ValueError("signed lifecycle authority decision is required")
        return None
    key_source, signature_verifier = get_lifecycle_authority_dependencies()
    return verify_lifecycle_authority_decision(
        envelope=request.authority_decision.to_domain(),
        key_discovery=key_source.get_key_discovery(),
        expected=ExpectedLifecycleAuthorityDecision(
            tenant_id=request.tenant_id,
            candidate_id=candidate_id,
            action=request.action,
            authority_ref=request.authority_ref,
            change_reference=request.change_reference,
            verified_at_utc=datetime.now(UTC),
        ),
        signature_verifier=signature_verifier,
    )


def _action_response(
    result: DataLifecycleOperationResult,
    *,
    request: DataLifecycleActionRequest,
    durable_storage_backed: bool,
) -> DataLifecycleActionResponse | JSONResponse:
    outcome_by_decision = {
        DataLifecycleDecision.APPLIED: OperationOutcome.ACCEPTED,
        DataLifecycleDecision.PREVIEW: OperationOutcome.ACCEPTED,
        DataLifecycleDecision.REPLAYED: OperationOutcome.REPLAYED,
        DataLifecycleDecision.BLOCKED: OperationOutcome.BLOCKED,
        DataLifecycleDecision.CONFLICT: OperationOutcome.CONFLICT,
        DataLifecycleDecision.NOT_FOUND: OperationOutcome.NOT_FOUND,
    }
    blocker = result.blockers[0].value if result.blockers else None
    _emit_event(
        IdeaOperation.DATA_LIFECYCLE_ACTION,
        outcome_by_decision[result.decision],
        blocker,
        durable_storage_backed=durable_storage_backed,
    )
    if result.decision is DataLifecycleDecision.NOT_FOUND:
        return problem_details_response(
            status_code=status.HTTP_404_NOT_FOUND,
            code="data_lifecycle_candidate_not_found",
            title="Candidate not found",
            detail="No tenant-scoped Idea candidate matches the supplied identifier.",
        )
    if result.decision is DataLifecycleDecision.CONFLICT:
        if DataLifecycleBlocker.AUTHORITY_ATTESTATION_REPLAY in result.blockers:
            return problem_details_response(
                status_code=status.HTTP_409_CONFLICT,
                code="lifecycle_authority_replay_conflict",
                title="Lifecycle authority replay conflict",
                detail="The signed lifecycle authority decision has already been applied.",
            )
        return problem_details_response(
            status_code=status.HTTP_409_CONFLICT,
            code="data_lifecycle_idempotency_conflict",
            title="Data lifecycle idempotency conflict",
            detail="The Idempotency-Key is already bound to a different lifecycle request.",
        )
    if result.decision is DataLifecycleDecision.BLOCKED:
        return problem_details_response(
            status_code=status.HTTP_409_CONFLICT,
            code="data_lifecycle_action_blocked",
            title="Data lifecycle action blocked",
            detail="The candidate remains unchanged pending authorized lifecycle prerequisites.",
        )
    return DataLifecycleActionResponse.from_domain(result, action=request.action)


DATA_LIFECYCLE_ACTION_ROUTE: RouteMetadata = {
    "path": "/api/v1/data-lifecycle/candidates/{candidateId}/actions",
    "operation_id": "applyIdeaCandidateDataLifecycleAction",
    "summary": "Apply a governed candidate data lifecycle action",
    "description": (
        "Previews or applies a tenant-scoped legal hold, hold release, erasure, or purge. "
        "The operation requires a durable repository, role plus capability, governed authority "
        "reference, idempotency, and dual approval where policy requires it. Production-like "
        "profiles also require a signed, request-bound lifecycle authority decision. Responses expose "
        "source-safe control evidence only and do not claim legal or privacy certification."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": DataLifecycleActionResponse,
    "tags": ["Operations"],
    "responses": {
        200: {
            "description": "Lifecycle action previewed, applied, or replayed.",
            "content": {
                "application/json": {
                    "example": {
                        "repository": "lotus-idea",
                        "operationId": "lifecycle-operation-0123456789abcdef01234567",
                        "decision": "preview",
                        "action": "erase",
                        "state": "erased",
                        "retentionExpiresAtUtc": "2033-07-11T09:00:00Z",
                        "controlVersion": 2,
                        "blockers": [],
                        "dryRun": True,
                        "auditSha256": "a" * 64,
                        "affectedRowCounts": {},
                        "certificationStatus": "not_certified",
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **invalid_request_metadata(
            detail="The lifecycle action or Idempotency-Key is invalid.",
            description="Lifecycle action validation failed.",
        ),
        **permission_denied_metadata(
            detail="The caller is not permitted to manage this tenant's data lifecycle.",
            description="Caller lacks the required role, capability, or tenant entitlement.",
        ),
        **not_found_metadata(
            code="data_lifecycle_candidate_not_found",
            title="Candidate not found",
            detail="No tenant-scoped Idea candidate matches the supplied identifier.",
            description="The candidate does not exist in the authorized tenant scope.",
        ),
        **merged_problem_response_metadata(
            status_code=status.HTTP_409_CONFLICT,
            description="The lifecycle action is blocked or conflicts with prior idempotency.",
            responses=(
                conflict_metadata(
                    code="data_lifecycle_action_blocked",
                    title="Data lifecycle action blocked",
                    detail=(
                        "The candidate remains unchanged pending authorized lifecycle prerequisites."
                    ),
                    description="A hold, active delivery, retention, or state prerequisite blocks action.",
                ),
                conflict_metadata(
                    code="data_lifecycle_idempotency_conflict",
                    title="Data lifecycle idempotency conflict",
                    detail=(
                        "The Idempotency-Key is already bound to a different lifecycle request."
                    ),
                    description="Idempotency-Key request fingerprint conflict.",
                ),
                conflict_metadata(
                    code="lifecycle_authority_replay_conflict",
                    title="Lifecycle authority replay conflict",
                    detail="The signed lifecycle authority decision has already been applied.",
                    description="Applied lifecycle authority decision or nonce reuse was rejected.",
                ),
            ),
        ),
        **merged_problem_response_metadata(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            description="Lifecycle authority or durable repository is unavailable.",
            responses=(
                durable_repository_write_unavailable_metadata(),
                service_unavailable_metadata(
                    code="lifecycle_authority_unavailable",
                    title="Lifecycle authority unavailable",
                    detail=_LIFECYCLE_AUTHORITY_UNAVAILABLE_DETAIL,
                    description="Signed lifecycle authority trust infrastructure is unavailable.",
                ),
            ),
        ),
    },
}


def register_data_lifecycle_routes(application: FastAPI) -> None:
    application.post(**DATA_LIFECYCLE_ACTION_ROUTE)(post_data_lifecycle_action)
