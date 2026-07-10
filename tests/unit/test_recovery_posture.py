from __future__ import annotations

import json

import pytest

from app.api.durable_write_guard import durable_write_problem
from app.domain import InMemoryIdeaRepository
from app.domain.recovery_posture import (
    ServiceRecoveryPosture,
    evaluate_recovery_readiness,
)
from app.runtime.recovery_posture import (
    RECOVERY_POSTURE_ENV,
    load_recovery_runtime_state,
)


@pytest.mark.parametrize(
    ("posture", "write_ready", "status", "blocker"),
    [
        (ServiceRecoveryPosture.NORMAL, True, "ready", None),
        (
            ServiceRecoveryPosture.RESTORING,
            False,
            "restoring",
            "service_recovery_restoring",
        ),
        (
            ServiceRecoveryPosture.DEGRADED,
            False,
            "degraded",
            "service_recovery_degraded",
        ),
        (
            ServiceRecoveryPosture.DRAINING,
            False,
            "draining",
            "service_recovery_draining",
        ),
    ],
)
def test_recovery_posture_domain_policy(
    posture: ServiceRecoveryPosture,
    write_ready: bool,
    status: str,
    blocker: str | None,
) -> None:
    decision = evaluate_recovery_readiness(posture)

    assert decision.write_ready is write_ready
    assert decision.readiness_status == status
    assert decision.blocker == blocker


def test_invalid_recovery_posture_fails_closed_without_echoing_value() -> None:
    state = load_recovery_runtime_state({RECOVERY_POSTURE_ENV: "secret-provider-state"})

    assert state.configuration_valid is False
    assert state.posture is ServiceRecoveryPosture.DEGRADED
    assert state.decision.blocker == "recovery_posture_invalid"


@pytest.mark.parametrize(
    ("posture", "expected_code"),
    [
        ("restoring", "service_restoring"),
        ("degraded", "service_recovery_degraded"),
        ("draining", "service_draining"),
        ("invalid-secret-posture", "service_recovery_degraded"),
    ],
)
def test_durable_write_guard_blocks_non_normal_recovery_posture(
    monkeypatch: pytest.MonkeyPatch,
    posture: str,
    expected_code: str,
) -> None:
    monkeypatch.setenv(RECOVERY_POSTURE_ENV, posture)

    response = durable_write_problem(InMemoryIdeaRepository())

    assert response is not None
    payload = json.loads(response.body)
    assert response.status_code == 503
    assert payload["code"] == expected_code
    assert "secret" not in response.body.decode().lower()
