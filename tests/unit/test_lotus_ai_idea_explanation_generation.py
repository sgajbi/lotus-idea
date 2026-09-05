from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace
from datetime import UTC, datetime
from typing import cast

import pytest

from app.application.ai_governance import AIExplanationEvaluationDecision
from app.application.lotus_ai_idea_explanation_generation import (
    AIExplanationGenerationDisposition,
    GenerateAIExplanationCommand,
    UnsupportedAIGenerationPurpose,
    generate_ai_explanation_to_repository,
)
from app.domain import AIExplanationPosture, InMemoryIdeaRepository
from app.domain.ai_governance import AIFallbackReason, AIWorkflowPurpose
from app.domain.persistence_models import CandidatePersistenceRecord
from app.ports.lotus_ai_runtime import (
    InvalidLotusAIWorkflowRuntimeResponse,
    LotusAIWorkflowRuntimeUnavailable,
)
from tests.unit.test_ai_governance import EVALUATED_AT, candidate

REQUESTED_AT = datetime(2026, 6, 21, 11, 0, tzinfo=UTC)

_STUB_MESSAGE = (
    "Drafted a review-gated Lotus Idea explanation from redacted evidence packet "
    "iep_ai_test for candidate idea-ai-001."
)


def _enriched_stub_response() -> dict[str, object]:
    """The real lotus-ai idea-explanation stub shape (see lotus-ai#321 cross-repo proof)."""

    return {
        "execution": {
            "status": "COMPLETED",
            "output_label": "EXPLANATION_ONLY",
            "result": {
                "message": _STUB_MESSAGE,
                "structured_output": {
                    "workflow_pack_family": "idea_explanation",
                    "human_review_required": True,
                    "client_ready_publication": "BLOCKED",
                    "downstream_authority": "BLOCKED",
                    "idea_workflow_output": {
                        "output_id": "idea-explanation-output-gen-request-001",
                        "explanation_text": _STUB_MESSAGE,
                        "claims": [
                            {
                                "claim_id": "reason-01-high_cash_ratio",
                                "claim_text": (
                                    "Candidate idea-ai-001 was surfaced with reason code "
                                    "HIGH_CASH_RATIO under scoring policy "
                                    "idea-deterministic-ranking-v1."
                                ),
                                "source_product_ids": [
                                    "lotus-core:PortfolioStateSnapshot:v1",
                                    "lotus-core:HoldingsAsOf:v1",
                                ],
                            }
                        ],
                        "proposed_actions": [
                            {
                                "action_type": "advisor_review",
                                "action_label": "Review the evidence",
                            }
                        ],
                    },
                },
            },
        },
        "workflow_pack_run": {"run_id": "wpr_generation_test_001"},
    }


class FakeRuntime:
    def __init__(
        self,
        response: Mapping[str, object] | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.response = response
        self.error = error
        self.requests: list[tuple[Mapping[str, object], str]] = []

    async def execute_workflow_pack(
        self,
        request: Mapping[str, object],
        *,
        caller_app: str,
    ) -> Mapping[str, object]:
        self.requests.append((request, caller_app))
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response

    async def get_run_attestation(self, run_id: str) -> Mapping[str, object]:
        raise AssertionError(f"generation S2 must not fetch attestation for {run_id}")


class EvidenceAdvancingRepository(InMemoryIdeaRepository):
    expose_changed_evidence = False

    def candidate_record_by_id(
        self,
        candidate_id: str,
    ) -> CandidatePersistenceRecord | None:
        record = cast(
            CandidatePersistenceRecord | None,
            super().candidate_record_by_id(candidate_id),
        )
        if record is None or not self.expose_changed_evidence:
            return record
        return replace(record, evidence_hash=f"sha256:{'f' * 64}")


class EvidenceAdvancingRuntime(FakeRuntime):
    def __init__(self, repository: EvidenceAdvancingRepository) -> None:
        super().__init__(_enriched_stub_response())
        self._repository = repository

    async def execute_workflow_pack(
        self,
        request: Mapping[str, object],
        *,
        caller_app: str,
    ) -> Mapping[str, object]:
        response = await super().execute_workflow_pack(request, caller_app=caller_app)
        self._repository.expose_changed_evidence = True
        return response


def _remove_execution(response: dict[str, object]) -> None:
    response.pop("execution")


def _remove_execution_result(response: dict[str, object]) -> None:
    execution = response["execution"]
    assert isinstance(execution, dict)
    execution.pop("result")


def _blank_workflow_pack_run_id(response: dict[str, object]) -> None:
    workflow_pack_run = response["workflow_pack_run"]
    assert isinstance(workflow_pack_run, dict)
    workflow_pack_run["run_id"] = " "


def _repository_with_candidate() -> InMemoryIdeaRepository:
    repository = InMemoryIdeaRepository()
    persisted = repository.persist_candidate(
        candidate(),
        idempotency_key="signal-ingestion:generation-test:001",
        payload={"candidate_id": "idea-ai-001"},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    assert persisted.record is not None, persisted.decision
    return repository


def _command(
    *,
    candidate_id: str = "idea-ai-001",
    purpose: AIWorkflowPurpose = AIWorkflowPurpose.ADVISOR_RATIONALE_DRAFT,
    tenant_ids: tuple[str, ...] = ("tenant-ai-test",),
) -> GenerateAIExplanationCommand:
    return GenerateAIExplanationCommand(
        candidate_id=candidate_id,
        request_id="gen-request-001",
        actor_subject="advisor-001",
        purpose=purpose,
        requested_at_utc=REQUESTED_AT,
        idempotency_key="ai-explanation:generation:001",
        caller_tenant_ids=tenant_ids,
    )


@pytest.mark.asyncio
async def test_generation_executes_pack_and_accepts_grounded_output() -> None:
    runtime = FakeRuntime(_enriched_stub_response())

    outcome = await generate_ai_explanation_to_repository(
        _command(),
        repository=_repository_with_candidate(),
        runtime=runtime,
        unattested_workflow_fixture_allowed=True,
    )

    assert outcome.disposition is AIExplanationGenerationDisposition.EXECUTED
    assert outcome.lotus_ai_run_id == "wpr_generation_test_001"
    assert outcome.runtime_execution_confirmed is True
    assert outcome.result.decision is AIExplanationEvaluationDecision.ACCEPTED
    assert outcome.result.explanation_result is not None
    assert (
        outcome.result.explanation_result.posture is AIExplanationPosture.READY_FOR_ADVISOR_REVIEW
    )
    request, caller_app = runtime.requests[0]
    assert caller_app == "lotus-idea"
    assert request["pack_id"] == "idea_explanation.pack"
    assert request["workflow_surface"] == "idea-explanation-evidence"
    owner_key = request["idempotency_key"]
    assert isinstance(owner_key, str)
    assert owner_key.startswith("idea-explanation-")
    assert len(owner_key) == len("idea-explanation-") + 64
    assert "ai-explanation:generation:001" not in owner_key
    task_request = request["task_request"]
    assert isinstance(task_request, dict)
    assert task_request["task_id"] == "explain.v1"
    assert task_request["expected_output_label"] == "EXPLANATION_ONLY"
    caller = task_request["caller"]
    assert isinstance(caller, dict)
    assert caller["tenant_id"] == "tenant-ai-test"


@pytest.mark.asyncio
async def test_generation_never_executes_when_attested_provenance_is_required() -> None:
    runtime = FakeRuntime(error=AssertionError("must not execute"))

    outcome = await generate_ai_explanation_to_repository(
        _command(),
        repository=_repository_with_candidate(),
        runtime=None,
        unattested_workflow_fixture_allowed=False,
    )

    assert outcome.disposition is (AIExplanationGenerationDisposition.ATTESTED_EXECUTION_REQUIRED)
    assert outcome.result.explanation_result is not None
    assert outcome.result.explanation_result.posture is AIExplanationPosture.FALLBACK_USED
    assert (
        outcome.result.explanation_result.fallback_reason is AIFallbackReason.WORKFLOW_NOT_APPROVED
    )
    assert runtime.requests == []


@pytest.mark.asyncio
async def test_generation_degrades_to_deterministic_fallback_when_runtime_unavailable() -> None:
    runtime = FakeRuntime(
        error=LotusAIWorkflowRuntimeUnavailable("lotus-ai workflow runtime is unavailable")
    )

    outcome = await generate_ai_explanation_to_repository(
        _command(),
        repository=_repository_with_candidate(),
        runtime=runtime,
        unattested_workflow_fixture_allowed=True,
    )

    assert outcome.disposition is AIExplanationGenerationDisposition.RUNTIME_UNAVAILABLE
    assert outcome.result.explanation_result is not None
    assert outcome.result.explanation_result.posture is AIExplanationPosture.FALLBACK_USED
    assert outcome.result.explanation_result.fallback_reason is AIFallbackReason.AI_UNAVAILABLE


@pytest.mark.parametrize(
    "mutate",
    [
        _remove_execution,
        _remove_execution_result,
        _blank_workflow_pack_run_id,
    ],
)
@pytest.mark.asyncio
async def test_generation_degrades_when_runtime_response_is_malformed(
    mutate: Callable[[dict[str, object]], None],
) -> None:
    response = _enriched_stub_response()
    mutate(response)
    runtime = FakeRuntime(response)

    outcome = await generate_ai_explanation_to_repository(
        _command(),
        repository=_repository_with_candidate(),
        runtime=runtime,
        unattested_workflow_fixture_allowed=True,
    )

    assert outcome.disposition is AIExplanationGenerationDisposition.INVALID_RUNTIME_RESPONSE
    assert outcome.result.explanation_result is not None
    assert outcome.result.explanation_result.posture is AIExplanationPosture.FALLBACK_USED


@pytest.mark.asyncio
async def test_generation_degrades_when_output_omits_idea_workflow_output() -> None:
    response = _enriched_stub_response()
    execution = response["execution"]
    assert isinstance(execution, dict)
    result = execution["result"]
    assert isinstance(result, dict)
    structured = result["structured_output"]
    assert isinstance(structured, dict)
    structured.pop("idea_workflow_output")

    outcome = await generate_ai_explanation_to_repository(
        _command(),
        repository=_repository_with_candidate(),
        runtime=FakeRuntime(response),
        unattested_workflow_fixture_allowed=True,
    )

    assert outcome.disposition is AIExplanationGenerationDisposition.INVALID_RUNTIME_RESPONSE
    assert outcome.result.explanation_result is not None
    assert outcome.result.explanation_result.posture is AIExplanationPosture.FALLBACK_USED


@pytest.mark.asyncio
async def test_generation_exposes_non_accepted_output_without_serving_it() -> None:
    response = _enriched_stub_response()
    execution = response["execution"]
    assert isinstance(execution, dict)
    result = execution["result"]
    assert isinstance(result, dict)
    structured = result["structured_output"]
    assert isinstance(structured, dict)
    workflow_output = structured["idea_workflow_output"]
    assert isinstance(workflow_output, dict)
    proposed_actions = workflow_output["proposed_actions"]
    assert isinstance(proposed_actions, list)
    action = proposed_actions[0]
    assert isinstance(action, dict)
    action["action_type"] = "final_investment_recommendation"

    outcome = await generate_ai_explanation_to_repository(
        _command(),
        repository=_repository_with_candidate(),
        runtime=FakeRuntime(response),
        unattested_workflow_fixture_allowed=True,
    )

    assert outcome.disposition is AIExplanationGenerationDisposition.OUTPUT_NOT_ACCEPTED
    assert outcome.status.value == "EXPLANATION_UNAVAILABLE"
    assert outcome.lotus_ai_run_id == "wpr_generation_test_001"
    assert outcome.runtime_execution_confirmed is True
    assert outcome.result.explanation_result is not None
    assert (
        outcome.result.explanation_result.posture is AIExplanationPosture.BLOCKED_FORBIDDEN_ACTION
    )
    assert outcome.result.explanation_result.explanation_text.startswith(
        "AI explanation was blocked"
    )


def test_generation_rejects_unsupported_purpose() -> None:
    with pytest.raises(UnsupportedAIGenerationPurpose):
        _command(purpose=AIWorkflowPurpose.MISSING_EVIDENCE_CHECK)


@pytest.mark.asyncio
async def test_generation_reports_unavailable_when_local_runtime_is_not_configured() -> None:
    outcome = await generate_ai_explanation_to_repository(
        _command(),
        repository=_repository_with_candidate(),
        runtime=None,
        unattested_workflow_fixture_allowed=True,
    )

    assert outcome.disposition is AIExplanationGenerationDisposition.RUNTIME_UNAVAILABLE
    assert outcome.status.value == "EXPLANATION_UNAVAILABLE"
    assert outcome.lotus_ai_run_id is None
    assert outcome.runtime_execution_confirmed is False
    assert outcome.result.explanation_result is not None
    assert outcome.result.explanation_result.fallback_used is True


@pytest.mark.asyncio
async def test_generation_preserves_owner_idempotency_conflict_without_retry() -> None:
    runtime = FakeRuntime(
        error=InvalidLotusAIWorkflowRuntimeResponse(
            "lotus-ai workflow execution returned HTTP 409",
            status_code=409,
        )
    )

    outcome = await generate_ai_explanation_to_repository(
        _command(),
        repository=_repository_with_candidate(),
        runtime=runtime,
        unattested_workflow_fixture_allowed=True,
    )

    assert outcome.disposition is (AIExplanationGenerationDisposition.OWNER_IDEMPOTENCY_CONFLICT)
    assert outcome.status.value == "EXPLANATION_UNAVAILABLE"
    assert outcome.runtime_execution_confirmed is False
    assert len(runtime.requests) == 1


@pytest.mark.asyncio
async def test_generation_reuses_stable_owner_key_and_local_lineage_on_exact_replay() -> None:
    repository = _repository_with_candidate()
    runtime = FakeRuntime(_enriched_stub_response())

    first = await generate_ai_explanation_to_repository(
        _command(),
        repository=repository,
        runtime=runtime,
        unattested_workflow_fixture_allowed=True,
    )
    replay = await generate_ai_explanation_to_repository(
        _command(),
        repository=repository,
        runtime=runtime,
        unattested_workflow_fixture_allowed=True,
    )

    assert first.lotus_ai_run_id == replay.lotus_ai_run_id == "wpr_generation_test_001"
    assert runtime.requests[0][0]["idempotency_key"] == runtime.requests[1][0]["idempotency_key"]
    assert replay.result.lineage_persistence_result is not None
    assert replay.result.lineage_persistence_result.decision.value == "replayed"
    record = repository.candidate_record_by_id("idea-ai-001")
    assert record is not None
    assert len(record.ai_explanation_lineage_records) == 1


@pytest.mark.asyncio
async def test_generation_does_not_mutate_candidate_lifecycle_or_identity() -> None:
    repository = _repository_with_candidate()
    before = repository.candidate_record_by_id("idea-ai-001")
    assert before is not None

    await generate_ai_explanation_to_repository(
        _command(),
        repository=repository,
        runtime=FakeRuntime(_enriched_stub_response()),
        unattested_workflow_fixture_allowed=True,
    )

    after = repository.candidate_record_by_id("idea-ai-001")
    assert after is not None
    assert after.candidate == before.candidate
    assert after.evidence_hash == before.evidence_hash


@pytest.mark.asyncio
async def test_generation_refuses_output_when_candidate_evidence_changes_in_flight() -> None:
    repository = EvidenceAdvancingRepository()
    persisted = repository.persist_candidate(
        candidate(),
        idempotency_key="signal-ingestion:generation-evidence-fence:001",
        payload={"candidate_id": "idea-ai-001"},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    assert persisted.record is not None

    outcome = await generate_ai_explanation_to_repository(
        _command(),
        repository=repository,
        runtime=EvidenceAdvancingRuntime(repository),
        unattested_workflow_fixture_allowed=True,
    )

    assert outcome.disposition is (AIExplanationGenerationDisposition.CANDIDATE_EVIDENCE_CHANGED)
    assert outcome.status.value == "EXPLANATION_UNAVAILABLE"
    assert outcome.lotus_ai_run_id == "wpr_generation_test_001"
    assert outcome.runtime_execution_confirmed is True
    assert outcome.result.explanation_result is not None
    assert outcome.result.explanation_result.fallback_used is True
    assert (
        outcome.result.explanation_result.fallback_reason is AIFallbackReason.UNSUPPORTED_EVIDENCE
    )


@pytest.mark.asyncio
async def test_generation_skips_execution_for_unknown_candidate() -> None:
    runtime = FakeRuntime(error=AssertionError("must not execute"))

    outcome = await generate_ai_explanation_to_repository(
        _command(candidate_id="missing-candidate"),
        repository=InMemoryIdeaRepository(),
        runtime=runtime,
        unattested_workflow_fixture_allowed=True,
    )

    assert outcome.result.decision is AIExplanationEvaluationDecision.NOT_FOUND
    assert runtime.requests == []


@pytest.mark.asyncio
async def test_generation_skips_execution_outside_caller_tenant_scope() -> None:
    from app.application.ai_governance import AIExplanationEntitlementDenied

    runtime = FakeRuntime(error=AssertionError("must not execute"))

    with pytest.raises(AIExplanationEntitlementDenied):
        await generate_ai_explanation_to_repository(
            _command(tenant_ids=("tenant-other",)),
            repository=_repository_with_candidate(),
            runtime=runtime,
            unattested_workflow_fixture_allowed=True,
        )

    assert runtime.requests == []
