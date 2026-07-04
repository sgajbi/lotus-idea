from __future__ import annotations

from fastapi import FastAPI, Header, status
from fastapi.responses import JSONResponse
from pydantic import Field

from app.api.base_model import CamelModel
from app.api.caller_headers import TRUSTED_CALLER_CONTEXT_HEADER, caller_context_from_headers
from app.api.problem_details import permission_denied_metadata
from app.api.route_metadata import RouteMetadata
from app.api.runtime_dependencies import (
    SourceIngestionRuntime,
    SourceIngestionRuntimeBlocker,
    get_idea_repository,
    idea_repository_durable_storage_backed,
)
from app.api.runtime_dependencies import (
    build_source_ingestion_runtime_from_environment as _build_source_ingestion_runtime_from_environment,
)
from app.api.telemetry_buckets import bounded_count_bucket
from app.application.source_ingestion import (
    HighCashSourceIngestionBatchResult,
    HighCashSourceIngestionDecision,
    run_high_cash_source_ingestion_batch,
)
from app.application.source_ingestion_readiness import (
    SourceIngestionReadinessSnapshot,
    build_source_ingestion_readiness_snapshot,
)
from app.api.problem_details import problem_details_response as problem_response
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

_READ_SOURCE_INGESTION_READINESS_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.source-ingestion.readiness.read",
    allowed_roles=("operator",),
)
_RUN_SOURCE_INGESTION_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.source-ingestion.run",
    allowed_roles=("operator",),
)


class SourceIngestionReadinessResponse(CamelModel):
    repository: str
    source_authority: str = Field(..., alias="sourceAuthority")
    opportunity_family: str = Field(..., alias="opportunityFamily")
    manifest_schema_version: str = Field(..., alias="manifestSchemaVersion")
    example_manifest_path: str = Field(..., alias="exampleManifestPath")
    example_manifest_available: bool = Field(..., alias="exampleManifestAvailable")
    configured_manifest_available: bool = Field(..., alias="configuredManifestAvailable")
    configured_live_proof_available: bool = Field(..., alias="configuredLiveProofAvailable")
    live_core_source_proof_valid: bool = Field(..., alias="liveCoreSourceProofValid")
    configured_scheduled_worker_proof_available: bool = Field(
        ..., alias="configuredScheduledWorkerProofAvailable"
    )
    scheduled_worker_deploy_proof_valid: bool = Field(..., alias="scheduledWorkerDeployProofValid")
    core_base_url_configured: bool = Field(..., alias="coreBaseUrlConfigured")
    core_query_base_url_configured: bool = Field(..., alias="coreQueryBaseUrlConfigured")
    core_query_control_plane_base_url_configured: bool = Field(
        ..., alias="coreQueryControlPlaneBaseUrlConfigured"
    )
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
            configuredLiveProofAvailable=snapshot.configured_live_proof_available,
            liveCoreSourceProofValid=snapshot.live_core_source_proof_valid,
            configuredScheduledWorkerProofAvailable=(
                snapshot.configured_scheduled_worker_proof_available
            ),
            scheduledWorkerDeployProofValid=snapshot.scheduled_worker_deploy_proof_valid,
            coreBaseUrlConfigured=snapshot.core_base_url_configured,
            coreQueryBaseUrlConfigured=snapshot.core_query_base_url_configured,
            coreQueryControlPlaneBaseUrlConfigured=(
                snapshot.core_query_control_plane_base_url_configured
            ),
            durableRepositoryConfigured=snapshot.durable_repository_configured,
            runOnceConfigurationStatus=snapshot.run_once_configuration_status,
            runOnceConfigured=snapshot.run_once_configured,
            certificationStatus=snapshot.certification_status,
            liveSourceCertified=snapshot.live_source_certified,
            configurationBlockers=snapshot.configuration_blockers,
            certificationBlockers=snapshot.certification_blockers,
            supportedFeaturePromoted=snapshot.supported_feature_promoted,
        )


class SourceIngestionRunOnceResponse(CamelModel):
    repository: str
    run_status: str = Field(..., alias="runStatus")
    supportability_status: str = Field(..., alias="supportabilityStatus")
    source_authority: str = Field(..., alias="sourceAuthority")
    opportunity_family: str = Field(..., alias="opportunityFamily")
    durable_storage_backed: bool = Field(..., alias="durableStorageBacked")
    configured_manifest_available: bool = Field(..., alias="configuredManifestAvailable")
    core_base_url_configured: bool = Field(..., alias="coreBaseUrlConfigured")
    core_query_base_url_configured: bool = Field(..., alias="coreQueryBaseUrlConfigured")
    core_query_control_plane_base_url_configured: bool = Field(
        ..., alias="coreQueryControlPlaneBaseUrlConfigured"
    )
    total_count: int = Field(..., alias="totalCount")
    decision_counts: dict[str, int] = Field(..., alias="decisionCounts")
    configuration_blockers: tuple[str, ...] = Field(..., alias="configurationBlockers")
    certification_blockers: tuple[str, ...] = Field(..., alias="certificationBlockers")
    live_source_certified: bool = Field(False, alias="liveSourceCertified")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")

    @classmethod
    def blocked(
        cls,
        *,
        blocker: str,
        durable_storage_backed: bool,
        configured_manifest_available: bool = False,
        core_base_url_configured: bool = False,
        core_query_base_url_configured: bool = False,
        core_query_control_plane_base_url_configured: bool = False,
    ) -> "SourceIngestionRunOnceResponse":
        return cls(
            repository="lotus-idea",
            runStatus="blocked",
            supportabilityStatus="not_certified",
            sourceAuthority="lotus-core",
            opportunityFamily="high_cash",
            durableStorageBacked=durable_storage_backed,
            configuredManifestAvailable=configured_manifest_available,
            coreBaseUrlConfigured=core_base_url_configured,
            coreQueryBaseUrlConfigured=core_query_base_url_configured,
            coreQueryControlPlaneBaseUrlConfigured=core_query_control_plane_base_url_configured,
            totalCount=0,
            decisionCounts=_empty_decision_counts(),
            configurationBlockers=(blocker,),
            certificationBlockers=_source_ingestion_certification_blockers(),
            liveSourceCertified=False,
            supportedFeaturePromoted=False,
        )

    @classmethod
    def from_domain(
        cls,
        result: HighCashSourceIngestionBatchResult,
        *,
        runtime: SourceIngestionRuntime,
        durable_storage_backed: bool,
    ) -> "SourceIngestionRunOnceResponse":
        return cls(
            repository="lotus-idea",
            runStatus="completed",
            supportabilityStatus="not_certified",
            sourceAuthority=result.source_authority,
            opportunityFamily="high_cash",
            durableStorageBacked=durable_storage_backed,
            configuredManifestAvailable=runtime.configured_manifest_available,
            coreBaseUrlConfigured=runtime.core_base_url_configured,
            coreQueryBaseUrlConfigured=runtime.core_query_base_url_configured,
            coreQueryControlPlaneBaseUrlConfigured=(
                runtime.core_query_control_plane_base_url_configured
            ),
            totalCount=result.total_count,
            decisionCounts=result.decision_counts(),
            configurationBlockers=(),
            certificationBlockers=_source_ingestion_certification_blockers(),
            liveSourceCertified=False,
            supportedFeaturePromoted=False,
        )


async def get_source_ingestion_readiness(
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
    x_lotus_trusted_caller_context: str | None = Header(
        default=None,
        alias=TRUSTED_CALLER_CONTEXT_HEADER,
    ),
) -> SourceIngestionReadinessResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
        trusted_caller_context=x_lotus_trusted_caller_context,
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


async def post_source_ingestion_run_once(
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
    x_lotus_trusted_caller_context: str | None = Header(
        default=None,
        alias=TRUSTED_CALLER_CONTEXT_HEADER,
    ),
) -> SourceIngestionRunOnceResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
        trusted_caller_context=x_lotus_trusted_caller_context,
    )
    try:
        require_role_and_capability(caller, _RUN_SOURCE_INGESTION_POLICY)
    except PermissionDeniedError:
        _emit_source_ingestion_run_event(
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return problem_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to run idea source ingestion.",
        )

    repository = get_idea_repository()
    durable_storage_backed = idea_repository_durable_storage_backed(repository)
    if not durable_storage_backed:
        _emit_source_ingestion_run_event(
            OperationOutcome.BLOCKED,
            "durable_repository_not_configured",
            durable_storage_backed=durable_storage_backed,
        )
        snapshot = build_source_ingestion_readiness_snapshot()
        return SourceIngestionRunOnceResponse.blocked(
            blocker="durable_repository_not_configured",
            durable_storage_backed=durable_storage_backed,
            configured_manifest_available=snapshot.configured_manifest_available,
            core_base_url_configured=snapshot.core_base_url_configured,
            core_query_base_url_configured=snapshot.core_query_base_url_configured,
            core_query_control_plane_base_url_configured=(
                snapshot.core_query_control_plane_base_url_configured
            ),
        )

    runtime = _build_source_ingestion_runtime_from_environment()
    if isinstance(runtime, SourceIngestionRuntimeBlocker):
        _emit_source_ingestion_run_event(
            OperationOutcome.BLOCKED,
            runtime.code,
            durable_storage_backed=durable_storage_backed,
        )
        return SourceIngestionRunOnceResponse.blocked(
            blocker=runtime.code,
            durable_storage_backed=durable_storage_backed,
            configured_manifest_available=runtime.configured_manifest_available,
            core_base_url_configured=runtime.core_base_url_configured,
            core_query_base_url_configured=runtime.core_query_base_url_configured,
            core_query_control_plane_base_url_configured=(
                runtime.core_query_control_plane_base_url_configured
            ),
        )

    try:
        result = run_high_cash_source_ingestion_batch(
            runtime.plan.command,
            core_source=runtime.core_source,
            repository=repository,
        )
        _emit_source_ingestion_run_event(
            _source_ingestion_operation_outcome(result),
            durable_storage_backed=durable_storage_backed,
            total_count=result.total_count,
        )
        return SourceIngestionRunOnceResponse.from_domain(
            result,
            runtime=runtime,
            durable_storage_backed=durable_storage_backed,
        )
    finally:
        runtime.close()


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


def _emit_source_ingestion_run_event(
    outcome: OperationOutcome,
    error_code: str | None = None,
    *,
    durable_storage_backed: bool = False,
    total_count: int | None = None,
) -> None:
    attributes: dict[str, str] = {}
    if total_count is not None:
        attributes["work_item_count_bucket"] = bounded_count_bucket(total_count)
    emit_operation_event(
        OperationEvent(
            operation=IdeaOperation.SOURCE_INGESTION_RUN_ONCE,
            outcome=outcome,
            source_authority="lotus-core",
            supportability_status=OperationSupportability.NOT_CERTIFIED,
            durable_storage_backed=durable_storage_backed,
            supported_feature_promoted=False,
            error_code=error_code,
            attributes=attributes,
        )
    )


def _source_ingestion_operation_outcome(
    result: HighCashSourceIngestionBatchResult,
) -> OperationOutcome:
    if result.total_count == 0:
        return OperationOutcome.BLOCKED
    if result.count(HighCashSourceIngestionDecision.BLOCKED) == result.total_count:
        return OperationOutcome.BLOCKED
    return OperationOutcome.ACCEPTED


def _empty_decision_counts() -> dict[str, int]:
    return {decision.value: 0 for decision in HighCashSourceIngestionDecision}


def _source_ingestion_certification_blockers() -> tuple[str, ...]:
    snapshot = build_source_ingestion_readiness_snapshot()
    return (*snapshot.certification_blockers, "supported_feature_promotion_missing")


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
                        "configuredLiveProofAvailable": False,
                        "liveCoreSourceProofValid": False,
                        "configuredScheduledWorkerProofAvailable": False,
                        "scheduledWorkerDeployProofValid": False,
                        "coreBaseUrlConfigured": False,
                        "coreQueryBaseUrlConfigured": False,
                        "coreQueryControlPlaneBaseUrlConfigured": False,
                        "durableRepositoryConfigured": False,
                        "runOnceConfigurationStatus": "blocked",
                        "runOnceConfigured": False,
                        "certificationStatus": "not_certified",
                        "liveSourceCertified": False,
                        "configurationBlockers": [
                            "source_ingestion_manifest_not_configured",
                            "lotus_core_query_base_url_not_configured",
                            "lotus_core_query_control_plane_base_url_not_configured",
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
        **permission_denied_metadata(
            detail="The caller is not permitted to read source-ingestion readiness.",
            description="Caller lacks source-ingestion readiness read permission.",
        ),
    },
}


SOURCE_INGESTION_RUN_ONCE_ROUTE: RouteMetadata = {
    "path": "/api/v1/source-ingestion/run-once",
    "operation_id": "runIdeaSourceIngestionOnce",
    "summary": "Run idea source ingestion once",
    "description": (
        "Runs one bounded internal high-cash Core source-ingestion pass for operators using the "
        "configured worker manifest, active repository provider, and Core source adapter. The "
        "endpoint returns aggregate counts only, requires durable repository configuration, and "
        "remains not certified until live Core source proof, scheduled worker deployment proof, "
        "data-mesh runtime telemetry certification, Gateway/Workbench proof, and "
        "supported-feature promotion exist."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": SourceIngestionRunOnceResponse,
    "tags": ["Operations"],
    "responses": {
        200: {
            "description": "Source-ingestion run-once summary returned.",
            "content": {
                "application/json": {
                    "example": {
                        "repository": "lotus-idea",
                        "runStatus": "blocked",
                        "supportabilityStatus": "not_certified",
                        "sourceAuthority": "lotus-core",
                        "opportunityFamily": "high_cash",
                        "durableStorageBacked": False,
                        "configuredManifestAvailable": False,
                        "coreBaseUrlConfigured": False,
                        "coreQueryBaseUrlConfigured": False,
                        "coreQueryControlPlaneBaseUrlConfigured": False,
                        "totalCount": 0,
                        "decisionCounts": {
                            "accepted": 0,
                            "replayed": 0,
                            "conflict": 0,
                            "duplicate_candidate": 0,
                            "skipped_not_eligible": 0,
                            "blocked": 0,
                            "suppressed": 0,
                        },
                        "configurationBlockers": ["durable_repository_not_configured"],
                        "certificationBlockers": [
                            "live_core_source_proof_missing",
                            "scheduled_worker_deploy_proof_missing",
                            "data_mesh_runtime_telemetry_not_certified",
                            "gateway_workbench_proof_missing",
                            "supported_feature_promotion_missing",
                        ],
                        "liveSourceCertified": False,
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **permission_denied_metadata(
            detail="The caller is not permitted to run source ingestion.",
            description="Caller lacks source-ingestion run permission.",
        ),
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
    app.post(
        path=SOURCE_INGESTION_RUN_ONCE_ROUTE["path"],
        operation_id=SOURCE_INGESTION_RUN_ONCE_ROUTE["operation_id"],
        summary=SOURCE_INGESTION_RUN_ONCE_ROUTE["summary"],
        description=SOURCE_INGESTION_RUN_ONCE_ROUTE["description"],
        status_code=SOURCE_INGESTION_RUN_ONCE_ROUTE["status_code"],
        response_model=SOURCE_INGESTION_RUN_ONCE_ROUTE["response_model"],
        tags=SOURCE_INGESTION_RUN_ONCE_ROUTE["tags"],
        responses=SOURCE_INGESTION_RUN_ONCE_ROUTE["responses"],
    )(post_source_ingestion_run_once)
