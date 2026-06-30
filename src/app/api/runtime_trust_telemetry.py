from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from fastapi import FastAPI, Header, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api.caller_headers import caller_context_from_headers
from app.api.route_metadata import RouteMetadata
from app.api.runtime_dependencies import (
    get_idea_repository,
    idea_repository_durable_storage_backed,
)
from app.application.runtime_trust_telemetry import (
    RuntimeTrustTelemetryPreview,
    build_runtime_trust_telemetry_preview,
    build_runtime_trust_telemetry_snapshot,
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

_READ_RUNTIME_TRUST_TELEMETRY_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.mesh.trust-telemetry.preview.read",
    allowed_roles=("operator",),
)
_READ_RUNTIME_TRUST_TELEMETRY_SNAPSHOT_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.mesh.trust-telemetry.snapshot.read",
    allowed_roles=("operator",),
)


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class RuntimeTrustTelemetryPreviewResponse(CamelModel):
    repository: str
    product_id: str = Field(..., alias="productId")
    generated_at_utc: datetime = Field(..., alias="generatedAtUtc")
    candidate_snapshot_count: int = Field(..., alias="candidateSnapshotCount")
    current_source_ref_count: int = Field(..., alias="currentSourceRefCount")
    stale_or_unavailable_source_ref_count: int = Field(
        ...,
        alias="staleOrUnavailableSourceRefCount",
    )
    source_authority_counts: Mapping[str, int] = Field(..., alias="sourceAuthorityCounts")
    freshness_counts: Mapping[str, int] = Field(..., alias="freshnessCounts")
    supportability_counts: Mapping[str, int] = Field(..., alias="supportabilityCounts")
    lifecycle_counts: Mapping[str, int] = Field(..., alias="lifecycleCounts")
    review_decision_count: int = Field(..., alias="reviewDecisionCount")
    feedback_event_count: int = Field(..., alias="feedbackEventCount")
    conversion_intent_count: int = Field(..., alias="conversionIntentCount")
    conversion_outcome_count: int = Field(..., alias="conversionOutcomeCount")
    report_evidence_pack_count: int = Field(..., alias="reportEvidencePackCount")
    lineage_materialized: bool = Field(..., alias="lineageMaterialized")
    runtime_telemetry_backed: bool = Field(..., alias="runtimeTelemetryBacked")
    platform_certified: bool = Field(..., alias="platformCertified")
    certification_status: str = Field(..., alias="certificationStatus")
    certification_ready: bool = Field(..., alias="certificationReady")
    certification_blockers: tuple[str, ...] = Field(..., alias="certificationBlockers")
    supported_feature_promoted: bool = Field(..., alias="supportedFeaturePromoted")

    @classmethod
    def from_domain(
        cls,
        snapshot: RuntimeTrustTelemetryPreview,
    ) -> "RuntimeTrustTelemetryPreviewResponse":
        return cls(
            repository=snapshot.repository,
            productId=snapshot.product_id,
            generatedAtUtc=snapshot.generated_at_utc,
            candidateSnapshotCount=snapshot.candidate_snapshot_count,
            currentSourceRefCount=snapshot.current_source_ref_count,
            staleOrUnavailableSourceRefCount=snapshot.stale_or_unavailable_source_ref_count,
            sourceAuthorityCounts=dict(snapshot.source_authority_counts),
            freshnessCounts=dict(snapshot.freshness_counts),
            supportabilityCounts=dict(snapshot.supportability_counts),
            lifecycleCounts=dict(snapshot.lifecycle_counts),
            reviewDecisionCount=snapshot.review_decision_count,
            feedbackEventCount=snapshot.feedback_event_count,
            conversionIntentCount=snapshot.conversion_intent_count,
            conversionOutcomeCount=snapshot.conversion_outcome_count,
            reportEvidencePackCount=snapshot.report_evidence_pack_count,
            lineageMaterialized=snapshot.lineage_materialized,
            runtimeTelemetryBacked=snapshot.runtime_telemetry_backed,
            platformCertified=snapshot.platform_certified,
            certificationStatus=snapshot.certification_status,
            certificationReady=snapshot.certification_ready,
            certificationBlockers=snapshot.certification_blockers,
            supportedFeaturePromoted=snapshot.supported_feature_promoted,
        )


class RuntimeTrustTelemetryFreshnessResponse(BaseModel):
    freshness_class: str
    freshness_state: str
    evaluated_at_utc: str
    age_seconds: int | None = None
    max_allowed_age_seconds: int | None = None


class RuntimeTrustTelemetryLineageResponse(BaseModel):
    lineage_materialized: bool
    evidence_access_class: str
    evidence_uris: list[str]


class RuntimeTrustTelemetryBlockingResponse(BaseModel):
    blocked: bool
    blocked_reason: str


class RuntimeTrustTelemetryEvidenceResponse(BaseModel):
    correlation_id: str
    validation_lanes: list[str]
    source_artifact_uri: str


class RuntimeTrustTelemetrySnapshotResponse(BaseModel):
    contract_id: str
    contract_version: str
    governed_by_rfcs: list[str]
    emitted_at_utc: str
    product_id: str
    producer_repository: str
    product_name: str
    product_version: str
    source_repository: str
    freshness: RuntimeTrustTelemetryFreshnessResponse
    completeness_status: str
    reconciliation_status: str
    data_quality_status: str
    lineage: RuntimeTrustTelemetryLineageResponse
    blocking: RuntimeTrustTelemetryBlockingResponse
    observed_trust_metadata: Mapping[str, str]
    evidence: RuntimeTrustTelemetryEvidenceResponse

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "RuntimeTrustTelemetrySnapshotResponse":
        return cls(**payload)


async def get_runtime_trust_telemetry_preview(
    generated_at_utc: datetime | None = Query(default=None, alias="generatedAtUtc"),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
) -> RuntimeTrustTelemetryPreviewResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
    )
    try:
        require_role_and_capability(caller, _READ_RUNTIME_TRUST_TELEMETRY_POLICY)
    except PermissionDeniedError:
        _emit_runtime_trust_telemetry_event(
            IdeaOperation.MESH_TRUST_TELEMETRY_PREVIEW_READ,
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return problem_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to read idea runtime trust telemetry preview.",
        )
    if generated_at_utc is not None and (
        generated_at_utc.tzinfo is None or generated_at_utc.utcoffset() is None
    ):
        _emit_runtime_trust_telemetry_event(
            IdeaOperation.MESH_TRUST_TELEMETRY_PREVIEW_READ,
            OperationOutcome.INVALID_REQUEST,
            "invalid_request",
        )
        return problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail="generatedAtUtc must be timezone-aware when provided.",
        )

    repository = get_idea_repository()
    durable_storage_backed = idea_repository_durable_storage_backed(repository)
    snapshot = build_runtime_trust_telemetry_preview(
        repository=repository,
        durable_storage_backed=durable_storage_backed,
        generated_at_utc=generated_at_utc,
    )
    _emit_runtime_trust_telemetry_event(
        IdeaOperation.MESH_TRUST_TELEMETRY_PREVIEW_READ,
        OperationOutcome.BLOCKED,
        durable_storage_backed=durable_storage_backed,
        candidate_snapshot_count=snapshot.candidate_snapshot_count,
    )
    return RuntimeTrustTelemetryPreviewResponse.from_domain(snapshot)


async def get_runtime_trust_telemetry_snapshot(
    generated_at_utc: datetime | None = Query(default=None, alias="generatedAtUtc"),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
) -> RuntimeTrustTelemetrySnapshotResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
    )
    try:
        require_role_and_capability(caller, _READ_RUNTIME_TRUST_TELEMETRY_SNAPSHOT_POLICY)
    except PermissionDeniedError:
        _emit_runtime_trust_telemetry_event(
            IdeaOperation.MESH_TRUST_TELEMETRY_SNAPSHOT_READ,
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return problem_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to read idea runtime trust telemetry snapshot.",
        )
    if generated_at_utc is not None and (
        generated_at_utc.tzinfo is None or generated_at_utc.utcoffset() is None
    ):
        _emit_runtime_trust_telemetry_event(
            IdeaOperation.MESH_TRUST_TELEMETRY_SNAPSHOT_READ,
            OperationOutcome.INVALID_REQUEST,
            "invalid_request",
        )
        return problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail="generatedAtUtc must be timezone-aware when provided.",
        )

    repository = get_idea_repository()
    durable_storage_backed = idea_repository_durable_storage_backed(repository)
    candidate_snapshot_count = len(repository.snapshot().candidate_records)
    snapshot = build_runtime_trust_telemetry_snapshot(
        repository=repository,
        durable_storage_backed=durable_storage_backed,
        generated_at_utc=generated_at_utc,
    )
    payload = snapshot.to_dict()
    _emit_runtime_trust_telemetry_event(
        IdeaOperation.MESH_TRUST_TELEMETRY_SNAPSHOT_READ,
        OperationOutcome.BLOCKED,
        durable_storage_backed=durable_storage_backed,
        candidate_snapshot_count=candidate_snapshot_count,
    )
    return RuntimeTrustTelemetrySnapshotResponse.from_payload(payload)


def _emit_runtime_trust_telemetry_event(
    operation: IdeaOperation,
    outcome: OperationOutcome,
    error_code: str | None = None,
    *,
    durable_storage_backed: bool = False,
    candidate_snapshot_count: int | None = None,
) -> None:
    attributes: dict[str, str] = {}
    if candidate_snapshot_count is not None:
        attributes["candidate_snapshot_count_bucket"] = _count_bucket(candidate_snapshot_count)
    emit_operation_event(
        OperationEvent(
            operation=operation,
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
    return "101+"


RUNTIME_TRUST_TELEMETRY_PREVIEW_ROUTE: RouteMetadata = {
    "path": "/api/v1/data-mesh/trust-telemetry/runtime-preview",
    "operation_id": "getIdeaRuntimeTrustTelemetryPreview",
    "summary": "Get idea runtime trust telemetry preview",
    "description": (
        "Returns a source-safe runtime trust telemetry preview for the proposed "
        "IdeaCandidate data product. The endpoint reports aggregate repository "
        "counts, source-authority coverage, freshness, supportability, lifecycle, "
        "workflow, and certification blockers for internal operators. It is not "
        "platform mesh certification, does not expose candidate identifiers or "
        "source routes, and does not promote a supported feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": RuntimeTrustTelemetryPreviewResponse,
    "tags": ["Data Mesh"],
    "responses": {
        200: {
            "description": "Runtime trust telemetry preview returned.",
            "content": {
                "application/json": {
                    "example": {
                        "repository": "lotus-idea",
                        "productId": "lotus-idea:IdeaCandidate:v1",
                        "generatedAtUtc": "2026-06-21T10:10:00Z",
                        "candidateSnapshotCount": 2,
                        "currentSourceRefCount": 8,
                        "staleOrUnavailableSourceRefCount": 0,
                        "sourceAuthorityCounts": {"lotus-core": 8},
                        "freshnessCounts": {"current": 8},
                        "supportabilityCounts": {"ready": 2},
                        "lifecycleCounts": {"generated": 2},
                        "reviewDecisionCount": 0,
                        "feedbackEventCount": 0,
                        "conversionIntentCount": 0,
                        "conversionOutcomeCount": 0,
                        "reportEvidencePackCount": 0,
                        "lineageMaterialized": True,
                        "runtimeTelemetryBacked": True,
                        "platformCertified": False,
                        "certificationStatus": "not_certified",
                        "certificationReady": False,
                        "certificationBlockers": [
                            "platform_source_manifest_inclusion_missing",
                            "platform_mesh_certification_missing",
                            "gateway_workbench_discovery_proof_missing",
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
            "description": "Caller lacks runtime trust telemetry preview permission.",
        },
    },
}


RUNTIME_TRUST_TELEMETRY_SNAPSHOT_ROUTE: RouteMetadata = {
    "path": "/api/v1/data-mesh/trust-telemetry/runtime-snapshot",
    "operation_id": "getIdeaRuntimeTrustTelemetrySnapshot",
    "summary": "Get idea runtime trust telemetry snapshot",
    "description": (
        "Returns the source-safe, contract-shaped runtime trust telemetry snapshot for the "
        "proposed IdeaCandidate data product. The endpoint is an internal operator proof "
        "surface over aggregate active-repository state. It is not platform mesh "
        "certification, does not expose candidate identifiers or source routes, and does "
        "not promote a supported feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": RuntimeTrustTelemetrySnapshotResponse,
    "tags": ["Data Mesh"],
    "responses": {
        200: {
            "description": "Runtime trust telemetry snapshot returned.",
            "content": {
                "application/json": {
                    "example": {
                        "contract_id": "lotus-domain-product-trust-telemetry-snapshot",
                        "contract_version": "1.0.0",
                        "governed_by_rfcs": ["RFC-0087", "RFC-0091", "RFC-0002"],
                        "emitted_at_utc": "2026-06-21T10:10:00Z",
                        "product_id": "lotus-idea:IdeaCandidate:v1",
                        "producer_repository": "lotus-idea",
                        "product_name": "IdeaCandidate",
                        "product_version": "v1",
                        "source_repository": "lotus-idea",
                        "freshness": {
                            "freshness_class": "daily",
                            "freshness_state": "current",
                            "evaluated_at_utc": "2026-06-21T10:10:00Z",
                            "age_seconds": 600,
                            "max_allowed_age_seconds": 86400,
                        },
                        "completeness_status": "partial",
                        "reconciliation_status": "not_applicable",
                        "data_quality_status": "quality_passed",
                        "lineage": {
                            "lineage_materialized": True,
                            "evidence_access_class": "operator_only",
                            "evidence_uris": [
                                "lotus-idea://runtime/idea-candidate/source-owned-lineage"
                            ],
                        },
                        "blocking": {
                            "blocked": True,
                            "blocked_reason": (
                                "Runtime trust telemetry snapshot generated for "
                                "IdeaCandidate:v1, but platform source manifest inclusion, "
                                "platform mesh certification, Gateway/Workbench discovery "
                                "proof, and supported-feature promotion remain pending."
                            ),
                        },
                        "observed_trust_metadata": {
                            "product_name": "IdeaCandidate",
                            "product_version": "v1",
                            "generated_at": "2026-06-21T10:10:00Z",
                            "reconciliation_status": "not_applicable",
                            "data_quality_status": "quality_passed",
                            "lineage_bundle_id": "lotus-idea:IdeaCandidate:v1:runtime-lineage",
                            "correlation_id": "lotus-idea-runtime-trust-telemetry-snapshot",
                            "as_of_date": "2026-06-21",
                            "source_batch_fingerprint": "source-safe-runtime-aggregate",
                        },
                        "evidence": {
                            "correlation_id": "lotus-idea-runtime-trust-telemetry-snapshot",
                            "validation_lanes": ["feature", "pr-merge", "main-releasability"],
                            "source_artifact_uri": (
                                "lotus-idea://output/trust-telemetry/runtime/"
                                "idea-candidate.telemetry.v1.json"
                            ),
                        },
                    }
                }
            },
        },
        400: {"model": ProblemDetails, "description": "Request validation failed."},
        403: {
            "model": ProblemDetails,
            "description": "Caller lacks runtime trust telemetry snapshot permission.",
        },
    },
}


def register_runtime_trust_telemetry_routes(app: FastAPI) -> None:
    app.get(
        path=RUNTIME_TRUST_TELEMETRY_PREVIEW_ROUTE["path"],
        operation_id=RUNTIME_TRUST_TELEMETRY_PREVIEW_ROUTE["operation_id"],
        summary=RUNTIME_TRUST_TELEMETRY_PREVIEW_ROUTE["summary"],
        description=RUNTIME_TRUST_TELEMETRY_PREVIEW_ROUTE["description"],
        status_code=RUNTIME_TRUST_TELEMETRY_PREVIEW_ROUTE["status_code"],
        response_model=RUNTIME_TRUST_TELEMETRY_PREVIEW_ROUTE["response_model"],
        tags=RUNTIME_TRUST_TELEMETRY_PREVIEW_ROUTE["tags"],
        responses=RUNTIME_TRUST_TELEMETRY_PREVIEW_ROUTE["responses"],
    )(get_runtime_trust_telemetry_preview)
    app.get(
        path=RUNTIME_TRUST_TELEMETRY_SNAPSHOT_ROUTE["path"],
        operation_id=RUNTIME_TRUST_TELEMETRY_SNAPSHOT_ROUTE["operation_id"],
        summary=RUNTIME_TRUST_TELEMETRY_SNAPSHOT_ROUTE["summary"],
        description=RUNTIME_TRUST_TELEMETRY_SNAPSHOT_ROUTE["description"],
        status_code=RUNTIME_TRUST_TELEMETRY_SNAPSHOT_ROUTE["status_code"],
        response_model=RUNTIME_TRUST_TELEMETRY_SNAPSHOT_ROUTE["response_model"],
        tags=RUNTIME_TRUST_TELEMETRY_SNAPSHOT_ROUTE["tags"],
        responses=RUNTIME_TRUST_TELEMETRY_SNAPSHOT_ROUTE["responses"],
    )(get_runtime_trust_telemetry_snapshot)
