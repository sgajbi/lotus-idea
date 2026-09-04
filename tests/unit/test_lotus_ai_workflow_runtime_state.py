import pytest

from app.runtime.lotus_ai_attestation_state import LOTUS_AI_BASE_URL_ENV
from app.runtime.lotus_ai_workflow_runtime_state import (
    LOTUS_AI_RUNTIME_TIMEOUT_SECONDS_ENV,
    close_lotus_ai_workflow_runtime,
    get_lotus_ai_workflow_runtime,
    reset_lotus_ai_workflow_runtime,
)


@pytest.mark.asyncio
async def test_runtime_builds_and_caches_configured_workflow_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await reset_lotus_ai_workflow_runtime()
    monkeypatch.setenv(LOTUS_AI_BASE_URL_ENV, "https://lotus-ai.internal")
    monkeypatch.setenv(LOTUS_AI_RUNTIME_TIMEOUT_SECONDS_ENV, "5.0")

    first = get_lotus_ai_workflow_runtime()
    second = get_lotus_ai_workflow_runtime()

    assert first is second
    await reset_lotus_ai_workflow_runtime()


@pytest.mark.asyncio
async def test_close_releases_runtime_so_next_call_rebuilds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await reset_lotus_ai_workflow_runtime()
    monkeypatch.setenv(LOTUS_AI_BASE_URL_ENV, "https://lotus-ai.internal")

    first = get_lotus_ai_workflow_runtime()
    await close_lotus_ai_workflow_runtime()
    second = get_lotus_ai_workflow_runtime()

    assert first is not second
    await reset_lotus_ai_workflow_runtime()


@pytest.mark.parametrize("timeout", ["invalid", "0", "30.1"])
@pytest.mark.asyncio
async def test_runtime_rejects_invalid_workflow_timeout_configuration(
    monkeypatch: pytest.MonkeyPatch, timeout: str
) -> None:
    await reset_lotus_ai_workflow_runtime()
    monkeypatch.setenv(LOTUS_AI_BASE_URL_ENV, "https://lotus-ai.internal")
    monkeypatch.setenv(LOTUS_AI_RUNTIME_TIMEOUT_SECONDS_ENV, timeout)

    with pytest.raises(RuntimeError, match=LOTUS_AI_RUNTIME_TIMEOUT_SECONDS_ENV):
        get_lotus_ai_workflow_runtime()

    await reset_lotus_ai_workflow_runtime()


@pytest.mark.asyncio
async def test_runtime_requires_lotus_ai_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    await reset_lotus_ai_workflow_runtime()
    monkeypatch.delenv(LOTUS_AI_BASE_URL_ENV, raising=False)

    with pytest.raises(RuntimeError, match=LOTUS_AI_BASE_URL_ENV):
        get_lotus_ai_workflow_runtime()
