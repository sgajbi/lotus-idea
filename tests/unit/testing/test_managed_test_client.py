from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
import pytest

from tests.support.http import managed_test_client, managed_test_client_scope


def test_managed_client_runs_lifespan_and_closes_at_scope_exit() -> None:
    lifecycle = {"started": 0, "stopped": 0}

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        lifecycle["started"] += 1
        try:
            yield
        finally:
            lifecycle["stopped"] += 1

    app = FastAPI(lifespan=lifespan)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    with managed_test_client_scope():
        client = managed_test_client(app)
        assert client.get("/health").json() == {"status": "ok"}
        assert lifecycle == {"started": 1, "stopped": 0}

    assert lifecycle == {"started": 1, "stopped": 1}


def test_managed_client_rejects_unowned_lifecycle() -> None:
    with pytest.raises(RuntimeError, match="managed-client fixture"):
        managed_test_client(FastAPI())
