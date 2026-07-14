from __future__ import annotations

import json

import httpx
import pytest

from app.infrastructure.lotus_ai.workflow_runtime import (
    HttpLotusAIWorkflowRuntime,
    InvalidLotusAIWorkflowRuntimeResponse,
    LotusAIWorkflowRuntimeUnavailable,
)
from tests.support.ai_runtime_proof import lotus_ai_runtime_execution_response


def test_posts_governed_request_with_trusted_caller_header() -> None:
    observed: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        observed.append(request)
        return httpx.Response(200, json=lotus_ai_runtime_execution_response())

    runtime = HttpLotusAIWorkflowRuntime(
        base_url="http://lotus-ai.internal:8140",
        transport=httpx.MockTransport(handler),
    )

    response = runtime.execute_workflow_pack(
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


def test_maps_transport_failure_to_bounded_unavailable_error() -> None:
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
        runtime.execute_workflow_pack({}, caller_app="lotus-idea")

    assert "secret infrastructure detail" not in str(raised.value)


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(503, json={"detail": "database secret"}),
        httpx.Response(200, text="not-json"),
        httpx.Response(200, json=[]),
    ],
)
def test_rejects_unsuccessful_or_malformed_runtime_response(response: httpx.Response) -> None:
    runtime = HttpLotusAIWorkflowRuntime(
        base_url="http://lotus-ai.internal:8140",
        transport=httpx.MockTransport(lambda _: response),
    )

    with pytest.raises(InvalidLotusAIWorkflowRuntimeResponse):
        runtime.execute_workflow_pack({}, caller_app="lotus-idea")
