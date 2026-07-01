from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
import json

from app.api.signal_api_support import (
    operation_outcome_from_signal_evaluation,
    signal_permission_problem_or_none,
    source_authority_from_refs,
)
from app.domain.access_scope import ReviewAccessScope
from app.observability import IdeaOperation, OperationOutcome
from app.security.caller_context import CallerContext, CallerEntitlementScope


def test_source_authority_falls_back_for_mixed_source_refs() -> None:
    source_refs = (
        SimpleNamespace(source_system=SimpleNamespace(value="lotus-core")),
        SimpleNamespace(source_system=SimpleNamespace(value="lotus-risk")),
    )

    assert source_authority_from_refs(source_refs) == "source-owned"


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
