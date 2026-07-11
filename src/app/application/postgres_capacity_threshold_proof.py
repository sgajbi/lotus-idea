from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.domain.capacity_posture import CapacityPosture, PostgresCapacityPosture
from app.ports.postgres_capacity_stress import PostgresCapacityStressPort


SCHEMA_VERSION = "lotus-idea.postgres-capacity-threshold-proof.v1"
MAXIMUM_CONTROLLED_LOAD_CONNECTIONS = 100


def execute_postgres_capacity_threshold_proof(
    *,
    stress_port: PostgresCapacityStressPort,
    environment_profile: str,
    generated_at_utc: datetime,
    commit_sha: str,
    branch: str,
    run_id: str,
    maximum_load_connections: int,
) -> dict[str, Any]:
    _validate_inputs(
        environment_profile=environment_profile,
        generated_at_utc=generated_at_utc,
        commit_sha=commit_sha,
        branch=branch,
        run_id=run_id,
        maximum_load_connections=maximum_load_connections,
    )
    initial = stress_port.read_posture()
    if initial.posture is not CapacityPosture.NORMAL:
        raise ValueError("PostgreSQL capacity proof requires normal initial posture")

    held_connections = 0
    threshold: PostgresCapacityPosture | None = None
    try:
        for held_connections in range(1, maximum_load_connections + 1):
            stress_port.acquire_load_connection()
            observation = stress_port.read_posture()
            if observation.posture is CapacityPosture.UNAVAILABLE:
                raise ValueError("PostgreSQL capacity posture became unavailable under load")
            if observation.posture is CapacityPosture.SHED:
                threshold = observation
                break
        if threshold is None:
            raise ValueError("PostgreSQL shed threshold was not reached within the connection cap")
    finally:
        stress_port.release_load_connections()

    recovered = stress_port.read_posture()
    if recovered.posture is not CapacityPosture.NORMAL:
        raise ValueError("PostgreSQL capacity posture did not recover to normal")
    return {
        "schemaVersion": SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofScope": "source_safe_postgres_capacity_threshold_and_recovery",
        "claimPosture": "controlled_environment_evidence_only",
        "environmentProfile": environment_profile,
        "generatedAtUtc": generated_at_utc.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "commitSha": commit_sha,
        "branch": branch,
        "runId": run_id,
        "initial": _observation(initial),
        "threshold": {**_observation(threshold), "heldConnectionCount": held_connections},
        "recovered": _observation(recovered),
        "productionCapacityCertified": False,
        "supportedFeaturePromoted": False,
    }


def _validate_inputs(
    *,
    environment_profile: str,
    generated_at_utc: datetime,
    commit_sha: str,
    branch: str,
    run_id: str,
    maximum_load_connections: int,
) -> None:
    if environment_profile not in {"test", "production-like"}:
        raise ValueError("capacity threshold proof is prohibited in production")
    if generated_at_utc.tzinfo is None or generated_at_utc.utcoffset() is None:
        raise ValueError("generated_at_utc must be timezone-aware")
    if not 1 <= maximum_load_connections <= MAXIMUM_CONTROLLED_LOAD_CONNECTIONS:
        raise ValueError("maximum_load_connections must be between 1 and 100")
    for name, value in (("commit_sha", commit_sha), ("branch", branch), ("run_id", run_id)):
        if not value.strip():
            raise ValueError(f"{name} must not be blank")


def _observation(posture: PostgresCapacityPosture) -> dict[str, object]:
    return {
        "posture": posture.posture.value,
        "connectionUtilizationFraction": posture.connection_utilization_fraction,
        "collectionSucceeded": posture.collection_succeeded,
    }
