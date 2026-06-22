from __future__ import annotations

from enum import Enum
from typing import Any, TypedDict

from fastapi import FastAPI, Header, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api.caller_headers import caller_context_from_headers
from app.application.source_ingestion_readiness import (
    SourceIngestionReadinessSnapshot,
    build_source_ingestion_readiness_snapshot,
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


_READ_SOURCE_INGESTION_READINESS_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.source-ingestion.readiness.read",
    allowed_roles=("operator",),
)


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class SourceIngestionReadinessResponse(CamelModel):
    repository: str
    source_authority: str = Field(..., alias="sourceAuthority")
    opportunity_family: str = Field(..., alias="opportunityFamily")
    manifest_schema_version: str = Field(..., alias="manifestSchemaVersion")
    example_manifest_path: str = Field(..., alias="exampleManifestPath")
    example_manifest_available: bool = Field(..., alias="exampleManifestAvailable")
    configured_manifest_available: bool = Field(..., alias="configuredManifestAvailable")
    core_base_url_configured: bool = Field(..., alias="coreBaseUrlConfigured")
    durable_repository_configured: bool = Field(..., alias="durableRepositoryConfigured")
    run_once_configuration_status: str = Field(..., alias="runOnceConfigurationStatus")
    run_once_configured: bool = Field(..., alias="runOnceConfigured")
    certification_status: str = Field(..., alias="certificationStatus")
    live_source_certified: bool = Field(..., alias="liveSourceCertified")
    configuration_blockers: tuple[str, ...] = Field(..., alias="configurationBlockers")
    certification_blockers: tuple[str, ...] = Field(..., alias="certificationBlockers")
    supported_feature_promoted: bool = Field(..., alias="supportedFeaturePromoted")

    @classmethod
    def from_domain(
        cls,
        snapshot: SourceIngestionReadinessSnapshot,
    ) -> "SourceIngestionReadinessResponse":
        return cls(
            repository=snapshot.repository,
            sourceAuthority=snapshot.source_authority,
            opportunityFamily=snapshot.opportunity_family,
            manifestSchemaVersion=snapshot.manifest_schema_version,
            exampleManifestPath=snapshot.example_manifest_path,
            exampleManifestAvailable=snapshot.example_manifest_available,
            configuredManifestAvailable=snapshot.configured_manifest_available,
            coreBaseUrlConfigured=snapshot.core_base_url_configured,
            durableRepositoryConfigured=snapshot.durable_repository_configured,
            runOnceConfigurationStatus=snapshot.run_once_configuration_status,
            runOnceConfigured=snapshot.run_once_configured,
            certificationStatus=snapshot.certification_status,
            liveSourceCertified=snapshot.live_source_certified,
            configurationBlockers=snapshot.configuration_blockers,
            certificationBlockers=snapshot.certification_blockers,
            supportedFeaturePromoted=snapshot.supported_feature_promoted,
        )


async def get_source_ingestion_readiness(
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
) -> SourceIngestionReadinessResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
    )
    try:
        require_role_and_capability(caller, _READ_SOURCE_INGESTION_READINESS_POLICY)
    except PermissionDeniedError:
        _emit_source_ingestion_readiness_event(
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return problem_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to read idea source-ingestion readiness.",
        )

    snapshot = build_source_ingestion_readiness_snapshot()
    _emit_source_ingestion_readiness_event(
        OperationOutcome.ACCEPTED if snapshot.run_once_configured else OperationOutcome.BLOCKED,
        durable_storage_backed=snapshot.durable_repository_configured,
    )
    return SourceIngestionReadinessResponse.from_domain(snapshot)


def _emit_source_ingestion_readiness_event(
    outcome: OperationOutcome,
    error_code: str | None = None,
    durable_storage_backed: bool = False,
) -> None:
    emit_operation_event(
        OperationEvent(
            operation=IdeaOperation.SOURCE_INGESTION_READINESS_READ,
            outcome=outcome,
            source_authority="lotus-core",
            supportability_status=OperationSupportability.NOT_CERTIFIED,
            durable_storage_backed=durable_storage_backed,
            supported_feature_promoted=False,
            error_code=error_code,
        )
    )


SOURCE_INGESTION_READINESS_ROUTE: RouteMetadata = {
    "path": "/api/v1/source-ingestion/readiness",
    "operation_id": "getIdeaSourceIngestionReadiness",
    "summary": "Get idea source-ingestion readiness",
    "description": (
        "Returns source-safe operator readiness for the internal high-cash Core source-ingestion "
        "worker. The endpoint reports configuration and certification blockers only; it does not "
        "call Core, expose source payloads, certify live source ingestion, create Gateway/Workbench "
        "support, or promote a supported feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": SourceIngestionReadinessResponse,
    "tags": ["Operations"],
    "responses": {
        200: {
            "description": "Source-ingestion readiness posture returned.",
            "content": {
                "application/json": {
                    "example": {
                        "repository": "lotus-idea",
                        "sourceAuthority": "lotus-core",
                        "opportunityFamily": "high_cash",
                        "manifestSchemaVersion": (
                            "lotus-idea.source-ingestion.high-cash.run-once.v1"
                        ),
                        "exampleManifestPath": (
                            "docs/examples/source-ingestion/high-cash-worker-manifest.example.json"
                        ),
                        "exampleManifestAvailable": True,
                        "configuredManifestAvailable": False,
                        "coreBaseUrlConfigured": False,
                        "durableRepositoryConfigured": False,
                        "runOnceConfigurationStatus": "blocked",
                        "runOnceConfigured": False,
                        "certificationStatus": "not_certified",
                        "liveSourceCertified": False,
                        "configurationBlockers": [
                            "source_ingestion_manifest_not_configured",
                            "lotus_core_base_url_not_configured",
                            "durable_repository_not_configured",
                        ],
                        "certificationBlockers": [
                            "live_core_source_proof_missing",
                            "scheduled_worker_deploy_proof_missing",
                            "data_mesh_runtime_telemetry_not_certified",
                            "gateway_workbench_proof_missing",
                        ],
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        403: {
            "model": ProblemDetails,
            "description": "Caller lacks source-ingestion readiness read permission.",
        },
    },
}


def register_source_ingestion_readiness_routes(app: FastAPI) -> None:
    app.get(
        path=SOURCE_INGESTION_READINESS_ROUTE["path"],
        operation_id=SOURCE_INGESTION_READINESS_ROUTE["operation_id"],
        summary=SOURCE_INGESTION_READINESS_ROUTE["summary"],
        description=SOURCE_INGESTION_READINESS_ROUTE["description"],
        status_code=SOURCE_INGESTION_READINESS_ROUTE["status_code"],
        response_model=SOURCE_INGESTION_READINESS_ROUTE["response_model"],
        tags=SOURCE_INGESTION_READINESS_ROUTE["tags"],
        responses=SOURCE_INGESTION_READINESS_ROUTE["responses"],
    )(get_source_ingestion_readiness)
