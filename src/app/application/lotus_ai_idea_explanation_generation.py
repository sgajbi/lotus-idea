from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Mapping

from app.application.ai_governance import (
    AIExplanationEntitlementDenied,
    AIExplanationEvaluationDecision,
    AIExplanationWorkflowResult,
    EvaluateAIExplanationToRepositoryCommand,
    evaluate_ai_explanation_to_repository,
)
from app.application.candidate_lookup import candidate_record_by_id
from app.application.lotus_ai_idea_explanation_output import (
    map_lotus_ai_idea_workflow_output,
)
from app.application.lotus_ai_idea_explanation_request import (
    build_lotus_ai_idea_explanation_input,
)
from app.domain.ai_execution_provenance import AIWorkflowOutputTrustPolicy
from app.domain.ai_governance import (
    GOVERNED_IDEA_EXPLANATION_WORKFLOW_PACK,
    AIExplanationCommand,
    AIExplanationPosture,
    AIFallbackReason,
    AIWorkflowOutput,
    AIWorkflowPackRef,
    AIWorkflowPurpose,
    build_ai_explanation_request,
)
from app.domain.ideas import IdeaCandidate
from app.domain.lotus_ai_execution_digest import LotusAIExecutionOutputContent
from app.domain.persistence_models import CandidatePersistenceRecord
from app.ports.lotus_ai_runtime import (
    InvalidLotusAIWorkflowRuntimeResponse,
    LotusAIWorkflowRuntime,
    LotusAIWorkflowRuntimeUnavailable,
)
from app.ports.idea_repository import AIExplanationRepository


LOTUS_AI_CALLER_APP = "lotus-idea"
GENERATION_WORKFLOW_SURFACE = "idea-explanation-evidence"

# The lotus-ai input builder maps requested outputs for exactly these purposes;
# MISSING_EVIDENCE_CHECK stays an evaluate-only purpose until it declares outputs.
GENERATION_SUPPORTED_PURPOSES: frozenset[AIWorkflowPurpose] = frozenset(
    {
        AIWorkflowPurpose.UNSUPPORTED_CLAIM_VERIFICATION,
        AIWorkflowPurpose.ADVISOR_RATIONALE_DRAFT,
        AIWorkflowPurpose.MEETING_PREPARATION_DRAFT,
    }
)


class AIExplanationGenerationDisposition(StrEnum):
    EXECUTED = "executed"
    OUTPUT_NOT_ACCEPTED = "output_not_accepted"
    CANDIDATE_EVIDENCE_CHANGED = "candidate_evidence_changed"
    ATTESTED_EXECUTION_REQUIRED = "attested_execution_required"
    RUNTIME_UNAVAILABLE = "runtime_unavailable"
    INVALID_RUNTIME_RESPONSE = "invalid_runtime_response"
    OWNER_IDEMPOTENCY_CONFLICT = "owner_idempotency_conflict"


class AIExplanationGenerationStatus(StrEnum):
    EXPLANATION_SERVED = "EXPLANATION_SERVED"
    EXPLANATION_UNAVAILABLE = "EXPLANATION_UNAVAILABLE"


class UnsupportedAIGenerationPurpose(ValueError):
    def __init__(self, purpose: AIWorkflowPurpose) -> None:
        super().__init__(f"AI explanation generation does not support purpose {purpose.value}")


@dataclass(frozen=True)
class GenerateAIExplanationCommand:
    candidate_id: str
    request_id: str
    actor_subject: str
    purpose: AIWorkflowPurpose
    requested_at_utc: datetime
    idempotency_key: str
    caller_tenant_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.purpose not in GENERATION_SUPPORTED_PURPOSES:
            raise UnsupportedAIGenerationPurpose(self.purpose)


@dataclass(frozen=True)
class GeneratedAIExplanationOutcome:
    disposition: AIExplanationGenerationDisposition
    result: AIExplanationWorkflowResult
    lotus_ai_run_id: str | None = None
    runtime_execution_confirmed: bool = False

    @property
    def status(self) -> AIExplanationGenerationStatus:
        if self.disposition is AIExplanationGenerationDisposition.EXECUTED:
            return AIExplanationGenerationStatus.EXPLANATION_SERVED
        return AIExplanationGenerationStatus.EXPLANATION_UNAVAILABLE


async def generate_ai_explanation_to_repository(
    command: GenerateAIExplanationCommand,
    *,
    repository: AIExplanationRepository,
    runtime: LotusAIWorkflowRuntime | None,
    unattested_workflow_fixture_allowed: bool,
) -> GeneratedAIExplanationOutcome:
    """Execute the governed lotus-ai explanation pack and evaluate its output in-process.

    The generated output receives exactly the acceptance an external producer's
    output would get: the existing evaluate pipeline verifies grounding, action
    policy, and lineage. When execution cannot yield acceptable output — the
    profile requires attested provenance (unobtainable under the current stub
    posture), the runtime is unreachable, or its response is invalid — the
    evaluation runs the deterministic fallback instead, so nothing fabricated
    and nothing unattested is ever served.
    """

    explanation_command = AIExplanationCommand(
        request_id=command.request_id,
        actor_subject=command.actor_subject,
        workflow_pack=_governed_workflow_pack_ref(command.purpose),
        approved_metadata={},
        requested_at_utc=command.requested_at_utc,
    )

    record = candidate_record_by_id(repository, command.candidate_id)
    if record is not None and not _caller_may_read_candidate(record, command):
        raise AIExplanationEntitlementDenied(command.candidate_id)

    disposition = AIExplanationGenerationDisposition.ATTESTED_EXECUTION_REQUIRED
    workflow_output: AIWorkflowOutput | None = None
    lotus_ai_run_id: str | None = None
    runtime_execution_confirmed = False
    fallback_reason = AIFallbackReason.WORKFLOW_NOT_APPROVED
    if unattested_workflow_fixture_allowed and record is not None:
        if runtime is None:
            disposition = AIExplanationGenerationDisposition.RUNTIME_UNAVAILABLE
            fallback_reason = AIFallbackReason.AI_UNAVAILABLE
        else:
            (
                disposition,
                workflow_output,
                fallback_reason,
                lotus_ai_run_id,
                runtime_execution_confirmed,
            ) = await _execute_workflow_pack(
                command,
                explanation_command=explanation_command,
                record_candidate=record.candidate,
                runtime=runtime,
            )
            current_record = candidate_record_by_id(repository, command.candidate_id)
            if workflow_output is not None and not _same_candidate_evidence_revision(
                record,
                current_record,
            ):
                disposition = AIExplanationGenerationDisposition.CANDIDATE_EVIDENCE_CHANGED
                workflow_output = None
                fallback_reason = AIFallbackReason.UNSUPPORTED_EVIDENCE

    evaluate_command = EvaluateAIExplanationToRepositoryCommand(
        candidate_id=command.candidate_id,
        explanation=explanation_command,
        fallback_reason=fallback_reason,
        idempotency_key=command.idempotency_key,
        idempotency_payload={
            "candidateId": command.candidate_id,
            "candidateEvidenceHash": record.evidence_hash if record is not None else None,
            "candidateMaterialVersion": (
                record.candidate.identity.material_version if record is not None else None
            ),
            "candidateEvidenceVersion": (
                record.candidate.identity.evidence_version if record is not None else None
            ),
            "generation": {
                "requestId": command.request_id,
                "purpose": command.purpose.value,
                "requestedAtUtc": command.requested_at_utc.isoformat(),
                "workflowPackVersion": GOVERNED_IDEA_EXPLANATION_WORKFLOW_PACK.workflow_pack_version,
            },
        },
        workflow_output=workflow_output,
        caller_tenant_ids=command.caller_tenant_ids,
        workflow_output_trust_policy=(
            AIWorkflowOutputTrustPolicy.UNATTESTED_LOCAL_TEST_FIXTURE_ALLOWED
            if unattested_workflow_fixture_allowed
            else AIWorkflowOutputTrustPolicy.LOTUS_AI_ATTESTATION_REQUIRED
        ),
    )
    result = evaluate_ai_explanation_to_repository(evaluate_command, repository=repository)
    if disposition is AIExplanationGenerationDisposition.EXECUTED and (
        result.explanation_result is None
        or result.explanation_result.posture is not AIExplanationPosture.READY_FOR_ADVISOR_REVIEW
        or result.decision is not AIExplanationEvaluationDecision.ACCEPTED
    ):
        disposition = AIExplanationGenerationDisposition.OUTPUT_NOT_ACCEPTED
    return GeneratedAIExplanationOutcome(
        disposition=disposition,
        result=result,
        lotus_ai_run_id=lotus_ai_run_id,
        runtime_execution_confirmed=runtime_execution_confirmed,
    )


def _governed_workflow_pack_ref(purpose: AIWorkflowPurpose) -> AIWorkflowPackRef:
    contract = GOVERNED_IDEA_EXPLANATION_WORKFLOW_PACK
    return AIWorkflowPackRef(
        workflow_pack_id=contract.request_workflow_pack_id,
        workflow_pack_version=contract.workflow_pack_version,
        purpose=purpose,
        evaluation_ref=contract.evaluation_ref,
    )


def _caller_may_read_candidate(
    record: CandidatePersistenceRecord,
    command: GenerateAIExplanationCommand,
) -> bool:
    candidate_scope = record.candidate.access_scope
    return candidate_scope is None or candidate_scope.tenant_id in command.caller_tenant_ids


def _same_candidate_evidence_revision(
    expected: CandidatePersistenceRecord,
    current: CandidatePersistenceRecord | None,
) -> bool:
    if current is None:
        return False
    expected_candidate = expected.candidate
    current_candidate = current.candidate
    return (
        current.evidence_hash == expected.evidence_hash
        and current_candidate.identity.business_identity_id
        == expected_candidate.identity.business_identity_id
        and current_candidate.identity.material_version
        == expected_candidate.identity.material_version
        and current_candidate.identity.evidence_version
        == expected_candidate.identity.evidence_version
        and current_candidate.evidence_packet.evidence_packet_id
        == expected_candidate.evidence_packet.evidence_packet_id
    )


async def _execute_workflow_pack(
    command: GenerateAIExplanationCommand,
    *,
    explanation_command: AIExplanationCommand,
    record_candidate: IdeaCandidate,
    runtime: LotusAIWorkflowRuntime,
) -> tuple[
    AIExplanationGenerationDisposition,
    AIWorkflowOutput | None,
    AIFallbackReason,
    str | None,
    bool,
]:
    # Candidate-state and purpose errors are caller errors and must propagate;
    # only runtime transport and response-shape failures degrade to fallback.
    explanation_request = build_ai_explanation_request(record_candidate, explanation_command)
    input_evidence = build_lotus_ai_idea_explanation_input(explanation_request)
    envelope = _execution_envelope(
        command,
        context_summary=input_evidence.context_summary,
        context_payload=input_evidence.context_payload,
        source_refs=input_evidence.source_refs,
        task_id=input_evidence.task_id,
        expected_output_label=input_evidence.expected_output_label,
        tenant_id=_candidate_tenant_id(record_candidate),
    )
    lotus_ai_run_id: str | None = None
    run_identity_confirmed = False
    try:
        response = await runtime.execute_workflow_pack(envelope, caller_app=LOTUS_AI_CALLER_APP)
        lotus_ai_run_id = _workflow_pack_run_id(response)
        run_identity_confirmed = True
        workflow_output = map_lotus_ai_idea_workflow_output(
            _execution_output_content(response),
            request_id=explanation_request.request_id,
            workflow_pack_id=explanation_request.workflow_pack.workflow_pack_id,
            workflow_pack_version=explanation_request.workflow_pack.workflow_pack_version,
            verifier_ran_at_utc=datetime.now(UTC),
        )
    except LotusAIWorkflowRuntimeUnavailable:
        return (
            AIExplanationGenerationDisposition.RUNTIME_UNAVAILABLE,
            None,
            AIFallbackReason.AI_UNAVAILABLE,
            None,
            False,
        )
    except InvalidLotusAIWorkflowRuntimeResponse as exc:
        return (
            (
                AIExplanationGenerationDisposition.OWNER_IDEMPOTENCY_CONFLICT
                if exc.status_code == 409
                else AIExplanationGenerationDisposition.INVALID_RUNTIME_RESPONSE
            ),
            None,
            AIFallbackReason.AI_UNAVAILABLE,
            lotus_ai_run_id,
            run_identity_confirmed,
        )
    except ValueError:
        return (
            AIExplanationGenerationDisposition.INVALID_RUNTIME_RESPONSE,
            None,
            AIFallbackReason.AI_UNAVAILABLE,
            lotus_ai_run_id,
            run_identity_confirmed,
        )
    return (
        AIExplanationGenerationDisposition.EXECUTED,
        workflow_output,
        AIFallbackReason.AI_UNAVAILABLE,
        lotus_ai_run_id,
        True,
    )


def _execution_envelope(
    command: GenerateAIExplanationCommand,
    *,
    context_summary: str,
    context_payload: Mapping[str, object],
    source_refs: tuple[str, ...],
    task_id: str,
    expected_output_label: str | None,
    tenant_id: str | None,
) -> dict[str, object]:
    contract = GOVERNED_IDEA_EXPLANATION_WORKFLOW_PACK
    pack_id, _, _ = contract.proof_workflow_pack_id.partition("@")
    caller: dict[str, object] = {
        "caller_app": LOTUS_AI_CALLER_APP,
        "correlation_id": f"lotus-idea-explanation-{command.request_id}",
    }
    if tenant_id:
        caller["tenant_id"] = tenant_id
    return {
        "pack_id": pack_id,
        "version": contract.workflow_pack_version,
        "environment": "DEVELOPMENT",
        "idempotency_key": _lotus_ai_owner_idempotency_key(command.idempotency_key),
        "caller_identity_class": "INTERNAL_SERVICE",
        "workflow_surface": GENERATION_WORKFLOW_SURFACE,
        "task_request": {
            "task_id": task_id,
            "input_mode": "STRUCTURED_CONTEXT",
            "caller": caller,
            "context": {
                "summary": context_summary,
                "payload": dict(context_payload),
                "source_refs": list(source_refs),
            },
            "expected_output_label": expected_output_label,
        },
    }


def _lotus_ai_owner_idempotency_key(idea_idempotency_key: str) -> str:
    material = f"lotus-idea:ai-explanation-generation:v1:{idea_idempotency_key}"
    return f"idea-explanation-{hashlib.sha256(material.encode('utf-8')).hexdigest()}"


def _candidate_tenant_id(record_candidate: IdeaCandidate) -> str | None:
    scope = record_candidate.access_scope
    return scope.tenant_id if scope is not None else None


def _execution_output_content(response: Mapping[str, object]) -> LotusAIExecutionOutputContent:
    execution = _object(response, "execution")
    result = _object(execution, "result")
    return LotusAIExecutionOutputContent(
        status=_text(execution, "status"),
        output_label=_text(execution, "output_label"),
        message=_text(result, "message"),
        structured_output=_object(result, "structured_output"),
    )


def _workflow_pack_run_id(response: Mapping[str, object]) -> str:
    return _text(_object(response, "workflow_pack_run"), "run_id")


def _object(mapping: Mapping[str, object], field_name: str) -> Mapping[str, object]:
    value = mapping.get(field_name)
    if not isinstance(value, Mapping):
        raise InvalidLotusAIWorkflowRuntimeResponse(
            f"lotus-ai execution response field `{field_name}` must be an object"
        )
    return value


def _text(mapping: Mapping[str, object], field_name: str) -> str:
    value = mapping.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise InvalidLotusAIWorkflowRuntimeResponse(
            f"lotus-ai execution response field `{field_name}` must be non-empty text"
        )
    return value


__all__ = [
    "AIExplanationGenerationDisposition",
    "AIExplanationGenerationStatus",
    "GENERATION_SUPPORTED_PURPOSES",
    "GenerateAIExplanationCommand",
    "GeneratedAIExplanationOutcome",
    "UnsupportedAIGenerationPurpose",
    "generate_ai_explanation_to_repository",
]
