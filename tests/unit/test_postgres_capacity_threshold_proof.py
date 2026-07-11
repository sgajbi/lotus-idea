from __future__ import annotations

from collections import deque
from datetime import UTC, datetime

import pytest

from app.application.postgres_capacity_threshold_proof import (
    execute_postgres_capacity_threshold_proof,
    validate_postgres_capacity_threshold_proof,
)
from app.domain.capacity_posture import evaluate_postgres_capacity_posture


class StubStressPort:
    def __init__(self, utilizations: list[float | None]) -> None:
        self._utilizations = deque(utilizations)
        self.acquired = 0
        self.released = 0

    def read_posture(self):  # type: ignore[no-untyped-def]
        return evaluate_postgres_capacity_posture(self._utilizations.popleft())

    def acquire_load_connection(self) -> None:
        self.acquired += 1

    def release_load_connections(self) -> None:
        self.released += self.acquired

    def close(self) -> None:
        pass


def _execute(port: StubStressPort, **overrides: object) -> dict[str, object]:
    values = {
        "stress_port": port,
        "environment_profile": "test",
        "generated_at_utc": datetime(2026, 7, 11, 6, 0, tzinfo=UTC),
        "commit_sha": "abc123",
        "branch": "feature/capacity",
        "run_id": "local-1",
        "maximum_load_connections": 5,
    }
    values.update(overrides)
    return execute_postgres_capacity_threshold_proof(**values)  # type: ignore[arg-type]


def test_builds_source_safe_threshold_and_recovery_evidence() -> None:
    port = StubStressPort([0.2, 0.7, 0.9, 0.2])

    artifact = _execute(port)

    assert artifact["proofScope"] == "source_safe_postgres_capacity_threshold_and_recovery"
    assert artifact["claimPosture"] == "controlled_environment_evidence_only"
    assert artifact["threshold"] == {
        "posture": "shed",
        "connectionUtilizationFraction": 0.9,
        "collectionSucceeded": True,
        "heldConnectionCount": 2,
    }
    assert artifact["recovered"]["posture"] == "normal"  # type: ignore[index]
    assert artifact["productionCapacityCertified"] is False
    assert artifact["supportedFeaturePromoted"] is False
    assert port.released == 2
    assert validate_postgres_capacity_threshold_proof(artifact) == []


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("claimPosture",), "production_certified", "claimPosture"),
        (("productionCapacityCertified",), True, "must not claim"),
        (("supportedFeaturePromoted",), True, "must not promote"),
        (("threshold", "posture"), "normal", "must be shed"),
        (("threshold", "heldConnectionCount"), 0, "between 1 and 100"),
        (("recovered", "connectionUtilizationFraction"), 2.0, "between zero and one"),
    ],
)
def test_validator_rejects_claim_or_observation_mutation(
    path: tuple[str, ...], value: object, message: str
) -> None:
    artifact = _execute(StubStressPort([0.2, 0.9, 0.2]))
    target: dict[str, object] = artifact
    for key in path[:-1]:
        target = target[key]  # type: ignore[assignment]
    target[path[-1]] = value

    assert any(message in error for error in validate_postgres_capacity_threshold_proof(artifact))


@pytest.mark.parametrize(
    ("utilizations", "message"),
    [
        ([0.7], "normal initial posture"),
        ([0.2, None], "became unavailable"),
        ([0.2, 0.7, 0.7, 0.7, 0.7, 0.7], "threshold was not reached"),
        ([0.2, 0.9, 0.7], "did not recover"),
    ],
)
def test_fails_closed_and_releases_load_connections(
    utilizations: list[float | None], message: str
) -> None:
    port = StubStressPort(utilizations)

    with pytest.raises(ValueError, match=message):
        _execute(port)

    if len(utilizations) > 1:
        assert port.released == port.acquired


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"environment_profile": "production"}, "prohibited in production"),
        ({"maximum_load_connections": 0}, "between 1 and 100"),
        ({"maximum_load_connections": 101}, "between 1 and 100"),
        ({"commit_sha": " "}, "commit_sha must not be blank"),
        ({"generated_at_utc": datetime(2026, 7, 11)}, "timezone-aware"),
    ],
)
def test_rejects_unsafe_or_ambiguous_inputs(overrides: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        _execute(StubStressPort([0.2]), **overrides)
