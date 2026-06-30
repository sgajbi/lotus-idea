from __future__ import annotations

import json
from datetime import datetime
from typing import Mapping

from fastapi import FastAPI, Header, Query, status
from fastapi.responses import JSONResponse
from pydantic import Field

from app.api.base_model import CamelModel
from app.api.caller_headers import caller_context_from_headers
from app.api.problem_details import (
    invalid_request_metadata,
    permission_denied_metadata,
    service_unavailable_metadata,
)
from app.api.route_metadata import RouteMetadata
from app.api.runtime_dependencies import (
    configured_implementation_proof_artifacts,
    get_idea_repository,
    idea_repository_durable_storage_backed,
)
from app.api.temporal_validation import is_timezone_aware
from app.application.implementation_proof_models import (
    ImplementationProofCapabilityReadiness,
    ImplementationProofReadinessSnapshot,
)
from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
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

_READ_IMPLEMENTATION_PROOF_READINESS_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.implementation-proof.readiness.read",
    allowed_roles=("operator",),
)


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
    if not is_timezone_aware(evaluated_at_utc):
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
        proof_artifacts = configured_implementation_proof_artifacts()
        snapshot = build_implementation_proof_readiness_snapshot(
            evaluated_at_utc=evaluated_at_utc,
            repository=repository,
            durable_storage_backed=durable_storage_backed,
            source_ingestion_live_proof_ref=proof_artifacts.source_ingestion_live_proof_ref,
            source_ingestion_scheduled_worker_proof_ref=(
                proof_artifacts.source_ingestion_scheduled_worker_proof_ref
            ),
            durable_repository_proof=proof_artifacts.durable_repository_proof,
            durable_repository_proof_ref=proof_artifacts.durable_repository_proof_ref,
            runtime_trust_telemetry_proof=proof_artifacts.runtime_trust_telemetry_proof,
            runtime_trust_telemetry_proof_ref=proof_artifacts.runtime_trust_telemetry_proof_ref,
            ai_lineage_store_proof=proof_artifacts.ai_lineage_store_proof,
            ai_lineage_store_proof_ref=proof_artifacts.ai_lineage_store_proof_ref,
            ai_model_risk_operations_proof=(proof_artifacts.ai_model_risk_operations_proof),
            ai_model_risk_operations_proof_ref=(proof_artifacts.ai_model_risk_operations_proof_ref),
            ai_workflow_pack_registration_proof=(
                proof_artifacts.ai_workflow_pack_registration_proof
            ),
            ai_workflow_pack_registration_proof_ref=(
                proof_artifacts.ai_workflow_pack_registration_proof_ref
            ),
            ai_workflow_pack_runtime_execution_proof=(
                proof_artifacts.ai_workflow_pack_runtime_execution_proof
            ),
            ai_workflow_pack_runtime_execution_proof_ref=(
                proof_artifacts.ai_workflow_pack_runtime_execution_proof_ref
            ),
            outbox_broker_proof=proof_artifacts.outbox_broker_proof,
            outbox_broker_proof_ref=proof_artifacts.outbox_broker_proof_ref,
            outbox_platform_mesh_event_publication_proof=(
                proof_artifacts.outbox_platform_mesh_event_publication_proof
            ),
            outbox_platform_mesh_event_publication_proof_ref=(
                proof_artifacts.outbox_platform_mesh_event_publication_proof_ref
            ),
            report_intake_route_proof=proof_artifacts.report_intake_route_proof,
            report_intake_route_proof_ref=proof_artifacts.report_intake_route_proof_ref,
            platform_mesh_onboarding_proof=proof_artifacts.platform_mesh_onboarding_proof,
            platform_mesh_onboarding_proof_ref=(proof_artifacts.platform_mesh_onboarding_proof_ref),
            workbench_read_path_proof=proof_artifacts.workbench_read_path_proof,
            workbench_read_path_proof_ref=proof_artifacts.workbench_read_path_proof_ref,
            gateway_workbench_operational_proof=(
                proof_artifacts.gateway_workbench_operational_proof
            ),
            gateway_workbench_operational_proof_ref=(
                proof_artifacts.gateway_workbench_operational_proof_ref
            ),
            gateway_workbench_discovery_proof=proof_artifacts.gateway_workbench_discovery_proof,
            gateway_workbench_discovery_proof_ref=(
                proof_artifacts.gateway_workbench_discovery_proof_ref
            ),
            bond_maturity_live_proof=proof_artifacts.bond_maturity_live_proof,
            bond_maturity_live_proof_ref=proof_artifacts.bond_maturity_live_proof_ref,
            low_income_core_cashflow_live_proof=(
                proof_artifacts.low_income_core_cashflow_live_proof
            ),
            low_income_core_cashflow_live_proof_ref=(
                proof_artifacts.low_income_core_cashflow_live_proof_ref
            ),
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
        **invalid_request_metadata(
            detail="Correct the implementation proof readiness request and retry.",
        ),
        **permission_denied_metadata(
            detail="The caller is not permitted to read implementation proof readiness.",
            description="Caller lacks implementation proof readiness permission.",
        ),
        **service_unavailable_metadata(
            code="readiness_source_contracts_unavailable",
            title="Implementation proof readiness unavailable",
            detail="Readiness source contracts are unavailable.",
            description="Readiness source contracts are unavailable.",
        ),
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
