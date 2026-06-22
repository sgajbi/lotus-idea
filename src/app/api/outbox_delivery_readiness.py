from __future__ import annotations

from enum import Enum
from typing import Any, Mapping, TypedDict

from fastapi import FastAPI, Header, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api.caller_headers import caller_context_from_headers
from app.api.repository_state import get_idea_repository, idea_repository_durable_storage_backed
from app.application.outbox_delivery_readiness import (
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
            deliveryReadyCount=snapshot.delivery_ready_count,
            maxRetryCount=snapshot.max_retry_count,
            statusCounts=OutboxDeliveryStatusCountsResponse.from_domain(snapshot.status_counts),
            sourceOfTruth=dict(snapshot.source_of_truth),
            configurationBlockers=snapshot.configuration_blockers,
            certificationBlockers=snapshot.certification_blockers,
            supportedFeaturePromoted=snapshot.supported_feature_promoted,
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


OUTBOX_DELIVERY_READINESS_ROUTE: RouteMetadata = {
    "path": "/api/v1/outbox-delivery/readiness",
    "operation_id": "getIdeaOutboxDeliveryReadiness",
    "summary": "Get idea outbox delivery readiness",
    "description": (
        "Returns source-safe operator readiness for the internal outbox delivery foundation. "
        "The endpoint reports aggregate outbox status counts, delivery-ready count, durable "
        "repository posture, broker configuration posture, and explicit certification blockers. "
        "It does not publish events, expose event identifiers, call a broker, certify downstream "
        "delivery, create Gateway or Workbench support, or promote a supported feature."
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
                            "repository_port": "src/app/ports/idea_repository.py",
                        },
                        "configurationBlockers": ["outbox_broker_not_configured"],
                        "certificationBlockers": [
                            "external_broker_publisher_missing",
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
