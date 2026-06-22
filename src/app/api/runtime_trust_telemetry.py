from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Mapping, TypedDict

from fastapi import FastAPI, Header, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api.caller_headers import caller_context_from_headers
from app.api.repository_state import get_idea_repository, idea_repository_durable_storage_backed
from app.application.runtime_trust_telemetry import (
    RuntimeTrustTelemetryPreview,
    build_runtime_trust_telemetry_preview,
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


_READ_RUNTIME_TRUST_TELEMETRY_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.mesh.trust-telemetry.preview.read",
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
        OperationOutcome.BLOCKED,
        durable_storage_backed=durable_storage_backed,
        candidate_snapshot_count=snapshot.candidate_snapshot_count,
    )
    return RuntimeTrustTelemetryPreviewResponse.from_domain(snapshot)


def _emit_runtime_trust_telemetry_event(
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
            operation=IdeaOperation.MESH_TRUST_TELEMETRY_PREVIEW_READ,
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
