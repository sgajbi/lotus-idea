from __future__ import annotations

from datetime import datetime
from enum import Enum
import json
from typing import Any, Mapping, TypedDict

from fastapi import FastAPI, Header, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api.caller_headers import caller_context_from_headers
from app.runtime.repository_state import get_idea_repository, idea_repository_durable_storage_backed
from app.application.implementation_proof_readiness import (
    ImplementationProofCapabilityReadiness,
    ImplementationProofReadinessSnapshot,
    build_implementation_proof_readiness_snapshot,
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


_READ_IMPLEMENTATION_PROOF_READINESS_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.implementation-proof.readiness.read",
    allowed_roles=("operator",),
)


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class ImplementationProofCapabilityReadinessResponse(CamelModel):
    capability_id: str = Field(..., alias="capabilityId")
    name: str
    readiness_status: str = Field(..., alias="readinessStatus")
    supportability_status: str = Field(..., alias="supportabilityStatus")
    certification_ready: bool = Field(..., alias="certificationReady")
    evidence_refs: tuple[str, ...] = Field(..., alias="evidenceRefs")
    blockers: tuple[str, ...]
    supported_feature_promoted: bool = Field(..., alias="supportedFeaturePromoted")

    @classmethod
    def from_domain(
        cls,
        capability: ImplementationProofCapabilityReadiness,
    ) -> "ImplementationProofCapabilityReadinessResponse":
        return cls(
            capabilityId=capability.capability_id,
            name=capability.name,
            readinessStatus=capability.readiness_status,
            supportabilityStatus=capability.supportability_status,
            certificationReady=capability.certification_ready,
            evidenceRefs=capability.evidence_refs,
            blockers=capability.blockers,
            supportedFeaturePromoted=capability.supported_feature_promoted,
        )


class ImplementationProofReadinessResponse(CamelModel):
    repository: str
    evaluated_at_utc: datetime = Field(..., alias="evaluatedAtUtc")
    readiness_status: str = Field(..., alias="readinessStatus")
    supportability_status: str = Field(..., alias="supportabilityStatus")
    certification_ready: bool = Field(..., alias="certificationReady")
    capability_count: int = Field(..., alias="capabilityCount")
    certification_ready_capability_count: int = Field(
        ...,
        alias="certificationReadyCapabilityCount",
    )
    blocked_capability_count: int = Field(..., alias="blockedCapabilityCount")
    supported_feature_count: int = Field(..., alias="supportedFeatureCount")
    supported_features_promoted: bool = Field(..., alias="supportedFeaturesPromoted")
    overall_blockers: tuple[str, ...] = Field(..., alias="overallBlockers")
    source_of_truth: Mapping[str, str] = Field(..., alias="sourceOfTruth")
    capabilities: tuple[ImplementationProofCapabilityReadinessResponse, ...]
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")

    @classmethod
    def from_domain(
        cls,
        snapshot: ImplementationProofReadinessSnapshot,
    ) -> "ImplementationProofReadinessResponse":
        return cls(
            repository=snapshot.repository,
            evaluatedAtUtc=snapshot.evaluated_at_utc,
            readinessStatus=snapshot.readiness_status,
            supportabilityStatus=snapshot.supportability_status,
            certificationReady=snapshot.certification_ready,
            capabilityCount=snapshot.capability_count,
            certificationReadyCapabilityCount=snapshot.certification_ready_capability_count,
            blockedCapabilityCount=snapshot.blocked_capability_count,
            supportedFeatureCount=snapshot.supported_feature_count,
            supportedFeaturesPromoted=snapshot.supported_features_promoted,
            overallBlockers=snapshot.overall_blockers,
            sourceOfTruth=dict(snapshot.source_of_truth),
            capabilities=tuple(
                ImplementationProofCapabilityReadinessResponse.from_domain(capability)
                for capability in snapshot.capabilities
            ),
            supportedFeaturePromoted=False,
        )


async def get_implementation_proof_readiness(
    evaluated_at_utc: datetime = Query(..., alias="evaluatedAtUtc"),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
) -> ImplementationProofReadinessResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
    )
    try:
        require_role_and_capability(caller, _READ_IMPLEMENTATION_PROOF_READINESS_POLICY)
    except PermissionDeniedError:
        _emit_implementation_proof_readiness_event(
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return problem_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to read idea implementation proof readiness.",
        )
    if evaluated_at_utc.tzinfo is None or evaluated_at_utc.utcoffset() is None:
        _emit_implementation_proof_readiness_event(
            OperationOutcome.INVALID_REQUEST,
            "invalid_request",
        )
        return problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail="evaluatedAtUtc must be timezone-aware.",
        )

    repository = get_idea_repository()
    durable_storage_backed = idea_repository_durable_storage_backed(repository)
    try:
        snapshot = build_implementation_proof_readiness_snapshot(
            evaluated_at_utc=evaluated_at_utc,
            repository=repository,
            durable_storage_backed=durable_storage_backed,
        )
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        _emit_implementation_proof_readiness_event(
            OperationOutcome.INVALID_STATE,
            "implementation_proof_readiness_unavailable",
            durable_storage_backed=durable_storage_backed,
        )
        return problem_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="implementation_proof_readiness_unavailable",
            title="Implementation proof readiness unavailable",
            detail="The service could not read its implementation proof readiness contracts.",
        )

    _emit_implementation_proof_readiness_event(
        OperationOutcome.ACCEPTED if snapshot.certification_ready else OperationOutcome.BLOCKED,
        durable_storage_backed=durable_storage_backed,
    )
    return ImplementationProofReadinessResponse.from_domain(snapshot)


def _emit_implementation_proof_readiness_event(
    outcome: OperationOutcome,
    error_code: str | None = None,
    *,
    durable_storage_backed: bool = False,
) -> None:
    emit_operation_event(
        OperationEvent(
            operation=IdeaOperation.IMPLEMENTATION_PROOF_READINESS_READ,
            outcome=outcome,
            source_authority="lotus-idea",
            supportability_status=OperationSupportability.NOT_CERTIFIED,
            durable_storage_backed=durable_storage_backed,
            supported_feature_promoted=False,
            error_code=error_code,
        )
    )


IMPLEMENTATION_PROOF_READINESS_ROUTE: RouteMetadata = {
    "path": "/api/v1/implementation-proof/readiness",
    "operation_id": "getIdeaImplementationProofReadiness",
    "summary": "Get idea implementation proof readiness",
    "description": (
        "Returns an aggregate, source-safe operator readiness snapshot for RFC-0002 "
        "implementation proof. The endpoint summarizes existing internal foundations "
        "and remaining blockers for source ingestion, review queue, AI explanation, "
        "data mesh, runtime trust telemetry preview, outbox delivery, Workbench "
        "realization, downstream realization, and supported-feature promotion. It "
        "does not expose candidate identifiers, source payloads, outbox event "
        "identifiers, broker payloads, Workbench proof, data-product certification, "
        "client-ready publication, or a supported feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": ImplementationProofReadinessResponse,
    "tags": ["Operations"],
    "responses": {
        200: {
            "description": "Aggregate implementation proof readiness posture returned.",
            "content": {
                "application/json": {
                    "example": {
                        "repository": "lotus-idea",
                        "evaluatedAtUtc": "2026-06-21T10:10:00Z",
                        "readinessStatus": "blocked",
                        "supportabilityStatus": "not_certified",
                        "certificationReady": False,
                        "capabilityCount": 9,
                        "certificationReadyCapabilityCount": 0,
                        "blockedCapabilityCount": 9,
                        "supportedFeatureCount": 0,
                        "supportedFeaturesPromoted": False,
                        "overallBlockers": [
                            "source_ingestion_manifest_not_configured",
                            "workbench_panel_missing",
                            "no_supported_features_promoted",
                        ],
                        "sourceOfTruth": {
                            "rfc": (
                                "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
                                "RFC-0002-enterprise-opportunity-intelligence-operating-layer.md"
                            ),
                            "supported_features": "supported-features/supported-features.json",
                        },
                        "capabilities": [
                            {
                                "capabilityId": "advisor-review-queue",
                                "name": "Deterministic advisor review queue",
                                "readinessStatus": "blocked",
                                "supportabilityStatus": "not_certified",
                                "certificationReady": False,
                                "evidenceRefs": ["GET /api/v1/review-queues/advisor"],
                                "blockers": ["workbench_product_proof_missing"],
                                "supportedFeaturePromoted": False,
                            }
                        ],
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        400: {"model": ProblemDetails, "description": "Request validation failed."},
        403: {
            "model": ProblemDetails,
            "description": "Caller lacks implementation proof readiness permission.",
        },
        503: {
            "model": ProblemDetails,
            "description": "Readiness source contracts are unavailable.",
        },
    },
}


def register_implementation_proof_readiness_routes(app: FastAPI) -> None:
    app.get(
        path=IMPLEMENTATION_PROOF_READINESS_ROUTE["path"],
        operation_id=IMPLEMENTATION_PROOF_READINESS_ROUTE["operation_id"],
        summary=IMPLEMENTATION_PROOF_READINESS_ROUTE["summary"],
        description=IMPLEMENTATION_PROOF_READINESS_ROUTE["description"],
        status_code=IMPLEMENTATION_PROOF_READINESS_ROUTE["status_code"],
        response_model=IMPLEMENTATION_PROOF_READINESS_ROUTE["response_model"],
        tags=IMPLEMENTATION_PROOF_READINESS_ROUTE["tags"],
        responses=IMPLEMENTATION_PROOF_READINESS_ROUTE["responses"],
    )(get_implementation_proof_readiness)
