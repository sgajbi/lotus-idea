from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
import json
from fastapi.responses import JSONResponse
import pytest

from app.api.signal_api_support import (
    SignalSourceRefContract,
    evaluate_caller_supplied_signal,
    operation_outcome_from_signal_evaluation,
    signal_permission_problem_or_none,
    signal_source_ref_one_of_contract_problem_or_none,
    signal_source_ref_contract_problem_or_none,
    source_authority_from_contracts,
    source_authority_from_refs,
)
from app.api.idea_signals import _operation_outcome_from_candidate_persistence
from app.domain import SourceSystem
from app.domain import (
    CandidatePersistenceDecision,
    OpportunityFamily,
    ReasonCode,
    SignalEvaluationOutcome,
    SignalEvaluationResult,
)
from app.domain.access_scope import ReviewAccessScope
from app.observability import IdeaOperation, OperationOutcome
from app.security.caller_context import CallerContext, CallerEntitlementScope
from app.application.source_ingestion import _source_ingestion_decision
from app.infrastructure.source_product_payloads import first_reason_code


def test_source_authority_falls_back_for_mixed_source_refs() -> None:
    source_refs = (
        SimpleNamespace(source_system=SimpleNamespace(value="lotus-core")),
        SimpleNamespace(source_system=SimpleNamespace(value="lotus-risk")),
    )

    assert source_authority_from_refs(source_refs) == "source-owned"


def test_source_authority_uses_the_single_ref_authority() -> None:
    source_refs = (SimpleNamespace(source_system=SimpleNamespace(value="lotus-core")),)

    assert source_authority_from_refs(source_refs) == "lotus-core"


def test_source_authority_from_contracts_uses_expected_authority() -> None:
    contracts = (
        SignalSourceRefContract(
            None,
            SourceSystem.LOTUS_RISK,
            ("lotus-risk:ConcentrationRiskReport:v1",),
        ),
    )

    assert source_authority_from_contracts(contracts) == "lotus-risk"


def test_signal_source_ref_contract_rejects_wrong_source_without_leaking_ref() -> None:
    events: list[tuple[str, str, str, str | None]] = []
    source_ref = SimpleNamespace(
        source_system=SourceSystem.LOTUS_CORE,
        product_id="lotus-core:PortfolioStateSnapshot:v1",
    )

    problem = signal_source_ref_contract_problem_or_none(
        contracts=(
            SignalSourceRefContract(
                source_ref,
                SourceSystem.LOTUS_RISK,
                ("lotus-risk:ConcentrationRiskReport:v1",),
            ),
        ),
        source_authority="lotus-risk",
        emit_event=lambda operation, outcome, **kwargs: events.append(
            (
                operation.value,
                outcome.value,
                kwargs["source_authority"],
                kwargs.get("error_code"),
            )
        ),
    )

    assert problem is not None
    assert problem.status_code == 400
    body = problem.body if isinstance(problem.body, bytes) else problem.body.tobytes()
    assert json.loads(body)["code"] == "invalid_request"
    assert "PortfolioStateSnapshot" not in body.decode("utf-8")
    assert events == [
        (
            "signal_evaluation",
            "invalid_request",
            "lotus-risk",
            "source_ref_contract_mismatch",
        )
    ]


def test_signal_source_ref_contract_uses_offending_contract_source_authority() -> None:
    events: list[tuple[str, str, str | None]] = []
    manage_source_ref = SimpleNamespace(
        source_system=SourceSystem.LOTUS_MANAGE,
        product_id="lotus-manage:PortfolioActionRegister:v1",
    )
    mismatched_performance_source_ref = SimpleNamespace(
        source_system=SourceSystem.LOTUS_CORE,
        product_id="lotus-core:PortfolioStateSnapshot:v1",
    )

    problem = signal_source_ref_contract_problem_or_none(
        contracts=(
            SignalSourceRefContract(
                manage_source_ref,
                SourceSystem.LOTUS_MANAGE,
                ("lotus-manage:PortfolioActionRegister:v1",),
            ),
            SignalSourceRefContract(
                mismatched_performance_source_ref,
                SourceSystem.LOTUS_PERFORMANCE,
                ("lotus-performance:MandatePerformanceHealthContext:v1",),
            ),
        ),
        source_authority="source-owned",
        emit_event=lambda operation, outcome, **kwargs: events.append(
            (operation.value, outcome.value, kwargs.get("source_authority"))
        ),
    )

    assert problem is not None
    assert events == [("signal_evaluation", "invalid_request", "lotus-performance")]


def test_signal_source_ref_one_of_contract_accepts_any_matching_contract() -> None:
    source_ref = SimpleNamespace(
        source_system=SourceSystem.LOTUS_MANAGE,
        product_id="lotus-manage:PortfolioActionRegister:v1",
    )

    problem = signal_source_ref_one_of_contract_problem_or_none(
        contracts=(
            SignalSourceRefContract(
                source_ref,
                SourceSystem.LOTUS_CORE,
                ("lotus-core:PortfolioStateSnapshot:v1",),
            ),
            SignalSourceRefContract(
                source_ref,
                SourceSystem.LOTUS_MANAGE,
                ("lotus-manage:PortfolioActionRegister:v1",),
            ),
        ),
        source_authority="lotus-manage",
        emit_event=lambda *args, **kwargs: None,
    )

    assert problem is None


def test_signal_source_ref_one_of_contract_allows_no_contracts_or_ref() -> None:
    def emit_event(*args: Any, **kwargs: Any) -> None:
        del args, kwargs

    assert (
        signal_source_ref_one_of_contract_problem_or_none(
            contracts=(),
            source_authority="source-owned",
            emit_event=emit_event,
        )
        is None
    )
    assert (
        signal_source_ref_one_of_contract_problem_or_none(
            contracts=(
                SignalSourceRefContract(
                    None,
                    SourceSystem.LOTUS_CORE,
                    ("lotus-core:PortfolioStateSnapshot:v1",),
                ),
            ),
            source_authority="lotus-core",
            emit_event=emit_event,
        )
        is None
    )


def test_candidate_persistence_outcomes_preserve_duplicate_and_conflict_semantics() -> None:
    evaluation = SignalEvaluationResult(
        outcome=SignalEvaluationOutcome.NOT_ELIGIBLE,
        family=OpportunityFamily.HIGH_CASH,
        reason_codes=(ReasonCode.BELOW_MATERIALITY,),
    )

    assert (
        _operation_outcome_from_candidate_persistence(
            persistence_decision=CandidatePersistenceDecision.DUPLICATE_CANDIDATE,
            evaluation=evaluation,
        )
        is OperationOutcome.DUPLICATE
    )
    assert (
        _operation_outcome_from_candidate_persistence(
            persistence_decision=CandidatePersistenceDecision.CONFLICT,
            evaluation=evaluation,
        )
        is OperationOutcome.CONFLICT
    )


def test_source_ingestion_rejects_unpersisted_candidate_created_result() -> None:
    evaluation = SignalEvaluationResult(
        outcome=SignalEvaluationOutcome.CANDIDATE_CREATED,
        family=OpportunityFamily.HIGH_CASH,
        reason_codes=(ReasonCode.HIGH_CASH_RATIO,),
    )

    with pytest.raises(RuntimeError, match="was not persisted"):
        _source_ingestion_decision(
            cast(Any, SimpleNamespace(evaluation=evaluation, persistence=None))
        )


def test_first_reason_code_returns_none_for_empty_or_non_text_reasons() -> None:
    assert first_reason_code({"reasonCodes": [None, " ", 42]}) is None


def test_signal_source_ref_one_of_contract_rejects_unknown_pair_without_leaking_ref() -> None:
    events: list[tuple[str, str, str | None]] = []
    source_ref = SimpleNamespace(
        source_system=SourceSystem.LOTUS_RISK,
        product_id="lotus-risk:MandateRiskHealthContext:v1",
    )

    problem = signal_source_ref_one_of_contract_problem_or_none(
        contracts=(
            SignalSourceRefContract(
                source_ref,
                SourceSystem.LOTUS_CORE,
                ("lotus-core:PortfolioStateSnapshot:v1",),
            ),
            SignalSourceRefContract(
                source_ref,
                SourceSystem.LOTUS_MANAGE,
                ("lotus-manage:PortfolioActionRegister:v1",),
            ),
        ),
        source_authority="source-owned",
        emit_event=lambda operation, outcome, **kwargs: events.append(
            (operation.value, outcome.value, kwargs.get("error_code"))
        ),
    )

    assert problem is not None
    assert problem.status_code == 400
    body = problem.body if isinstance(problem.body, bytes) else problem.body.tobytes()
    assert json.loads(body)["code"] == "invalid_request"
    assert "MandateRiskHealthContext" not in body.decode("utf-8")
    assert events == [("signal_evaluation", "invalid_request", "source_ref_contract_mismatch")]


def test_caller_supplied_signal_boundary_orders_auth_contract_evaluation_and_projection() -> None:
    events: list[tuple[str, str, str]] = []
    calls: list[str] = []
    expected = SignalEvaluationResult(
        outcome=SignalEvaluationOutcome.NOT_ELIGIBLE,
        family=OpportunityFamily.HIGH_CASH,
        reason_codes=(ReasonCode.BELOW_MATERIALITY,),
    )

    def map_command() -> object:
        calls.append("dto-mapped")
        return object()

    def evaluate(command: object) -> SignalEvaluationResult:
        calls.append("use-case")
        return expected

    def project(
        result: SignalEvaluationResult,
        *,
        source_authority: str,
    ) -> SignalEvaluationResult:
        calls.append(f"response:{source_authority}:{result.outcome.value}")
        return result

    response = evaluate_caller_supplied_signal(
        caller=_signal_caller(portfolio_ids=("PB_SG_GLOBAL_BAL_001",)),
        source_authority="lotus-core",
        source_contracts=(
            SignalSourceRefContract(
                None,
                SourceSystem.LOTUS_CORE,
                ("lotus-core:PortfolioStateSnapshot:v1",),
            ),
        ),
        requested_access_scope=_requested_scope(portfolio_id="PB_SG_GLOBAL_BAL_001"),
        command_factory=map_command,
        evaluator=evaluate,
        response_factory=project,
        emit_event=lambda operation, outcome, **kwargs: events.append(
            (operation.value, outcome.value, kwargs["source_authority"])
        ),
    )

    assert response is expected
    assert calls == ["dto-mapped", "use-case", "response:lotus-core:not_eligible"]
    assert events == [("signal_evaluation", "not_eligible", "lotus-core")]


def test_caller_supplied_signal_boundary_does_not_call_use_case_after_scope_denial() -> None:
    calls: list[str] = []

    def map_command() -> object:
        calls.append("dto-mapped")
        return object()

    def unexpected_evaluator(command: object) -> SignalEvaluationResult:
        raise AssertionError("the application use case must not run after scope denial")

    def project(
        result: SignalEvaluationResult,
        *,
        source_authority: str,
    ) -> SignalEvaluationResult:
        return result

    response = evaluate_caller_supplied_signal(
        caller=_signal_caller(portfolio_ids=("PB_SG_GLOBAL_BAL_001",)),
        source_authority="lotus-core",
        source_contracts=(),
        requested_access_scope=_requested_scope(portfolio_id="PB_SG_OTHER_002"),
        command_factory=map_command,
        evaluator=unexpected_evaluator,
        response_factory=project,
        emit_event=lambda *args, **kwargs: None,
    )

    assert isinstance(response, JSONResponse)
    assert response.status_code == 403
    assert calls == []


def test_signal_outcome_maps_suppressed_to_operation_outcome() -> None:
    result = cast(Any, SimpleNamespace(outcome=SimpleNamespace(value="suppressed")))

    assert operation_outcome_from_signal_evaluation(result) == OperationOutcome.SUPPRESSED


def test_signal_permission_allows_in_scope_request() -> None:
    events: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    problem = signal_permission_problem_or_none(
        caller=_signal_caller(portfolio_ids=("PB_SG_GLOBAL_BAL_001",)),
        source_authority="lotus-risk",
        requested_access_scope=_requested_scope(portfolio_id="PB_SG_GLOBAL_BAL_001"),
        emit_event=lambda *args, **kwargs: events.append((args, kwargs)),
    )

    assert problem is None
    assert events == []


def test_signal_permission_denies_capability_only_caller() -> None:
    problem = signal_permission_problem_or_none(
        caller=CallerContext.from_iterables(
            subject="service-001",
            capabilities=("idea.signal.evaluate",),
        ),
        source_authority="lotus-risk",
        requested_access_scope=None,
        emit_event=lambda *args, **kwargs: None,
    )

    assert problem is not None
    assert problem.status_code == 403


def test_signal_permission_denies_role_only_caller() -> None:
    problem = signal_permission_problem_or_none(
        caller=CallerContext.from_iterables(
            subject="advisor-001",
            roles=("advisor",),
        ),
        source_authority="lotus-risk",
        requested_access_scope=None,
        emit_event=lambda *args, **kwargs: None,
    )

    assert problem is not None
    assert problem.status_code == 403


def test_signal_permission_denies_wrong_role_with_capability() -> None:
    problem = signal_permission_problem_or_none(
        caller=CallerContext.from_iterables(
            subject="viewer-001",
            roles=("viewer",),
            capabilities=("idea.signal.evaluate",),
        ),
        source_authority="lotus-risk",
        requested_access_scope=None,
        emit_event=lambda *args, **kwargs: None,
    )

    assert problem is not None
    assert problem.status_code == 403


def test_signal_permission_denies_wrong_capability_with_advisor_role() -> None:
    problem = signal_permission_problem_or_none(
        caller=CallerContext.from_iterables(
            subject="advisor-001",
            roles=("advisor",),
            capabilities=("idea.signal.read",),
        ),
        source_authority="lotus-risk",
        requested_access_scope=None,
        emit_event=lambda *args, **kwargs: None,
    )

    assert problem is not None
    assert problem.status_code == 403


def test_signal_permission_denies_out_of_scope_request_with_bounded_event() -> None:
    events: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    problem = signal_permission_problem_or_none(
        caller=_signal_caller(portfolio_ids=("PB_SG_GLOBAL_BAL_001",)),
        source_authority="lotus-risk",
        requested_access_scope=_requested_scope(portfolio_id="PB_SG_OTHER_002"),
        emit_event=lambda *args, **kwargs: events.append((args, kwargs)),
    )

    assert problem is not None
    assert problem.status_code == 403
    body = json.loads(bytes(problem.body).decode("utf-8"))
    assert body == {
        "type": "about:blank",
        "status": 403,
        "code": "permission_denied",
        "title": "Permission denied",
        "detail": "The caller is not permitted to evaluate idea signals for the requested scope.",
    }
    assert "PB_SG_OTHER_002" not in bytes(problem.body).decode("utf-8")
    assert events == [
        (
            (IdeaOperation.SIGNAL_EVALUATION, OperationOutcome.PERMISSION_DENIED),
            {"source_authority": "lotus-risk", "error_code": "permission_denied"},
        )
    ]


def test_signal_permission_denies_scoped_request_without_caller_entitlements() -> None:
    problem = signal_permission_problem_or_none(
        caller=CallerContext.from_iterables(
            subject="advisor-001",
            roles=("advisor",),
            capabilities=("idea.signal.evaluate",),
        ),
        source_authority="lotus-risk",
        requested_access_scope=_requested_scope(portfolio_id="PB_SG_GLOBAL_BAL_001"),
        emit_event=lambda *args, **kwargs: None,
    )

    assert problem is not None
    assert problem.status_code == 403


def _signal_caller(*, portfolio_ids: tuple[str, ...]) -> CallerContext:
    return CallerContext.from_iterables(
        subject="advisor-001",
        roles=("advisor",),
        capabilities=("idea.signal.evaluate",),
        entitlement_scope=CallerEntitlementScope.from_iterables(
            tenant_ids=("tenant-private-bank-sg",),
            book_ids=("book-advisor-001",),
            portfolio_ids=portfolio_ids,
            client_ids=("client-001",),
        ),
    )


def _requested_scope(*, portfolio_id: str) -> ReviewAccessScope:
    return ReviewAccessScope(
        tenant_id="tenant-private-bank-sg",
        book_id="book-advisor-001",
        portfolio_id=portfolio_id,
        client_id="client-001",
    )
