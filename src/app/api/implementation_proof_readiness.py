from __future__ import annotations

import json
from datetime import datetime
from typing import Mapping

from fastapi import FastAPI, Header, Query, status
from fastapi.responses import JSONResponse
from pydantic import Field

from app.api.base_model import CamelModel
from app.api.caller_headers import TRUSTED_CALLER_CONTEXT_HEADER, caller_context_from_headers
from app.api.problem_details import (
    invalid_request_metadata,
    permission_denied_metadata,
    service_unavailable_metadata,
)
from app.api.route_metadata import RouteMetadata
from app.api.runtime_dependencies import (
    ConfiguredImplementationProofArtifacts,
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
from app.ports.idea_repository import IdeaRepository
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
            supportedFeaturePromoted=snapshot.supported_features_promoted,
        )


async def get_implementation_proof_readiness(
    evaluated_at_utc: datetime = Query(..., alias="evaluatedAtUtc"),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
    x_lotus_trusted_caller_context: str | None = Header(
        default=None,
        alias=TRUSTED_CALLER_CONTEXT_HEADER,
    ),
) -> ImplementationProofReadinessResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
        trusted_caller_context=x_lotus_trusted_caller_context,
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
        snapshot = _build_readiness_snapshot_from_configured_artifacts(
            evaluated_at_utc=evaluated_at_utc,
            repository=repository,
            durable_storage_backed=durable_storage_backed,
            proof_artifacts=configured_implementation_proof_artifacts(),
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


def _build_readiness_snapshot_from_configured_artifacts(
    *,
    evaluated_at_utc: datetime,
    repository: IdeaRepository,
    durable_storage_backed: bool,
    proof_artifacts: ConfiguredImplementationProofArtifacts,
) -> ImplementationProofReadinessSnapshot:
    return build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=evaluated_at_utc,
        repository=repository,
        durable_storage_backed=durable_storage_backed,
        source_ingestion_runtime_execution=(proof_artifacts.source_ingestion_runtime_execution),
        source_ingestion_runtime_execution_ref=(
            proof_artifacts.source_ingestion_runtime_execution_ref
        ),
        source_ingestion_scheduled_worker_source_contract_ref=(
            proof_artifacts.source_ingestion_scheduled_worker_source_contract_ref
        ),
        source_ingestion_scheduled_worker_deployment_evidence_ref=(
            proof_artifacts.source_ingestion_scheduled_worker_deployment_evidence_ref
        ),
        durable_repository_proof=proof_artifacts.durable_repository_proof,
        durable_repository_proof_ref=proof_artifacts.durable_repository_proof_ref,
        runtime_trust_telemetry_test_execution=proof_artifacts.runtime_trust_telemetry_test_execution,
        runtime_trust_telemetry_test_execution_ref=proof_artifacts.runtime_trust_telemetry_test_execution_ref,
        ai_lineage_store_proof=proof_artifacts.ai_lineage_store_proof,
        ai_lineage_store_proof_ref=proof_artifacts.ai_lineage_store_proof_ref,
        ai_model_risk_operations_proof=proof_artifacts.ai_model_risk_operations_proof,
        ai_model_risk_operations_proof_ref=proof_artifacts.ai_model_risk_operations_proof_ref,
        operator_workflows_operations_proof=proof_artifacts.operator_workflows_operations_proof,
        operator_workflows_operations_proof_ref=(
            proof_artifacts.operator_workflows_operations_proof_ref
        ),
        ai_workflow_pack_registration_proof=proof_artifacts.ai_workflow_pack_registration_proof,
        ai_workflow_pack_registration_proof_ref=(
            proof_artifacts.ai_workflow_pack_registration_proof_ref
        ),
        ai_workflow_pack_runtime_execution_proof=(
            proof_artifacts.ai_workflow_pack_runtime_execution_proof
        ),
        ai_workflow_pack_runtime_execution_proof_ref=(
            proof_artifacts.ai_workflow_pack_runtime_execution_proof_ref
        ),
        advise_intake_runtime_execution_proof=(
            proof_artifacts.advise_intake_runtime_execution_proof
        ),
        advise_intake_runtime_execution_proof_ref=(
            proof_artifacts.advise_intake_runtime_execution_proof_ref
        ),
        outbox_broker_source_contract_proof=proof_artifacts.outbox_broker_source_contract_proof,
        outbox_broker_source_contract_proof_ref=(
            proof_artifacts.outbox_broker_source_contract_proof_ref
        ),
        outbox_platform_mesh_event_source_contract_proof=(
            proof_artifacts.outbox_platform_mesh_event_source_contract_proof
        ),
        outbox_platform_mesh_event_source_contract_proof_ref=(
            proof_artifacts.outbox_platform_mesh_event_source_contract_proof_ref
        ),
        report_intake_route_source_contract_proof=proof_artifacts.report_intake_route_source_contract_proof,
        report_intake_route_source_contract_proof_ref=proof_artifacts.report_intake_route_source_contract_proof_ref,
        platform_catalog_source_contract_proof=proof_artifacts.platform_catalog_source_contract,
        platform_catalog_source_contract_proof_ref=(
            proof_artifacts.platform_catalog_source_contract_ref
        ),
        workbench_read_path_source_contract_proof=(
            proof_artifacts.workbench_read_path_source_contract_proof
        ),
        workbench_read_path_source_contract_proof_ref=(
            proof_artifacts.workbench_read_path_source_contract_proof_ref
        ),
        gateway_workbench_contract_proof=proof_artifacts.gateway_workbench_contract_proof,
        gateway_workbench_contract_proof_ref=(proof_artifacts.gateway_workbench_contract_proof_ref),
        gateway_workbench_discovery_contract_proof=proof_artifacts.gateway_workbench_discovery_contract_proof,
        gateway_workbench_discovery_contract_proof_ref=(
            proof_artifacts.gateway_workbench_discovery_contract_proof_ref
        ),
        bond_maturity_live_proof=proof_artifacts.bond_maturity_live_proof,
        bond_maturity_live_proof_ref=proof_artifacts.bond_maturity_live_proof_ref,
        low_income_core_cashflow_live_proof=proof_artifacts.low_income_core_cashflow_live_proof,
        low_income_core_cashflow_live_proof_ref=(
            proof_artifacts.low_income_core_cashflow_live_proof_ref
        ),
    )


IMPLEMENTATION_PROOF_READINESS_ROUTE: RouteMetadata = {
    "path": "/api/v1/implementation-proof/readiness",
    "operation_id": "getIdeaImplementationProofReadiness",
    "summary": "Get idea implementation proof readiness",
    "description": (
        "Returns an aggregate, source-safe operator readiness snapshot for RFC-0002 "
        "implementation proof. The endpoint summarizes existing internal foundations "
        "and remaining blockers for source ingestion, review queue, AI explanation, "
        "data mesh, runtime trust telemetry preview, outbox delivery, non-AI "
        "operator workflow operations, Workbench realization, downstream realization, "
        "and supported-feature promotion. It "
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
                        "capabilityCount": 11,
                        "certificationReadyCapabilityCount": 0,
                        "blockedCapabilityCount": 11,
                        "supportedFeatureCount": 0,
                        "supportedFeaturesPromoted": False,
                        "overallBlockers": [
                            "source_ingestion_manifest_not_configured",
                            "operator_workflow_dashboard_runtime_proof_missing",
                            "operator_workflow_alert_rules_runtime_proof_missing",
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
                                "capabilityId": "operator-workflows-operations",
                                "name": "Non-AI operator workflow operations",
                                "readinessStatus": "blocked",
                                "supportabilityStatus": "not_certified",
                                "certificationReady": False,
                                "evidenceRefs": [
                                    (
                                        "contracts/observability/"
                                        "lotus-idea-operator-workflows-operations.v1.json"
                                    ),
                                    "make operator-workflows-ops-contract-gate",
                                    "make operator-workflows-operations-proof-contract-gate",
                                ],
                                "blockers": [
                                    "operator_workflow_dashboard_runtime_proof_missing",
                                    "operator_workflow_alert_rules_runtime_proof_missing",
                                    "external_broker_runtime_proof_missing",
                                    "gateway_workbench_proof_missing",
                                    "supported_feature_promotion_missing",
                                ],
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
