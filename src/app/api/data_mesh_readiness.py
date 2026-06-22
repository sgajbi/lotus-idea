from __future__ import annotations

from enum import Enum
import json
from typing import Any, Mapping, TypedDict

from fastapi import FastAPI, Header, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api.caller_headers import caller_context_from_headers
from app.application.data_mesh_readiness import (
    DataMeshProductReadiness,
    DataMeshReadinessSnapshot,
    build_data_mesh_readiness_snapshot,
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


_READ_MESH_READINESS_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.mesh.readiness.read",
    allowed_roles=("operator",),
)


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class DataMeshProductReadinessResponse(CamelModel):
    product_id: str = Field(..., alias="productId")
    lifecycle_status: str = Field(..., alias="lifecycleStatus")
    approved_consumers: tuple[str, ...] = Field(..., alias="approvedConsumers")

    @classmethod
    def from_domain(
        cls,
        product: DataMeshProductReadiness,
    ) -> "DataMeshProductReadinessResponse":
        return cls(
            productId=product.product_id,
            lifecycleStatus=product.lifecycle_status,
            approvedConsumers=product.approved_consumers,
        )


class DataMeshReadinessResponse(CamelModel):
    repository: str
    lifecycle_status: str = Field(..., alias="lifecycleStatus")
    certification_status: str = Field(..., alias="certificationStatus")
    mesh_role: str = Field(..., alias="meshRole")
    source_of_truth: Mapping[str, str] = Field(..., alias="sourceOfTruth")
    products: tuple[DataMeshProductReadinessResponse, ...]
    blockers: tuple[str, ...]
    certification_gates_before_promotion: tuple[str, ...] = Field(
        ..., alias="certificationGatesBeforePromotion"
    )
    runtime_telemetry_backed: bool = Field(..., alias="runtimeTelemetryBacked")
    platform_certified: bool = Field(..., alias="platformCertified")
    supported_feature_promoted: bool = Field(..., alias="supportedFeaturePromoted")

    @classmethod
    def from_domain(cls, snapshot: DataMeshReadinessSnapshot) -> "DataMeshReadinessResponse":
        return cls(
            repository=snapshot.repository,
            lifecycleStatus=snapshot.lifecycle_status,
            certificationStatus=snapshot.certification_status,
            meshRole=snapshot.mesh_role,
            sourceOfTruth=dict(snapshot.source_of_truth),
            products=tuple(
                DataMeshProductReadinessResponse.from_domain(product)
                for product in snapshot.products
            ),
            blockers=snapshot.blockers,
            certificationGatesBeforePromotion=snapshot.certification_gates_before_promotion,
            runtimeTelemetryBacked=snapshot.runtime_telemetry_backed,
            platformCertified=snapshot.platform_certified,
            supportedFeaturePromoted=snapshot.supported_feature_promoted,
        )


async def get_data_mesh_readiness(
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
) -> DataMeshReadinessResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
    )
    try:
        require_role_and_capability(caller, _READ_MESH_READINESS_POLICY)
    except PermissionDeniedError:
        _emit_data_mesh_readiness_event(
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return problem_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to read idea data-mesh readiness.",
        )

    try:
        snapshot = build_data_mesh_readiness_snapshot()
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        _emit_data_mesh_readiness_event(
            OperationOutcome.INVALID_STATE,
            "mesh_readiness_unavailable",
        )
        return problem_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="mesh_readiness_unavailable",
            title="Mesh readiness unavailable",
            detail="The service could not read its data-mesh readiness contracts.",
        )

    _emit_data_mesh_readiness_event(OperationOutcome.BLOCKED)
    return DataMeshReadinessResponse.from_domain(snapshot)


def _emit_data_mesh_readiness_event(
    outcome: OperationOutcome,
    error_code: str | None = None,
) -> None:
    emit_operation_event(
        OperationEvent(
            operation=IdeaOperation.MESH_READINESS_READ,
            outcome=outcome,
            source_authority="lotus-idea",
            supportability_status=OperationSupportability.NOT_CERTIFIED,
            durable_storage_backed=False,
            supported_feature_promoted=False,
            error_code=error_code,
        )
    )


DATA_MESH_READINESS_ROUTE: RouteMetadata = {
    "path": "/api/v1/data-mesh/readiness",
    "operation_id": "getIdeaDataMeshReadiness",
    "summary": "Get idea data-mesh readiness",
    "description": (
        "Returns the current repo-authored data-mesh readiness posture for lotus-idea. "
        "This operator-facing endpoint is read-only and explicitly reports planned, "
        "not-certified posture until runtime telemetry, platform source-manifest inclusion, "
        "Gateway/Workbench proof, and platform mesh certification exist."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": DataMeshReadinessResponse,
    "tags": ["Data Mesh"],
    "responses": {
        200: {
            "description": "Data-mesh readiness posture returned.",
            "content": {
                "application/json": {
                    "example": {
                        "repository": "lotus-idea",
                        "lifecycleStatus": "planned",
                        "certificationStatus": "not_certified",
                        "meshRole": "planned_producer_and_consumer",
                        "sourceOfTruth": {
                            "producer_declaration": (
                                "contracts/domain-data-products/lotus-idea-products.v1.json"
                            )
                        },
                        "products": [
                            {
                                "productId": "lotus-idea:IdeaCandidate:v1",
                                "lifecycleStatus": "proposed",
                                "approvedConsumers": ["lotus-gateway"],
                            }
                        ],
                        "blockers": [
                            "data_mesh_not_certified",
                            "producer_products_not_active",
                            "runtime_trust_telemetry_blocked",
                        ],
                        "certificationGatesBeforePromotion": [
                            "business capability implemented with source-owned evidence and endpoint certification"
                        ],
                        "runtimeTelemetryBacked": False,
                        "platformCertified": False,
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        403: {
            "model": ProblemDetails,
            "description": "Caller lacks data-mesh readiness read permission.",
        },
        503: {
            "model": ProblemDetails,
            "description": "Repo-authored data-mesh readiness contracts are unavailable.",
        },
    },
}


def register_data_mesh_readiness_routes(app: FastAPI) -> None:
    app.get(
        path=DATA_MESH_READINESS_ROUTE["path"],
        operation_id=DATA_MESH_READINESS_ROUTE["operation_id"],
        summary=DATA_MESH_READINESS_ROUTE["summary"],
        description=DATA_MESH_READINESS_ROUTE["description"],
        status_code=DATA_MESH_READINESS_ROUTE["status_code"],
        response_model=DATA_MESH_READINESS_ROUTE["response_model"],
        tags=DATA_MESH_READINESS_ROUTE["tags"],
        responses=DATA_MESH_READINESS_ROUTE["responses"],
    )(get_data_mesh_readiness)
