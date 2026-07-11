from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app.application.service_capacity_baseline import (  # noqa: E402
    CapacityMeasurement,
    SCENARIOS,
    build_service_capacity_baseline,
    validate_service_capacity_baseline,
)


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
        "production_like_environment_missing",
        "minimum_sample_volume_missing",
        "minimum_soak_window_missing",
        "postgres_saturation_evidence_missing",
        "cost_resource_evidence_missing",
    }
    if set(artifact["certificationBlockers"]) != expected_blockers:
        errors.append("test-profile capacity baseline must preserve non-certification blockers")
    if artifact["certificationReady"] is not False:
        errors.append("test-profile capacity baseline must not be certification-ready")
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
