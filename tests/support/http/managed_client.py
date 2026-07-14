from __future__ import annotations

from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar, Token
from typing import Any

from fastapi.testclient import TestClient
from starlette.types import ASGIApp


ManagedTestClient = TestClient

_active_client_stack: ContextVar[ExitStack | None] = ContextVar(
    "lotus_idea_integration_test_client_stack",
    default=None,
)


def managed_test_client(app: ASGIApp, **kwargs: Any) -> TestClient:
    """Create a lifespan-aware client closed by the integration-test scope."""
    stack = _active_client_stack.get()
    if stack is None:
        raise RuntimeError("managed_test_client requires the integration managed-client fixture")
    return stack.enter_context(TestClient(app, **kwargs))


@contextmanager
def managed_test_client_scope() -> Iterator[None]:
    """Own every client created during one integration test."""
    stack = ExitStack()
    token: Token[ExitStack | None] = _active_client_stack.set(stack)
    try:
        yield
    finally:
        stack.close()
        _active_client_stack.reset(token)
