from __future__ import annotations

from fastapi import FastAPI, Header, Path, status
from fastapi.responses import JSONResponse

from app.api.ai_governance import (
    _ai_explanation_durable_write_problem,
    _ai_explanation_exception_response,
    _ai_explanation_result_problem,
    _operation_outcome_from_ai_result,
    _successful_ai_explanation_response,
)
from app.api.ai_governance_models import (
    AIExplanationGenerationRequest,
    AIExplanationGenerationResponse,
)
from app.api.caller_headers import TRUSTED_CALLER_CONTEXT_HEADER, caller_context_from_headers
from app.api.durable_write_guard import durable_repository_write_unavailable_metadata
from app.api.examples.ai_explanation import build_ai_explanation_generation_openapi_examples
from app.api.idempotency import validate_idempotency_key
from app.api.problem_details import (
    conflict_metadata,
    invalid_request_metadata,
    merged_problem_response_metadata,
    not_found_metadata,
    permission_denied_metadata,
)
from app.api.route_metadata import RouteMetadata
from app.api.runtime_dependencies import (
    get_idea_repository,
    get_lotus_ai_workflow_runtime,
    idea_repository_durable_storage_backed,
    load_runtime_settings,
)
from app.application.ai_governance import AIExplanationEntitlementDenied
from app.application.lotus_ai_idea_explanation_generation import (
    GenerateAIExplanationCommand,
    GeneratedAIExplanationOutcome,
    generate_ai_explanation_to_repository,
)
from app.domain import (
    InvalidAIExplanationRequest,
    InvalidAIWorkflowOutput,
    InvalidAIWorkflowPack,
)
from app.domain.ai_execution_provenance import UntrustedAIWorkflowOutput
from app.domain.ai_metadata_policy import InvalidAIMetadataEnvelope
from app.observability import (
    IdeaOperation,
    OperationOutcome,
    emit_foundation_operation_event,
    observe_ai_explanation_generation_outcome,
    observe_ai_explanation_generation_requested,
)
from app.security.caller_context import CallerContext, PermissionDeniedError


_AI_EXPLANATION_GENERATION_CAPABILITY = "idea.ai-explanation.generate"


async def generate_ai_explanation(
    request: AIExplanationGenerationRequest,
    candidate_id: str = Path(..., alias="candidateId"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
    x_caller_tenant_ids: str | None = Header(default=None, alias="X-Caller-Tenant-Ids"),
    x_lotus_trusted_caller_context: str | None = Header(
        default=None,
        alias=TRUSTED_CALLER_CONTEXT_HEADER,
    ),
) -> AIExplanationGenerationResponse | JSONResponse:
    try:
        caller = caller_context_from_headers(
            subject=x_caller_subject,
            roles=x_caller_roles,
            capabilities=x_caller_capabilities,
            tenant_ids=x_caller_tenant_ids,
            trusted_caller_context=x_lotus_trusted_caller_context,
        )
        _require_generation_caller(caller)
        validate_idempotency_key(idempotency_key)
        command = GenerateAIExplanationCommand(
            candidate_id=candidate_id,
            request_id=request.request_id,
            actor_subject=caller.subject,
            purpose=request.purpose,
            requested_at_utc=request.requested_at_utc,
            idempotency_key=idempotency_key,
            caller_tenant_ids=caller.entitlement_scope.tenant_ids,
        )
        repository = get_idea_repository()
        durable_storage_backed = idea_repository_durable_storage_backed(repository)
        configuration_problem = _ai_explanation_durable_write_problem(
            repository,
            durable_storage_backed=durable_storage_backed,
        )
        if configuration_problem is not None:
            return configuration_problem
        observe_ai_explanation_generation_requested(request.purpose)
        fixture_allowed = (
            load_runtime_settings().runtime_profile.allows_unattested_ai_workflow_fixture
        )
        try:
            runtime = get_lotus_ai_workflow_runtime() if fixture_allowed else None
        except RuntimeError:
            runtime = None
        outcome = await generate_ai_explanation_to_repository(
            command,
            repository=repository,
            runtime=runtime,
            unattested_workflow_fixture_allowed=fixture_allowed,
        )
    except (
        PermissionDeniedError,
        AIExplanationEntitlementDenied,
        InvalidAIWorkflowOutput,
        UntrustedAIWorkflowOutput,
        InvalidAIMetadataEnvelope,
        InvalidAIWorkflowPack,
        InvalidAIExplanationRequest,
        ValueError,
    ) as exc:
        return _ai_explanation_exception_response(exc)

    _emit_generation_operation_event(outcome, purpose=request.purpose.value)
    observe_ai_explanation_generation_outcome(request.purpose, outcome.status)
    problem = _ai_explanation_result_problem(outcome.result)
    if problem is not None:
        return problem
    explanation = _successful_ai_explanation_response(
        outcome.result,
        durable_storage_backed=bool(getattr(repository, "durable_storage_backed", False)),
        runtime_execution_confirmed=outcome.runtime_execution_confirmed,
    )
    return AIExplanationGenerationResponse.from_outcome(outcome, explanation=explanation)


def _require_generation_caller(caller: CallerContext) -> None:
    if not caller.has_capability(_AI_EXPLANATION_GENERATION_CAPABILITY):
        raise PermissionDeniedError(_AI_EXPLANATION_GENERATION_CAPABILITY)


def _emit_generation_operation_event(
    outcome: GeneratedAIExplanationOutcome,
    *,
    purpose: str,
) -> None:
    emit_foundation_operation_event(
        IdeaOperation.AI_EXPLANATION,
        (
            _operation_outcome_from_ai_result(outcome.result.explanation_result)
            if outcome.result.explanation_result is not None
            else OperationOutcome.NOT_FOUND
        ),
        source_authority="lotus-idea",
        attributes={
            "ai_explanation_flow": "generation",
            "ai_generation_purpose": purpose,
            "ai_generation_disposition": outcome.disposition.value,
        },
    )


AI_EXPLANATION_GENERATION_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-candidates/{candidateId}/ai-explanations",
    "operation_id": "generateIdeaAIExplanation",
    "summary": "Generate an idea AI explanation",
    "description": (
        "Generates a governed AI explanation for a persisted idea candidate through the "
        "registered Lotus AI workflow pack. The server derives redacted evidence from candidate "
        "state, forwards a stable non-sensitive owner idempotency key, retains the exact owner "
        "run identity, and applies the existing claim-grounding, forbidden-action, redaction, "
        "lineage, and replay controls. EXPLANATION_SERVED means generated output passed the "
        "Idea-owned evaluation. Runtime, owner-conflict, changed-evidence, non-accepted-output, "
        "and production-like attestation gaps return EXPLANATION_UNAVAILABLE with deterministic "
        "fallback evidence. "
        "The route never changes eligibility, ranking, candidate lifecycle, or downstream "
        "authority and does not promote a supported feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": AIExplanationGenerationResponse,
    "tags": ["Idea AI Governance"],
    "responses": {
        200: {
            "description": "Generated output was served or explicitly unavailable.",
            "content": {
                "application/json": {
                    "examples": build_ai_explanation_generation_openapi_examples(),
                }
            },
        },
        **merged_problem_response_metadata(
            status_code=status.HTTP_400_BAD_REQUEST,
            description="AI explanation generation request validation failed.",
            responses=(
                invalid_request_metadata(
                    detail=(
                        "Correct the AI explanation generation request or Idempotency-Key "
                        "and retry."
                    ),
                ),
            ),
        ),
        **permission_denied_metadata(
            detail="The caller is not permitted to generate idea AI explanations.",
            description="Caller lacks AI explanation generation permission.",
        ),
        **not_found_metadata(
            code="candidate_not_found",
            title="Candidate not found",
            detail="No idea candidate exists for the requested candidateId.",
            description="Candidate was not found.",
        ),
        **conflict_metadata(
            code="idempotency_conflict",
            title="AI explanation request conflict",
            detail=(
                "The requested AI explanation conflicts with the candidate state, existing "
                "request lineage, or Idempotency-Key fingerprint."
            ),
            description="AI explanation generation request conflicts with governed state.",
        ),
        **durable_repository_write_unavailable_metadata(),
    },
}


def register_ai_explanation_generation_routes(app: FastAPI) -> None:
    app.post(
        path=AI_EXPLANATION_GENERATION_ROUTE["path"],
        operation_id=AI_EXPLANATION_GENERATION_ROUTE["operation_id"],
        summary=AI_EXPLANATION_GENERATION_ROUTE["summary"],
        description=AI_EXPLANATION_GENERATION_ROUTE["description"],
        status_code=AI_EXPLANATION_GENERATION_ROUTE["status_code"],
        response_model=AI_EXPLANATION_GENERATION_ROUTE["response_model"],
        tags=AI_EXPLANATION_GENERATION_ROUTE["tags"],
        responses=AI_EXPLANATION_GENERATION_ROUTE["responses"],
    )(generate_ai_explanation)


__all__ = [
    "AI_EXPLANATION_GENERATION_ROUTE",
    "generate_ai_explanation",
    "register_ai_explanation_generation_routes",
]
