from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from app.application.downstream_capacity_seed import (
    SeedDownstreamCapacityResourceCommand,
    build_downstream_capacity_seed_artifact,
    seed_downstream_capacity_resource,
)


SEEDED_AT = datetime(2026, 7, 11, 8, 0, tzinfo=UTC)


class RecordingSeedPort:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def persist_candidate(self, **kwargs: object) -> str:
        self.calls.append(("persist", kwargs))
        return "candidate-synthetic-001"

    def transition_candidate(self, **kwargs: object) -> None:
        self.calls.append(("transition", kwargs))

    def approve_candidate(self, **kwargs: object) -> None:
        self.calls.append(("approve", kwargs))

    def record_conversion_intent(self, **kwargs: object) -> None:
        self.calls.append(("conversion", kwargs))

    def close(self) -> None:
        pass


def test_seed_orchestrates_deterministic_lifecycle_and_conversion() -> None:
    port = RecordingSeedPort()
    command = SeedDownstreamCapacityResourceCommand(
        run_id="capacity-run-1",
        as_of_date=date(2026, 7, 11),
        seeded_at_utc=SEEDED_AT,
    )

    first = seed_downstream_capacity_resource(command, port=port)
    second = seed_downstream_capacity_resource(command, port=RecordingSeedPort())

    assert first == second
    assert first.conversion_intent_id.startswith("capacity-conversion-")
    assert first.downstream_submission_path.endswith(
        f"/{first.conversion_intent_id}/downstream-submissions"
    )
    assert [name for name, _ in port.calls] == [
        "persist",
        "transition",
        "transition",
        "transition",
        "transition",
        "approve",
        "conversion",
    ]
    transition_statuses = [
        call["target_status"] for name, call in port.calls if name == "transition"
    ]
    assert transition_statuses == [
        "enriched",
        "scored",
        "governance_checked",
        "ready_for_review",
    ]


def test_seed_artifact_is_explicitly_synthetic_and_non_certifying() -> None:
    result = seed_downstream_capacity_resource(
        SeedDownstreamCapacityResourceCommand(
            run_id="capacity-run-1",
            as_of_date=date(2026, 7, 11),
            seeded_at_utc=SEEDED_AT,
        ),
        port=RecordingSeedPort(),
    )

    artifact = build_downstream_capacity_seed_artifact(
        result,
        generated_at_utc=SEEDED_AT,
        commit_sha="a" * 40,
        branch="main",
        run_id="capacity-run-1",
    )

    assert artifact["syntheticResource"] is True
    assert artifact["claimPosture"] == "seed_only_not_capacity_evidence"
    assert artifact["productionCapacityCertified"] is False
    assert artifact["supportedFeaturePromoted"] is False
    assert "portfolio" not in str(artifact).lower()
    assert "client" not in str(artifact).lower()


@pytest.mark.parametrize(
    ("generated_at", "commit_sha", "branch", "run_id", "message"),
    [
        (datetime(2026, 7, 11), "a", "main", "run", "timezone-aware"),
        (SEEDED_AT, " ", "main", "run", "commit_sha"),
        (SEEDED_AT, "a", " ", "run", "branch"),
        (SEEDED_AT, "a", "main", " ", "run_id"),
    ],
)
def test_seed_artifact_rejects_ambiguous_provenance(
    generated_at: datetime,
    commit_sha: str,
    branch: str,
    run_id: str,
    message: str,
) -> None:
    result = seed_downstream_capacity_resource(
        SeedDownstreamCapacityResourceCommand(
            run_id="capacity-run-1",
            as_of_date=date(2026, 7, 11),
            seeded_at_utc=SEEDED_AT,
        ),
        port=RecordingSeedPort(),
    )

    with pytest.raises(ValueError, match=message):
        build_downstream_capacity_seed_artifact(
            result,
            generated_at_utc=generated_at,
            commit_sha=commit_sha,
            branch=branch,
            run_id=run_id,
        )


@pytest.mark.parametrize(
    ("run_id", "seeded_at", "message"),
    [
        (" ", SEEDED_AT, "run_id"),
        ("run", datetime(2026, 7, 11), "timezone-aware"),
    ],
)
def test_seed_command_rejects_ambiguous_provenance(
    run_id: str, seeded_at: datetime, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        SeedDownstreamCapacityResourceCommand(
            run_id=run_id,
            as_of_date=date(2026, 7, 11),
            seeded_at_utc=seeded_at,
        )
