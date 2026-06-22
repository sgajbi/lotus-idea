from __future__ import annotations

from enum import Enum
from typing import Any, Mapping, TypedDict

from fastapi import FastAPI, Header, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api.caller_headers import caller_context_from_headers
from app.runtime.repository_state import get_idea_repository, idea_repository_durable_storage_backed
from app.application.downstream_realization_readiness import (
    DownstreamRealizationCapabilityReadiness,
    DownstreamRealizationContractReadiness,
    DownstreamRealizationReadinessSnapshot,
    build_downstream_realization_readiness_snapshot,
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


_READ_DOWNSTREAM_REALIZATION_READINESS_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.downstream-realization.readiness.read",
    allowed_roles=("operator",),
)


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class DownstreamRealizationCapabilityReadinessResponse(CamelModel):
    capability_id: str = Field(..., alias="capabilityId")
    name: str
    source_authority: str = Field(..., alias="sourceAuthority")
    readiness_status: str = Field(..., alias="readinessStatus")
    supportability_status: str = Field(..., alias="supportabilityStatus")
    certification_ready: bool = Field(..., alias="certificationReady")
    evidence_refs: tuple[str, ...] = Field(..., alias="evidenceRefs")
    blockers: tuple[str, ...]

    @classmethod
    def from_domain(
        cls,
        capability: DownstreamRealizationCapabilityReadiness,
    ) -> "DownstreamRealizationCapabilityReadinessResponse":
        return cls(
            capabilityId=capability.capability_id,
            name=capability.name,
            sourceAuthority=capability.source_authority,
            readinessStatus=capability.readiness_status,
            supportabilityStatus=capability.supportability_status,
            certificationReady=capability.certification_ready,
            evidenceRefs=capability.evidence_refs,
            blockers=capability.blockers,
        )


class DownstreamRealizationContractReadinessResponse(CamelModel):
    contract_id: str = Field(..., alias="contractId")
    owner_repository: str = Field(..., alias="ownerRepository")
    source_authority: str = Field(..., alias="sourceAuthority")
    target_route: str = Field(..., alias="targetRoute")
    route_fit_status: str = Field(..., alias="routeFitStatus")
    adapter_status: str = Field(..., alias="adapterStatus")
    certification_ready: bool = Field(..., alias="certificationReady")
    evidence_refs: tuple[str, ...] = Field(..., alias="evidenceRefs")
    blockers: tuple[str, ...]

    @classmethod
    def from_domain(
        cls,
        contract: DownstreamRealizationContractReadiness,
    ) -> "DownstreamRealizationContractReadinessResponse":
        return cls(
            contractId=contract.contract_id,
            ownerRepository=contract.owner_repository,
            sourceAuthority=contract.source_authority,
            targetRoute=contract.target_route,
            routeFitStatus=contract.route_fit_status,
            adapterStatus=contract.adapter_status,
            certificationReady=contract.certification_ready,
            evidenceRefs=contract.evidence_refs,
            blockers=contract.blockers,
        )


class DownstreamRealizationReadinessResponse(CamelModel):
    repository: str
    readiness_status: str = Field(..., alias="readinessStatus")
    supportability_status: str = Field(..., alias="supportabilityStatus")
    certification_ready: bool = Field(..., alias="certificationReady")
    durable_storage_backed: bool = Field(..., alias="durableStorageBacked")
    conversion_intent_count: int = Field(..., alias="conversionIntentCount")
    conversion_outcome_count: int = Field(..., alias="conversionOutcomeCount")
    report_evidence_pack_request_count: int = Field(
        ...,
        alias="reportEvidencePackRequestCount",
    )
    downstream_adapter_foundation_present: bool = Field(
        ...,
        alias="downstreamAdapterFoundationPresent",
    )
    source_of_truth: Mapping[str, str] = Field(..., alias="sourceOfTruth")
    blockers: tuple[str, ...]
    capabilities: tuple[DownstreamRealizationCapabilityReadinessResponse, ...]
    downstream_contracts: tuple[DownstreamRealizationContractReadinessResponse, ...] = Field(
        ..., alias="downstreamContracts"
    )
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")

    @classmethod
    def from_domain(
        cls,
        snapshot: DownstreamRealizationReadinessSnapshot,
    ) -> "DownstreamRealizationReadinessResponse":
        return cls(
            repository=snapshot.repository,
            readinessStatus=snapshot.readiness_status,
            supportabilityStatus=snapshot.supportability_status,
            certificationReady=snapshot.certification_ready,
            durableStorageBacked=snapshot.durable_storage_backed,
            conversionIntentCount=snapshot.conversion_intent_count,
            conversionOutcomeCount=snapshot.conversion_outcome_count,
            reportEvidencePackRequestCount=snapshot.report_evidence_pack_request_count,
            downstreamAdapterFoundationPresent=snapshot.downstream_adapter_foundation_present,
            sourceOfTruth=dict(snapshot.source_of_truth),
            blockers=snapshot.blockers,
            capabilities=tuple(
                DownstreamRealizationCapabilityReadinessResponse.from_domain(capability)
                for capability in snapshot.capabilities
            ),
            downstreamContracts=tuple(
                DownstreamRealizationContractReadinessResponse.from_domain(contract)
                for contract in snapshot.downstream_contracts
            ),
            supportedFeaturePromoted=snapshot.supported_feature_promoted,
        )


async def get_downstream_realization_readiness(
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
) -> DownstreamRealizationReadinessResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
    )
    try:
        _require_downstream_realization_readiness_caller(caller)
    except PermissionDeniedError:
        _emit_downstream_realization_readiness_event(
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return problem_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to read idea downstream realization readiness.",
        )

    repository = get_idea_repository()
    durable_storage_backed = idea_repository_durable_storage_backed(repository)
    snapshot = build_downstream_realization_readiness_snapshot(
        repository=repository,
        durable_storage_backed=durable_storage_backed,
    )
    _emit_downstream_realization_readiness_event(
        OperationOutcome.ACCEPTED if snapshot.certification_ready else OperationOutcome.BLOCKED,
        durable_storage_backed=durable_storage_backed,
    )
    return DownstreamRealizationReadinessResponse.from_domain(snapshot)


def _require_downstream_realization_readiness_caller(caller: CallerContext) -> None:
    require_role_and_capability(caller, _READ_DOWNSTREAM_REALIZATION_READINESS_POLICY)


def _emit_downstream_realization_readiness_event(
    outcome: OperationOutcome,
    error_code: str | None = None,
    *,
    durable_storage_backed: bool = False,
) -> None:
    emit_operation_event(
        OperationEvent(
            operation=IdeaOperation.DOWNSTREAM_REALIZATION_READINESS_READ,
            outcome=outcome,
            source_authority="lotus-idea",
            supportability_status=OperationSupportability.NOT_CERTIFIED,
            durable_storage_backed=durable_storage_backed,
            supported_feature_promoted=False,
            error_code=error_code,
        )
    )


DOWNSTREAM_REALIZATION_READINESS_ROUTE: RouteMetadata = {
    "path": "/api/v1/downstream-realization/readiness",
    "operation_id": "getIdeaDownstreamRealizationReadiness",
    "summary": "Get idea downstream realization readiness",
    "description": (
        "Returns source-safe operator readiness for downstream realization across "
        "lotus-advise, lotus-manage, lotus-report, lotus-render, and lotus-archive. "
        "The endpoint reports lotus-idea-owned conversion intent, conversion outcome, "
        "report evidence-pack request counts, planned Advise/Manage/Report downstream "
        "contract posture, source-safe adapter-foundation presence, and explicit "
        "downstream blockers. It does not call downstream systems, create proposals, "
        "create manage actions, prove downstream route existence, render documents, "
        "archive records, authorize client publication, or promote a supported feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": DownstreamRealizationReadinessResponse,
    "tags": ["Operations"],
    "responses": {
        200: {
            "description": "Downstream realization readiness posture returned.",
            "content": {
                "application/json": {
                    "example": {
                        "repository": "lotus-idea",
                        "readinessStatus": "blocked",
                        "supportabilityStatus": "not_certified",
                        "certificationReady": False,
                        "durableStorageBacked": False,
                        "conversionIntentCount": 0,
                        "conversionOutcomeCount": 0,
                        "reportEvidencePackRequestCount": 0,
                        "downstreamAdapterFoundationPresent": True,
                        "sourceOfTruth": {
                            "conversion_workflow": "src/app/application/conversion_workflow.py",
                            "report_evidence_workflow": "src/app/application/report_evidence.py",
                            "downstream_adapter_port": "src/app/ports/downstream_realization.py",
                            "downstream_adapter_foundation": (
                                "src/app/infrastructure/downstream_realization.py"
                            ),
                            "downstream_contract_plan": (
                                "contracts/downstream-realization/"
                                "lotus-idea-downstream-contracts.v1.json"
                            ),
                            "downstream_contract_gate": (
                                "scripts/downstream_realization_contract_gate.py"
                            ),
                        },
                        "blockers": [
                            "advise_live_contract_proof_missing",
                            "manage_live_contract_proof_missing",
                            "report_evidence_pack_live_materialization_proof_missing",
                            "dedicated_report_idea_evidence_intake_contract_missing",
                        ],
                        "capabilities": [
                            {
                                "capabilityId": "advise-proposal-realization",
                                "name": "Advise proposal and suitability realization",
                                "sourceAuthority": "lotus-advise",
                                "readinessStatus": "planned",
                                "supportabilityStatus": "not_certified",
                                "certificationReady": False,
                                "evidenceRefs": [
                                    "POST /api/v1/idea-candidates/{candidateId}/conversion-intents"
                                ],
                                "blockers": ["advise_live_contract_proof_missing"],
                            }
                        ],
                        "downstreamContracts": [
                            {
                                "contractId": (
                                    "lotus-idea-to-lotus-report-evidence-pack-intake:v1"
                                ),
                                "ownerRepository": "lotus-report",
                                "sourceAuthority": "lotus-report",
                                "targetRoute": "planned:lotus-report-idea-evidence-pack-intake",
                                "routeFitStatus": "not_certified",
                                "adapterStatus": "adapter_foundation_present",
                                "certificationReady": False,
                                "evidenceRefs": [
                                    "POST /api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs"
                                ],
                                "blockers": [
                                    "dedicated_report_idea_evidence_intake_contract_missing"
                                ],
                            }
                        ],
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        403: {
            "model": ProblemDetails,
            "description": "Caller lacks downstream realization readiness permission.",
        },
    },
}


def register_downstream_realization_readiness_routes(app: FastAPI) -> None:
    app.get(
        path=DOWNSTREAM_REALIZATION_READINESS_ROUTE["path"],
        operation_id=DOWNSTREAM_REALIZATION_READINESS_ROUTE["operation_id"],
        summary=DOWNSTREAM_REALIZATION_READINESS_ROUTE["summary"],
        description=DOWNSTREAM_REALIZATION_READINESS_ROUTE["description"],
        status_code=DOWNSTREAM_REALIZATION_READINESS_ROUTE["status_code"],
        response_model=DOWNSTREAM_REALIZATION_READINESS_ROUTE["response_model"],
        tags=DOWNSTREAM_REALIZATION_READINESS_ROUTE["tags"],
        responses=DOWNSTREAM_REALIZATION_READINESS_ROUTE["responses"],
    )(get_downstream_realization_readiness)
