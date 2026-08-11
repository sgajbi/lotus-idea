from __future__ import annotations

from typing import Any

import pytest
from fastapi.responses import JSONResponse

import app.api.conversion_governance_operations as operations
from app.domain import (
    ConversionPersistenceDecision,
    ConversionPersistenceResult,
    InMemoryIdeaRepository,
)
from app.observability import IdeaOperation, OperationOutcome
from app.security.caller_context import PermissionDeniedError


def caller_headers(
    *,
    capability: str = "idea.conversion.intent.record",
) -> operations.ConversionCallerHeaders:
    return operations.ConversionCallerHeaders(
        subject="advisor-001",
        roles=None,
        capabilities=capability,
        tenant_ids="tenant-private-bank-sg",
        book_ids="book-advisor-001",
        portfolio_ids="PB_SG_GLOBAL_BAL_001",
        client_ids="client-001",
        trusted_caller_context=None,
    )


def test_build_conversion_caller_headers_preserves_trusted_context_and_scope() -> None:
    headers = operations.build_conversion_caller_headers(
        subject="advisor-002",
        roles="relationship-manager",
        capabilities="idea.conversion.outcome.record",
        tenant_ids="tenant-private-bank-sg",
        book_ids="book-advisor-002",
        portfolio_ids="PB_SG_GLOBAL_BAL_001",
        client_ids="client-002",
        trusted_caller_context="trusted-context-token",
    )

    assert headers == operations.ConversionCallerHeaders(
        subject="advisor-002",
        roles="relationship-manager",
        capabilities="idea.conversion.outcome.record",
        tenant_ids="tenant-private-bank-sg",
        book_ids="book-advisor-002",
        portfolio_ids="PB_SG_GLOBAL_BAL_001",
        client_ids="client-002",
        trusted_caller_context="trusted-context-token",
    )


def test_prepare_conversion_mutation_builds_context_without_runtime_split(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = InMemoryIdeaRepository()
    monkeypatch.setattr(operations, "get_idea_repository", lambda: repository)
    monkeypatch.setattr(
        operations,
        "idea_repository_durable_storage_backed",
        lambda candidate_repository: candidate_repository is repository,
    )
    monkeypatch.setattr(operations, "durable_write_problem", lambda _: None)

    context = operations.prepare_conversion_mutation(
        headers=caller_headers(),
        capability="idea.conversion.intent.record",
        idempotency_key="conversion-api-ops-001",
        operation=IdeaOperation.CONVERSION_INTENT,
    )

    assert not isinstance(context, JSONResponse)
    assert context.caller.subject == "advisor-001"
    assert context.repository is repository
    assert context.durable_storage_backed is True


def test_prepare_conversion_mutation_rejects_missing_capability() -> None:
    with pytest.raises(PermissionDeniedError, match="Permission denied"):
        operations.prepare_conversion_mutation(
            headers=caller_headers(capability="idea.review.record"),
            capability="idea.conversion.intent.record",
            idempotency_key="conversion-api-ops-denied-001",
            operation=IdeaOperation.CONVERSION_INTENT,
        )


def test_prepare_conversion_mutation_requires_complete_entitlement_scope() -> None:
    with pytest.raises(PermissionDeniedError, match="Permission denied"):
        operations.prepare_conversion_mutation(
            headers=operations.ConversionCallerHeaders(
                subject="advisor-001",
                roles=None,
                capabilities="idea.conversion.intent.record",
                tenant_ids="tenant-private-bank-sg",
                book_ids="book-advisor-001",
                portfolio_ids=None,
                client_ids="client-001",
                trusted_caller_context=None,
            ),
            capability="idea.conversion.intent.record",
            idempotency_key="conversion-api-ops-scope-001",
            operation=IdeaOperation.CONVERSION_INTENT,
            require_complete_entitlement_scope=True,
        )


def test_prepare_conversion_mutation_returns_product_safe_durable_write_problem(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    emitted_events: list[dict[str, Any]] = []
    problem = JSONResponse(
        status_code=503,
        content={"code": "durable_repository_not_configured"},
    )
    monkeypatch.setattr(operations, "get_idea_repository", InMemoryIdeaRepository)
    monkeypatch.setattr(operations, "idea_repository_durable_storage_backed", lambda _: False)
    monkeypatch.setattr(operations, "durable_write_problem", lambda _: problem)
    monkeypatch.setattr(
        operations,
        "emit_conversion_operation_event",
        lambda operation, outcome, error_code=None, durable_storage_backed=False: (
            emitted_events.append(
                {
                    "operation": operation,
                    "outcome": outcome,
                    "source_authority": "lotus-idea",
                    "error_code": error_code,
                    "durable_storage_backed": durable_storage_backed,
                }
            )
        ),
    )

    response = operations.prepare_conversion_mutation(
        headers=caller_headers(),
        capability="idea.conversion.intent.record",
        idempotency_key="conversion-api-ops-durable-001",
        operation=IdeaOperation.CONVERSION_INTENT,
    )

    assert response is problem
    assert emitted_events == [
        {
            "operation": IdeaOperation.CONVERSION_INTENT,
            "outcome": OperationOutcome.BLOCKED,
            "source_authority": "lotus-idea",
            "error_code": "durable_repository_not_configured",
            "durable_storage_backed": False,
        }
    ]


def test_conversion_permission_denied_response_emits_product_safe_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    emitted_events: list[dict[str, Any]] = []
    monkeypatch.setattr(
        operations,
        "emit_conversion_operation_event",
        lambda operation, outcome, error_code=None, durable_storage_backed=False: (
            emitted_events.append(
                {
                    "operation": operation,
                    "outcome": outcome,
                    "error_code": error_code,
                    "durable_storage_backed": durable_storage_backed,
                }
            )
        ),
    )

    response = operations.conversion_permission_denied_response(
        operation=IdeaOperation.CONVERSION_OUTCOME,
        detail="The caller is not permitted to record idea conversion outcomes.",
    )

    assert response.status_code == 403
    assert b"permission_denied" in response.body
    assert emitted_events == [
        {
            "operation": IdeaOperation.CONVERSION_OUTCOME,
            "outcome": OperationOutcome.PERMISSION_DENIED,
            "error_code": "permission_denied",
            "durable_storage_backed": False,
        }
    ]


@pytest.mark.parametrize(
    ("decision", "expected_status", "expected_code"),
    (
        (ConversionPersistenceDecision.NOT_FOUND, 404, "conversion_resource_not_found"),
        (ConversionPersistenceDecision.CONFLICT, 409, "idempotency_conflict"),
        (
            ConversionPersistenceDecision.OUTCOME_CONFLICT,
            409,
            "conversion_outcome_conflict",
        ),
    ),
)
def test_problem_for_conversion_persistence_maps_product_safe_problem_details(
    decision: ConversionPersistenceDecision,
    expected_status: int,
    expected_code: str,
) -> None:
    response = operations.problem_for_conversion_persistence(
        ConversionPersistenceResult(decision=decision, record=None)
    )

    assert response is not None
    assert response.status_code == expected_status
    assert expected_code.encode() in response.body


@pytest.mark.parametrize(
    ("decision", "expected_problem_code", "expected_outcome", "expected_error_code"),
    (
        (ConversionPersistenceDecision.ACCEPTED, None, OperationOutcome.ACCEPTED, None),
        (
            ConversionPersistenceDecision.CONFLICT,
            "idempotency_conflict",
            OperationOutcome.CONFLICT,
            "idempotency_conflict",
        ),
    ),
)
def test_emit_conversion_persistence_event_or_problem_maps_event_and_problem_once(
    monkeypatch: pytest.MonkeyPatch,
    decision: ConversionPersistenceDecision,
    expected_problem_code: str | None,
    expected_outcome: OperationOutcome,
    expected_error_code: str | None,
) -> None:
    emitted_events: list[dict[str, Any]] = []
    monkeypatch.setattr(
        operations,
        "emit_conversion_operation_event",
        lambda operation, outcome, error_code=None, durable_storage_backed=False: (
            emitted_events.append(
                {
                    "operation": operation,
                    "outcome": outcome,
                    "error_code": error_code,
                    "durable_storage_backed": durable_storage_backed,
                }
            )
        ),
    )

    response = operations.emit_conversion_persistence_event_or_problem(
        operation=IdeaOperation.CONVERSION_INTENT,
        result=ConversionPersistenceResult(decision=decision, record=None),
        durable_storage_backed=True,
    )

    if expected_problem_code is None:
        assert response is None
    else:
        assert response is not None
        assert expected_problem_code.encode() in response.body
    assert emitted_events == [
        {
            "operation": IdeaOperation.CONVERSION_INTENT,
            "outcome": expected_outcome,
            "error_code": expected_error_code,
            "durable_storage_backed": True,
        }
    ]
