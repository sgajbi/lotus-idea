from __future__ import annotations

from app.api.caller_context_openapi import CALLER_CONTEXT_EXTENSION
from app.main import app


def _operation(method: str, path: str) -> dict:
    return app.openapi()["paths"][path][method.lower()]


def _header_descriptions(operation: dict) -> dict[str, str]:
    return {
        parameter["name"]: parameter.get("description", "")
        for parameter in operation.get("parameters", [])
        if parameter.get("in") == "header"
    }


def test_signal_evaluation_openapi_publishes_caller_context_security() -> None:
    operation = _operation("POST", "/api/v1/idea-signals/high-cash/evaluate")

    assert operation["security"] == [{"LotusCallerContext": []}]
    caller_context = operation[CALLER_CONTEXT_EXTENSION]
    assert caller_context["requiredCapabilities"] == ["idea.signal.evaluate"]
    assert caller_context["requiredRoles"] == ["advisor"]
    assert "privileged X-Caller-* headers" in caller_context["trustedCallerContextProvenance"]
    headers = _header_descriptions(operation)
    assert headers["X-Caller-Capabilities"]
    assert headers["X-Lotus-Trusted-Caller-Context"]


def test_operator_readiness_openapi_publishes_caller_context_security() -> None:
    operation = _operation("GET", "/api/v1/implementation-proof/readiness")

    caller_context = operation[CALLER_CONTEXT_EXTENSION]
    assert caller_context["requiredCapabilities"] == ["idea.implementation-proof.readiness.read"]
    assert caller_context["requiredRoles"] == ["operator"]


def test_outbox_run_openapi_publishes_caller_context_security() -> None:
    operation = _operation("POST", "/api/v1/outbox-delivery/run-once")

    caller_context = operation[CALLER_CONTEXT_EXTENSION]
    assert caller_context["requiredCapabilities"] == ["idea.outbox-delivery.run"]
    assert caller_context["requiredRoles"] == ["operator"]


def test_advisor_queue_openapi_publishes_alternative_advisor_role() -> None:
    operation = _operation("GET", "/api/v1/review-queues/advisor")

    caller_context = operation[CALLER_CONTEXT_EXTENSION]
    assert caller_context["requiredCapabilities"] == ["idea.review.queue.read"]
    assert caller_context["alternativeRoles"] == ["advisor"]
