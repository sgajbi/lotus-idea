from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from app.infrastructure.lotus_ai.workflow_runtime import (
    HttpLotusAIWorkflowRuntime,
    InvalidLotusAIWorkflowRuntimeResponse,
    LotusAIWorkflowRuntimeUnavailable,
)
from tests.support.ai_runtime_proof import lotus_ai_runtime_execution_response


@pytest.mark.asyncio
async def test_posts_governed_request_with_trusted_caller_header() -> None:
    observed: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        observed.append(request)
        return httpx.Response(200, json=lotus_ai_runtime_execution_response())

    runtime = HttpLotusAIWorkflowRuntime(
        base_url="http://lotus-ai.internal:8140",
        transport=httpx.MockTransport(handler),
    )

    response = await runtime.execute_workflow_pack(
        {"pack_id": "idea_explanation.pack", "version": "v1"},
        caller_app="lotus-idea",
    )

    request = observed[0]
    assert request.url == "http://lotus-ai.internal:8140/platform/workflow-packs/execute"
    assert request.headers["X-Caller-App"] == "lotus-idea"
    assert json.loads(request.content) == {
        "pack_id": "idea_explanation.pack",
        "version": "v1",
    }
    assert response["service"] == "lotus-ai"
    await runtime.close()


@pytest.mark.asyncio
async def test_runtime_io_yields_control_while_lotus_ai_is_pending() -> None:
    request_started = asyncio.Event()
    release_response = asyncio.Event()

    async def handler(request: httpx.Request) -> httpx.Response:
        request_started.set()
        await release_response.wait()
        return httpx.Response(200, json=lotus_ai_runtime_execution_response())

    runtime = HttpLotusAIWorkflowRuntime(
        base_url="http://lotus-ai.internal:8140",
        transport=httpx.MockTransport(handler),
    )

    execution = asyncio.create_task(runtime.execute_workflow_pack({}, caller_app="lotus-idea"))
    await request_started.wait()
    competing_work_completed = await asyncio.sleep(0, result=True)

    assert competing_work_completed is True
    assert execution.done() is False
    release_response.set()
    assert (await execution)["service"] == "lotus-ai"
    await runtime.close()


@pytest.mark.parametrize("base_url", ["", "lotus-ai:8140", "file:///tmp/lotus-ai"])
def test_rejects_non_http_runtime_url(base_url: str) -> None:
    with pytest.raises(ValueError, match="absolute HTTP"):
        HttpLotusAIWorkflowRuntime(base_url=base_url)


@pytest.mark.parametrize("timeout_seconds", [0, -1, 31])
def test_rejects_unbounded_runtime_timeout(timeout_seconds: float) -> None:
    with pytest.raises(ValueError, match="at most 30"):
        HttpLotusAIWorkflowRuntime(
            base_url="http://lotus-ai.internal:8140",
            timeout_seconds=timeout_seconds,
        )


@pytest.mark.asyncio
async def test_maps_transport_failure_to_bounded_unavailable_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("secret infrastructure detail", request=request)

    runtime = HttpLotusAIWorkflowRuntime(
        base_url="http://lotus-ai.internal:8140",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        LotusAIWorkflowRuntimeUnavailable,
        match="lotus-ai workflow runtime is unavailable",
    ) as raised:
        await runtime.execute_workflow_pack({}, caller_app="lotus-idea")

    assert "secret infrastructure detail" not in str(raised.value)
    await runtime.close()


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(503, json={"detail": "database secret"}),
        httpx.Response(200, text="not-json"),
        httpx.Response(200, json=[]),
    ],
)
@pytest.mark.asyncio
async def test_rejects_unsuccessful_or_malformed_runtime_response(
    response: httpx.Response,
) -> None:
    runtime = HttpLotusAIWorkflowRuntime(
        base_url="http://lotus-ai.internal:8140",
        transport=httpx.MockTransport(lambda _: response),
    )

    with pytest.raises(InvalidLotusAIWorkflowRuntimeResponse):
        await runtime.execute_workflow_pack({}, caller_app="lotus-idea")
    await runtime.close()


@pytest.mark.asyncio
async def test_close_releases_the_underlying_http_client() -> None:
    runtime = HttpLotusAIWorkflowRuntime(
        base_url="http://lotus-ai.internal:8140",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={})),
    )

    await runtime.close()

    with pytest.raises(RuntimeError):
        await runtime.execute_workflow_pack(
            {"pack_id": "idea_explanation.pack"}, caller_app="lotus-idea"
        )


@pytest.mark.asyncio
async def test_fetches_attestation_for_exact_encoded_run_identity() -> None:
    observed: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        observed.append(request)
        return httpx.Response(200, json={"schema_version": "attestation.v1"})

    runtime = HttpLotusAIWorkflowRuntime(
        base_url="http://lotus-ai.internal:8140",
        transport=httpx.MockTransport(handler),
    )

    response = await runtime.get_run_attestation("run/with scope")

    assert observed[0].url.raw_path == (
        b"/platform/workflow-packs/runs/run%2Fwith%20scope/attestation"
    )
    assert observed[0].headers["Accept"] == "application/json"
    assert response == {"schema_version": "attestation.v1"}
    await runtime.close()


@pytest.mark.asyncio
async def test_rejects_empty_attestation_run_identity_without_io() -> None:
    runtime = HttpLotusAIWorkflowRuntime(
        base_url="http://lotus-ai.internal:8140",
        transport=httpx.MockTransport(
            lambda request: pytest.fail(f"unexpected request: {request.url}")
        ),
    )

    with pytest.raises(ValueError, match="run id must not be empty"):
        await runtime.get_run_attestation("   ")
    await runtime.close()
