from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Mapping, TypedDict

from fastapi import FastAPI, Header, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api.caller_headers import caller_context_from_headers
from app.api.repository_state import get_idea_repository, idea_repository_durable_storage_backed
from app.application.outbox_delivery import OutboxDeliveryRunSummary, run_outbox_delivery_once
from app.application.outbox_delivery_readiness import (
    DEFAULT_OUTBOX_DELIVERY_MAX_RETRY_COUNT,
    OutboxDeliveryReadinessSnapshot,
    OutboxDeliveryStatusCounts,
    build_outbox_delivery_readiness_snapshot,
)
from app.errors import ProblemDetails, problem_response
from app.observability import (
    IdeaOperation,
    OperationEvent,
    OperationOutcome,
    OperationSupportability,
    emit_operation_event,
)
from app.outbox_publisher_state import (
    build_outbox_publisher_from_environment as _build_outbox_publisher_from_environment,
)
from app.security.caller_context import (
    CapabilityPolicy,
    CallerContext,
    PermissionDeniedError,
    require_role_and_capability,
)


class RouteMetadata(TypedDict):
    path: str
    operation_id: str
    summary: str
    description: str
    status_code: int
    response_model: type[BaseModel]
    tags: list[str | Enum]
    responses: dict[int | str, dict[str, Any]]


_READ_OUTBOX_DELIVERY_READINESS_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.outbox-delivery.readiness.read",
    allowed_roles=("operator",),
)
_RUN_OUTBOX_DELIVERY_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.outbox-delivery.run",
    allowed_roles=("operator",),
)


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class OutboxDeliveryStatusCountsResponse(CamelModel):
    pending_count: int = Field(..., alias="pendingCount")
    failed_count: int = Field(..., alias="failedCount")
    published_count: int = Field(..., alias="publishedCount")
    dead_letter_count: int = Field(..., alias="deadLetterCount")
    total_count: int = Field(..., alias="totalCount")

    @classmethod
    def from_domain(
        cls,
        counts: OutboxDeliveryStatusCounts,
    ) -> "OutboxDeliveryStatusCountsResponse":
        return cls(
            pendingCount=counts.pending_count,
            failedCount=counts.failed_count,
            publishedCount=counts.published_count,
            deadLetterCount=counts.dead_letter_count,
            totalCount=counts.total_count,
        )


class OutboxDeliveryReadinessResponse(CamelModel):
    repository: str
    readiness_status: str = Field(..., alias="readinessStatus")
    supportability_status: str = Field(..., alias="supportabilityStatus")
    certification_ready: bool = Field(..., alias="certificationReady")
    durable_storage_backed: bool = Field(..., alias="durableStorageBacked")
    external_broker_configured: bool = Field(..., alias="externalBrokerConfigured")
    external_broker_publisher_adapter_present: bool = Field(
        ..., alias="externalBrokerPublisherAdapterPresent"
    )
    delivery_ready_count: int = Field(..., alias="deliveryReadyCount")
    max_retry_count: int = Field(..., alias="maxRetryCount")
    status_counts: OutboxDeliveryStatusCountsResponse = Field(..., alias="statusCounts")
    source_of_truth: Mapping[str, str] = Field(..., alias="sourceOfTruth")
    configuration_blockers: tuple[str, ...] = Field(..., alias="configurationBlockers")
    certification_blockers: tuple[str, ...] = Field(..., alias="certificationBlockers")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")

    @classmethod
    def from_domain(
        cls,
        snapshot: OutboxDeliveryReadinessSnapshot,
    ) -> "OutboxDeliveryReadinessResponse":
        return cls(
            repository=snapshot.repository,
            readinessStatus=snapshot.readiness_status,
            supportabilityStatus=snapshot.supportability_status,
            certificationReady=snapshot.certification_ready,
            durableStorageBacked=snapshot.durable_storage_backed,
            externalBrokerConfigured=snapshot.external_broker_configured,
            externalBrokerPublisherAdapterPresent=(
                snapshot.external_broker_publisher_adapter_present
            ),
            deliveryReadyCount=snapshot.delivery_ready_count,
            maxRetryCount=snapshot.max_retry_count,
            statusCounts=OutboxDeliveryStatusCountsResponse.from_domain(snapshot.status_counts),
            sourceOfTruth=dict(snapshot.source_of_truth),
            configurationBlockers=snapshot.configuration_blockers,
            certificationBlockers=snapshot.certification_blockers,
            supportedFeaturePromoted=snapshot.supported_feature_promoted,
        )


class OutboxDeliveryRunOnceResponse(CamelModel):
    repository: str
    run_status: str = Field(..., alias="runStatus")
    supportability_status: str = Field(..., alias="supportabilityStatus")
    durable_storage_backed: bool = Field(..., alias="durableStorageBacked")
    external_broker_configured: bool = Field(..., alias="externalBrokerConfigured")
    attempted_count: int = Field(..., alias="attemptedCount")
    published_count: int = Field(..., alias="publishedCount")
    failed_count: int = Field(..., alias="failedCount")
    dead_lettered_count: int = Field(..., alias="deadLetteredCount")
    skipped_count: int = Field(..., alias="skippedCount")
    max_retry_count: int = Field(..., alias="maxRetryCount")
    certification_blockers: tuple[str, ...] = Field(..., alias="certificationBlockers")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")

    @classmethod
    def blocked(
        cls,
        *,
        durable_storage_backed: bool,
        blocker: str,
        max_retry_count: int,
    ) -> "OutboxDeliveryRunOnceResponse":
        return cls(
            repository="lotus-idea",
            runStatus="blocked",
            supportabilityStatus="not_certified",
            durableStorageBacked=durable_storage_backed,
            externalBrokerConfigured=False,
            attemptedCount=0,
            publishedCount=0,
            failedCount=0,
            deadLetteredCount=0,
            skippedCount=0,
            maxRetryCount=max_retry_count,
            certificationBlockers=(
                blocker,
                "external_broker_runtime_proof_missing",
                "downstream_consumer_contracts_missing",
                "platform_mesh_event_contract_missing",
                "gateway_workbench_proof_missing",
                "supported_feature_promotion_missing",
            ),
            supportedFeaturePromoted=False,
        )

    @classmethod
    def from_domain(
        cls,
        summary: OutboxDeliveryRunSummary,
        *,
        durable_storage_backed: bool,
    ) -> "OutboxDeliveryRunOnceResponse":
        return cls(
            repository="lotus-idea",
            runStatus="completed",
            supportabilityStatus="not_certified",
            durableStorageBacked=durable_storage_backed,
            externalBrokerConfigured=True,
            attemptedCount=summary.attempted_count,
            publishedCount=summary.published_count,
            failedCount=summary.failed_count,
            deadLetteredCount=summary.dead_lettered_count,
            skippedCount=summary.skipped_count,
            maxRetryCount=summary.max_retry_count,
            certificationBlockers=(
                "external_broker_runtime_proof_missing",
                "downstream_consumer_contracts_missing",
                "platform_mesh_event_contract_missing",
                "gateway_workbench_proof_missing",
                "supported_feature_promotion_missing",
            ),
            supportedFeaturePromoted=False,
        )


async def get_outbox_delivery_readiness(
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
) -> OutboxDeliveryReadinessResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
    )
    try:
        _require_outbox_delivery_readiness_caller(caller)
    except PermissionDeniedError:
        _emit_outbox_delivery_readiness_event(
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return problem_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to read idea outbox delivery readiness.",
        )

    repository = get_idea_repository()
    durable_storage_backed = idea_repository_durable_storage_backed(repository)
    snapshot = build_outbox_delivery_readiness_snapshot(
        repository=repository,
        durable_storage_backed=durable_storage_backed,
    )
    _emit_outbox_delivery_readiness_event(
        OperationOutcome.ACCEPTED if snapshot.certification_ready else OperationOutcome.BLOCKED,
        durable_storage_backed=durable_storage_backed,
    )
    return OutboxDeliveryReadinessResponse.from_domain(snapshot)


async def post_outbox_delivery_run_once(
    limit: int = Query(default=100, ge=1, le=1000),
    max_retry_count: int = Query(
        default=DEFAULT_OUTBOX_DELIVERY_MAX_RETRY_COUNT,
        alias="maxRetryCount",
        ge=1,
        le=10,
    ),
    delivered_at_utc: datetime | None = Query(default=None, alias="deliveredAtUtc"),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
) -> OutboxDeliveryRunOnceResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
    )
    try:
        require_role_and_capability(caller, _RUN_OUTBOX_DELIVERY_POLICY)
    except PermissionDeniedError:
        _emit_outbox_delivery_run_event(
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return problem_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to run idea outbox delivery.",
        )

    repository = get_idea_repository()
    durable_storage_backed = idea_repository_durable_storage_backed(repository)

    if delivered_at_utc is not None and (
        delivered_at_utc.tzinfo is None
        or delivered_at_utc.utcoffset() != UTC.utcoffset(delivered_at_utc)
    ):
        _emit_outbox_delivery_run_event(
            OperationOutcome.INVALID_REQUEST,
            "invalid_request",
            durable_storage_backed=durable_storage_backed,
        )
        return problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail="deliveredAtUtc must be UTC when provided.",
        )

    publisher_result = _build_outbox_publisher_from_environment()
    if isinstance(publisher_result, str):
        _emit_outbox_delivery_run_event(
            OperationOutcome.BLOCKED,
            publisher_result,
            durable_storage_backed=durable_storage_backed,
        )
        return OutboxDeliveryRunOnceResponse.blocked(
            durable_storage_backed=durable_storage_backed,
            blocker=publisher_result,
            max_retry_count=max_retry_count,
        )

    summary = run_outbox_delivery_once(
        repository,
        publisher_result,
        limit=limit,
        max_retry_count=max_retry_count,
        delivered_at_utc=delivered_at_utc,
    )
    _emit_outbox_delivery_run_event(
        OperationOutcome.ACCEPTED,
        durable_storage_backed=durable_storage_backed,
        attempted_count=summary.attempted_count,
    )
    return OutboxDeliveryRunOnceResponse.from_domain(
        summary,
        durable_storage_backed=durable_storage_backed,
    )


def _require_outbox_delivery_readiness_caller(caller: CallerContext) -> None:
    require_role_and_capability(caller, _READ_OUTBOX_DELIVERY_READINESS_POLICY)


def _emit_outbox_delivery_readiness_event(
    outcome: OperationOutcome,
    error_code: str | None = None,
    *,
    durable_storage_backed: bool = False,
) -> None:
    emit_operation_event(
        OperationEvent(
            operation=IdeaOperation.OUTBOX_DELIVERY_READINESS_READ,
            outcome=outcome,
            source_authority="lotus-idea",
            supportability_status=OperationSupportability.NOT_CERTIFIED,
            durable_storage_backed=durable_storage_backed,
            supported_feature_promoted=False,
            error_code=error_code,
        )
    )


def _emit_outbox_delivery_run_event(
    outcome: OperationOutcome,
    error_code: str | None = None,
    *,
    durable_storage_backed: bool = False,
    attempted_count: int | None = None,
) -> None:
    attributes: dict[str, str] = {}
    if attempted_count is not None:
        attributes["attempted_count_bucket"] = _count_bucket(attempted_count)
    emit_operation_event(
        OperationEvent(
            operation=IdeaOperation.OUTBOX_DELIVERY_RUN_ONCE,
            outcome=outcome,
            source_authority="lotus-idea",
            supportability_status=OperationSupportability.NOT_CERTIFIED,
            durable_storage_backed=durable_storage_backed,
            supported_feature_promoted=False,
            error_code=error_code,
            attributes=attributes,
        )
    )


def _count_bucket(value: int) -> str:
    if value == 0:
        return "0"
    if value <= 10:
        return "1-10"
    if value <= 100:
        return "11-100"
    return "100+"


OUTBOX_DELIVERY_READINESS_ROUTE: RouteMetadata = {
    "path": "/api/v1/outbox-delivery/readiness",
    "operation_id": "getIdeaOutboxDeliveryReadiness",
    "summary": "Get idea outbox delivery readiness",
    "description": (
        "Returns source-safe operator readiness for the internal outbox delivery foundation. "
        "The endpoint reports aggregate outbox status counts, delivery-ready count, durable "
        "repository posture, broker configuration posture, and explicit certification blockers. "
        "It does not publish events, expose event identifiers, certify live broker runtime, "
        "certify downstream delivery, create Gateway or Workbench support, or promote a "
        "supported feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": OutboxDeliveryReadinessResponse,
    "tags": ["Operations"],
    "responses": {
        200: {
            "description": "Outbox delivery readiness posture returned.",
            "content": {
                "application/json": {
                    "example": {
                        "repository": "lotus-idea",
                        "readinessStatus": "blocked",
                        "supportabilityStatus": "not_certified",
                        "certificationReady": False,
                        "durableStorageBacked": False,
                        "externalBrokerConfigured": False,
                        "externalBrokerPublisherAdapterPresent": True,
                        "deliveryReadyCount": 0,
                        "maxRetryCount": 3,
                        "statusCounts": {
                            "pendingCount": 0,
                            "failedCount": 0,
                            "publishedCount": 0,
                            "deadLetterCount": 0,
                            "totalCount": 0,
                        },
                        "sourceOfTruth": {
                            "outbox_delivery": "src/app/application/outbox_delivery.py",
                            "publisher_port": "src/app/ports/outbox_publisher.py",
                            "publisher_adapter": "src/app/infrastructure/outbox_publisher.py",
                            "repository_port": "src/app/ports/idea_repository.py",
                        },
                        "configurationBlockers": ["outbox_broker_not_configured"],
                        "certificationBlockers": [
                            "external_broker_runtime_proof_missing",
                            "downstream_consumer_contracts_missing",
                            "platform_mesh_event_contract_missing",
                        ],
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        403: {
            "model": ProblemDetails,
            "description": "Caller lacks outbox delivery readiness read permission.",
        },
    },
}


OUTBOX_DELIVERY_RUN_ONCE_ROUTE: RouteMetadata = {
    "path": "/api/v1/outbox-delivery/run-once",
    "operation_id": "runIdeaOutboxDeliveryOnce",
    "summary": "Run idea outbox delivery once",
    "description": (
        "Runs one bounded internal outbox delivery pass for operators. The endpoint uses the "
        "active repository provider and configured outbox publisher adapter, returns aggregate "
        "counts only, and remains not certified until live broker runtime, downstream consumer "
        "contracts, platform mesh event certification, Gateway/Workbench proof, and "
        "supported-feature promotion exist. If the broker is not configured or invalid, the "
        "endpoint fails closed without mutating pending outbox records."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": OutboxDeliveryRunOnceResponse,
    "tags": ["Operations"],
    "responses": {
        200: {
            "description": "Outbox delivery run-once summary returned.",
            "content": {
                "application/json": {
                    "example": {
                        "repository": "lotus-idea",
                        "runStatus": "blocked",
                        "supportabilityStatus": "not_certified",
                        "durableStorageBacked": False,
                        "externalBrokerConfigured": False,
                        "attemptedCount": 0,
                        "publishedCount": 0,
                        "failedCount": 0,
                        "deadLetteredCount": 0,
                        "skippedCount": 0,
                        "maxRetryCount": 3,
                        "certificationBlockers": [
                            "outbox_broker_not_configured",
                            "external_broker_runtime_proof_missing",
                            "downstream_consumer_contracts_missing",
                            "platform_mesh_event_contract_missing",
                            "gateway_workbench_proof_missing",
                            "supported_feature_promotion_missing",
                        ],
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        400: {"model": ProblemDetails, "description": "Request validation failed."},
        403: {
            "model": ProblemDetails,
            "description": "Caller lacks outbox delivery run permission.",
        },
    },
}


def register_outbox_delivery_readiness_routes(app: FastAPI) -> None:
    app.get(
        path=OUTBOX_DELIVERY_READINESS_ROUTE["path"],
        operation_id=OUTBOX_DELIVERY_READINESS_ROUTE["operation_id"],
        summary=OUTBOX_DELIVERY_READINESS_ROUTE["summary"],
        description=OUTBOX_DELIVERY_READINESS_ROUTE["description"],
        status_code=OUTBOX_DELIVERY_READINESS_ROUTE["status_code"],
        response_model=OUTBOX_DELIVERY_READINESS_ROUTE["response_model"],
        tags=OUTBOX_DELIVERY_READINESS_ROUTE["tags"],
        responses=OUTBOX_DELIVERY_READINESS_ROUTE["responses"],
    )(get_outbox_delivery_readiness)
    app.post(
        path=OUTBOX_DELIVERY_RUN_ONCE_ROUTE["path"],
        operation_id=OUTBOX_DELIVERY_RUN_ONCE_ROUTE["operation_id"],
        summary=OUTBOX_DELIVERY_RUN_ONCE_ROUTE["summary"],
        description=OUTBOX_DELIVERY_RUN_ONCE_ROUTE["description"],
        status_code=OUTBOX_DELIVERY_RUN_ONCE_ROUTE["status_code"],
        response_model=OUTBOX_DELIVERY_RUN_ONCE_ROUTE["response_model"],
        tags=OUTBOX_DELIVERY_RUN_ONCE_ROUTE["tags"],
        responses=OUTBOX_DELIVERY_RUN_ONCE_ROUTE["responses"],
    )(post_outbox_delivery_run_once)
