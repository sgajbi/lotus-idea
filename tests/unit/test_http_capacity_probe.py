from __future__ import annotations

import httpx
import pytest

from app.infrastructure.http_capacity_probe import HttpCapacityProbe
from app.ports.capacity_probe import CapacityProbeRequest


def _request() -> CapacityProbeRequest:
    return CapacityProbeRequest(
        method="POST",
        path="/api/v1/outbox-delivery/run-once?limit=100&maxRetryCount=3",
        headers={"X-Caller-Roles": "operator", "Authorization": "secret"},
        expected_status_codes=frozenset({200}),
    )


def test_probe_returns_only_bounded_operational_response_fields() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "secret"
        return httpx.Response(
            200,
            json={
                "runStatus": "completed",
                "attemptedCount": 100,
                "deliveredCount": 98,
                "failedCount": 2,
                "durableStorageBacked": True,
                "oldestDeliveryReadyAgeSeconds": 12.5,
                "configurationBlockers": ["attacker-controlled-detail"],
                "operatorRunReference": "must-not-leak",
                "candidateId": "must-not-leak",
                "payload": {"must": "not-leak"},
            },
        )

    clock = iter((10.0, 10.25))
    probe = HttpCapacityProbe(
        base_url="https://idea.example",
        timeout_seconds=2.0,
        transport=httpx.MockTransport(handler),
        monotonic=lambda: next(clock),
    )

    result = probe.execute(_request())

    assert result.duration_seconds == 0.25
    assert result.status_code == 200
    assert result.transport_outcome == "accepted"
    assert result.response_summary == {
        "runStatus": "completed",
        "attemptedCount": 100,
        "deliveredCount": 98,
        "failedCount": 2,
        "durableStorageBacked": True,
        "oldestDeliveryReadyAgeSeconds": 12.5,
    }
    probe.close()


def test_probe_classifies_unexpected_status_without_preserving_problem_detail() -> None:
    probe = HttpCapacityProbe(
        base_url="https://idea.example",
        timeout_seconds=2.0,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                503,
                json={"code": "downstream_failure", "detail": "sensitive diagnostic"},
            )
        ),
    )

    result = probe.execute(_request())

    assert result.status_code == 503
    assert result.transport_outcome == "rejected"
    assert result.response_summary == {}


def test_probe_classifies_timeout_and_transport_failure_without_raw_errors() -> None:
    for exception, expected in (
        (httpx.ReadTimeout("timeout"), "timeout"),
        (httpx.ConnectError("host detail"), "unavailable"),
    ):
        probe = HttpCapacityProbe(
            base_url="https://idea.example",
            timeout_seconds=2.0,
            transport=httpx.MockTransport(
                lambda request, error=exception: (_ for _ in ()).throw(error)
            ),
        )

        result = probe.execute(_request())

        assert result.status_code is None
        assert result.transport_outcome == expected
        assert result.response_summary == {}


def test_probe_rejects_non_positive_timeout() -> None:
    try:
        HttpCapacityProbe(base_url="https://idea.example", timeout_seconds=0)
    except ValueError as error:
        assert str(error) == "timeout_seconds must be positive"
    else:
        raise AssertionError("expected invalid timeout to fail")


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="plain"),
        httpx.Response(200, content=b"{", headers={"content-type": "application/json"}),
        httpx.Response(200, json=[{"runStatus": "completed"}]),
    ],
)
def test_probe_discards_non_json_malformed_and_non_object_responses(
    response: httpx.Response,
) -> None:
    probe = HttpCapacityProbe(
        base_url="https://idea.example",
        timeout_seconds=2.0,
        transport=httpx.MockTransport(lambda request: response),
    )

    result = probe.execute(_request())

    assert result.response_summary == {}
