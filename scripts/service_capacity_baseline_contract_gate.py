from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app.application.service_capacity_baseline import (  # noqa: E402
    CapacityMeasurement,
    SCENARIOS,
    build_service_capacity_baseline,
    validate_service_capacity_baseline,
)
from app.application.postgres_capacity_threshold_proof import (  # noqa: E402
    execute_postgres_capacity_threshold_proof,
)
from app.domain.capacity_posture import evaluate_postgres_capacity_posture  # noqa: E402
from scripts.generate_service_capacity_baseline import INPUT_KEYS  # noqa: E402


class _ThresholdProofPort:
    def __init__(self) -> None:
        self._utilizations = iter([0.2, 0.9, 0.2])

    def read_posture(self):  # type: ignore[no-untyped-def]
        return evaluate_postgres_capacity_posture(next(self._utilizations))

    def acquire_load_connection(self) -> None:
        pass

    def release_load_connections(self) -> None:
        pass

    def close(self) -> None:
        pass


def validate_contract() -> list[str]:
    measurements = [
        CapacityMeasurement(
            scenario=scenario,
            duration_seconds=0.01,
            outcome="accepted",
            recovered=True if scenario == "dependency_failure" else None,
        )
        for scenario in SCENARIOS
    ]
    artifact = build_service_capacity_baseline(
        measurements=measurements,
        environment_profile="test",
        generated_at_utc=datetime(2026, 7, 11, tzinfo=UTC),
        commit_sha="contract-gate",
        branch="contract-gate",
        run_id="contract-gate",
        observed_window_seconds=1.0,
    )
    errors = validate_service_capacity_baseline(artifact)
    expected_blockers = {
        "load_soak_attestation_missing",
        "dependency_recovery_attestation_missing",
        "postgres_saturation_evidence_missing",
        "production_like_resource_attestation_missing",
        "cost_attribution_evidence_missing",
    }
    if set(artifact["certificationBlockers"]) != expected_blockers:
        errors.append("test-profile capacity baseline must preserve non-certification blockers")
    if artifact["certificationReady"] is not False:
        errors.append("test-profile capacity baseline must not be certification-ready")
    if "postgresThresholdProof" not in INPUT_KEYS or "postgresSaturationMeasured" in INPUT_KEYS:
        errors.append(
            "capacity generation must accept proof, not a caller-asserted saturation boolean"
        )
    if "costResourceMeasured" in INPUT_KEYS:
        errors.append("capacity generation must not accept caller-asserted cost evidence")
    if "resourceBaseline" not in INPUT_KEYS:
        errors.append("capacity generation must accept governed resource baseline evidence")

    proof = execute_postgres_capacity_threshold_proof(
        stress_port=_ThresholdProofPort(),
        environment_profile="test",
        generated_at_utc=datetime(2026, 7, 11, tzinfo=UTC),
        commit_sha="contract-gate",
        branch="contract-gate",
        run_id="threshold-contract-gate",
        maximum_load_connections=5,
    )
    linked = build_service_capacity_baseline(
        measurements=measurements,
        environment_profile="production-like",
        generated_at_utc=datetime(2026, 7, 11, tzinfo=UTC),
        commit_sha="contract-gate",
        branch="contract-gate",
        run_id="contract-gate",
        observed_window_seconds=1.0,
        postgres_threshold_proof=proof,
    )
    resource = linked["resourceEvidence"]
    if resource["postgresThresholdProofValidated"] is not True:
        errors.append("matching controlled test threshold proof must validate")
    if resource["postgresSaturationMeasured"] is not False:
        errors.append("controlled test proof must not satisfy saturation certification")
    if "postgres_saturation_evidence_missing" not in linked["certificationBlockers"]:
        errors.append("controlled test proof must preserve the saturation blocker")
    return errors


def main() -> int:
    errors = validate_contract()
    if errors:
        print("Service capacity baseline contract gate failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Service capacity baseline contract gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
