from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI, Header, Path, status
from fastapi.responses import JSONResponse
from pydantic import Field, field_validator

from app.api.base_model import CamelModel
from app.api.caller_headers import caller_context_from_headers
from app.api.idea_signals import SourceRefRequest
from app.api.problem_details import (
    invalid_request_metadata,
    not_found_metadata,
    permission_denied_metadata,
)
from app.api.route_metadata import RouteMetadata
from app.api.runtime_dependencies import (
    get_idea_repository,
    idea_repository_durable_storage_backed,
)
from app.application.candidate_evidence_replay import (
    ReplayCandidateEvidenceCommand,
    replay_candidate_evidence,
)
from app.domain import CandidatePersistenceRecord, EvidenceReplayResult, EvidenceReplayStatus
from app.api.problem_details import problem_details_response as problem_response
from app.observability import IdeaOperation, OperationOutcome, emit_foundation_operation_event
from app.security.caller_context import (
    CapabilityPolicy,
    PermissionDeniedError,
    require_role_and_capability,
)

_REPLAY_CANDIDATE_EVIDENCE_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.candidate.evidence.replay",
    allowed_roles=("operator",),
)


class ReplayCandidateEvidenceRequest(CamelModel):
    evaluated_at_utc: datetime = Field(
        ...,
        alias="evaluatedAtUtc",
        description="UTC timestamp for deterministic evidence replay evaluation.",
        examples=["2026-06-21T10:30:00Z"],
    )
    current_source_refs: tuple[SourceRefRequest, ...] = Field(
        ...,
        alias="currentSourceRefs",
        min_length=1,
        description="Current source-owned references to compare with the persisted candidate evidence.",
    )

    @field_validator("evaluated_at_utc")
    @classmethod
    def _evaluated_at_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evaluatedAtUtc must include timezone")
        return value


class CandidateEvidenceReplayResponse(CamelModel):
    candidate_id: str = Field(..., alias="candidateId")
    replay_status: str = Field(..., alias="replayStatus")
    evidence_packet_id: str | None = Field(default=None, alias="evidencePacketId")
    recorded_evidence_hash: str | None = Field(default=None, alias="recordedEvidenceHash")
    current_evidence_hash: str | None = Field(default=None, alias="currentEvidenceHash")
    source_ref_count: int = Field(..., alias="sourceRefCount")
    durable_storage_backed: bool = Field(False, alias="durableStorageBacked")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")
    grants_downstream_authority: bool = Field(False, alias="grantsDownstreamAuthority")

    @classmethod
    def from_replay_result(
        cls,
        result: EvidenceReplayResult,
        *,
        source_ref_count: int,
        durable_storage_backed: bool,
    ) -> "CandidateEvidenceReplayResponse":
        record = result.record
        return cls(
            candidateId=_candidate_id(record),
            replayStatus=result.status.value,
            evidencePacketId=(
                record.candidate.evidence_packet.evidence_packet_id if record is not None else None
            ),
            recordedEvidenceHash=(record.evidence_hash if record is not None else None),
            currentEvidenceHash=result.current_evidence_hash,
            sourceRefCount=source_ref_count,
            durableStorageBacked=durable_storage_backed,
            supportedFeaturePromoted=False,
            grantsDownstreamAuthority=False,
        )


async def replay_idea_candidate_evidence(
    request: ReplayCandidateEvidenceRequest,
    candidate_id: str = Path(..., alias="candidateId"),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
) -> CandidateEvidenceReplayResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
    )
    try:
        require_role_and_capability(caller, _REPLAY_CANDIDATE_EVIDENCE_POLICY)
        command = ReplayCandidateEvidenceCommand(
            candidate_id=candidate_id,
            current_source_refs=tuple(
                source_ref.to_domain() for source_ref in request.current_source_refs
            ),
            evaluated_at_utc=request.evaluated_at_utc,
        )
        result = replay_candidate_evidence(
            command,
            repository=get_idea_repository(),
        )
    except PermissionDeniedError:
        _emit_candidate_evidence_replay_operation_event(
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return problem_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to replay idea candidate evidence.",
        )
    except ValueError:
        _emit_candidate_evidence_replay_operation_event(
            OperationOutcome.INVALID_REQUEST,
            "invalid_request",
        )
        return problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail="candidateId and currentSourceRefs are required for evidence replay.",
        )

    durable_storage_backed = idea_repository_durable_storage_backed(get_idea_repository())
    operation_outcome = _operation_outcome_for_replay_status(result.status)
    _emit_candidate_evidence_replay_operation_event(
        operation_outcome,
        durable_storage_backed=durable_storage_backed,
    )
    if result.status is EvidenceReplayStatus.NOT_FOUND:
        return problem_response(
            status_code=status.HTTP_404_NOT_FOUND,
            code="candidate_not_found",
            title="Candidate not found",
            detail="The idea candidate was not found for evidence replay.",
        )

    return CandidateEvidenceReplayResponse.from_replay_result(
        result,
        source_ref_count=len(request.current_source_refs),
        durable_storage_backed=durable_storage_backed,
    )


def _candidate_id(record: CandidatePersistenceRecord | None) -> str:
    return record.candidate.candidate_id if record is not None else ""


def _operation_outcome_for_replay_status(status_value: EvidenceReplayStatus) -> OperationOutcome:
    if status_value is EvidenceReplayStatus.MATCHED:
        return OperationOutcome.ACCEPTED
    if status_value is EvidenceReplayStatus.HASH_MISMATCH:
        return OperationOutcome.CONFLICT
    if status_value is EvidenceReplayStatus.STALE_SOURCE:
        return OperationOutcome.BLOCKED
    if status_value is EvidenceReplayStatus.EXPIRED:
        return OperationOutcome.INVALID_STATE
    return OperationOutcome.NOT_FOUND


def _emit_candidate_evidence_replay_operation_event(
    outcome: OperationOutcome,
    error_code: str | None = None,
    durable_storage_backed: bool = False,
) -> None:
    emit_foundation_operation_event(
        IdeaOperation.CANDIDATE_EVIDENCE_REPLAY,
        outcome,
        source_authority="lotus-idea",
        error_code=error_code,
        durable_storage_backed=durable_storage_backed,
    )


CANDIDATE_EVIDENCE_REPLAY_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-candidates/{candidateId}/evidence-replay",
    "operation_id": "replayIdeaCandidateEvidence",
    "summary": "Replay source evidence for an idea candidate",
    "description": (
        "Compares operator-supplied current source-owned evidence references with the "
        "persisted evidence hash for an idea candidate and returns matched, stale-source, "
        "hash-mismatch, expired, or not-found posture. This is an RFC-0002 Slice 06, "
        "Slice 10, and Slice 15 internal supportability foundation; it is not live Core "
        "source certification, Gateway proof, Workbench proof, data-product certification, "
        "downstream authority, or supported-feature promotion."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": CandidateEvidenceReplayResponse,
    "tags": ["Idea Candidates"],
    "responses": {
        200: {
            "description": "Evidence replay posture returned.",
            "content": {
                "application/json": {
                    "example": {
                        "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                        "replayStatus": "matched",
                        "evidencePacketId": "iep_high_cash_8d57adbf52f7f5a7",
                        "recordedEvidenceHash": "sha256:evidence-lineage",
                        "currentEvidenceHash": "sha256:evidence-lineage",
                        "sourceRefCount": 4,
                        "durableStorageBacked": False,
                        "supportedFeaturePromoted": False,
                        "grantsDownstreamAuthority": False,
                    }
                }
            },
        },
        **invalid_request_metadata(
            detail="Correct the candidate evidence replay request and retry.",
        ),
        **permission_denied_metadata(
            detail="The caller is not permitted to replay idea candidate evidence.",
            description="Caller lacks evidence replay permission.",
        ),
        **not_found_metadata(
            code="candidate_not_found",
            title="Candidate not found",
            detail="No idea candidate exists for the requested candidateId.",
            description="Candidate was not found.",
        ),
    },
}


def register_candidate_evidence_replay_routes(app: FastAPI) -> None:
    app.post(
        path=CANDIDATE_EVIDENCE_REPLAY_ROUTE["path"],
        operation_id=CANDIDATE_EVIDENCE_REPLAY_ROUTE["operation_id"],
        summary=CANDIDATE_EVIDENCE_REPLAY_ROUTE["summary"],
        description=CANDIDATE_EVIDENCE_REPLAY_ROUTE["description"],
        status_code=CANDIDATE_EVIDENCE_REPLAY_ROUTE["status_code"],
        response_model=CANDIDATE_EVIDENCE_REPLAY_ROUTE["response_model"],
        tags=CANDIDATE_EVIDENCE_REPLAY_ROUTE["tags"],
        responses=CANDIDATE_EVIDENCE_REPLAY_ROUTE["responses"],
    )(replay_idea_candidate_evidence)
