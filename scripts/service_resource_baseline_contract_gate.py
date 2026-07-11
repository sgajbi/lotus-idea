from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app.application.service_resource_baseline import (  # noqa: E402
    build_service_resource_baseline,
    validate_service_resource_baseline,
)
from app.ports.resource_probe import ProcessResourceSnapshot  # noqa: E402


def validate_contract() -> list[str]:
    started_at = datetime(2026, 7, 11, 8, 0, tzinfo=UTC)
    artifact = build_service_resource_baseline(
        snapshots=[
            ProcessResourceSnapshot(started_at, 1.0, 100, 200, 5, 100),
            ProcessResourceSnapshot(started_at + timedelta(seconds=10), 2.0, 200, 300, 6, 100),
        ],
        environment_profile="test",
        generated_at_utc=started_at + timedelta(seconds=11),
        commit_sha="contract-gate",
        branch="contract-gate",
        run_id="contract-gate",
    )
    errors = validate_service_resource_baseline(artifact)
    expected_blockers = {
        "production_like_resource_attestation_missing",
        "cost_attribution_evidence_missing",
    }
    if set(artifact["certificationBlockers"]) != expected_blockers:
        errors.append("resource baseline must preserve production-like and cost blockers")
    if artifact["costAttributionVerified"] is not False:
        errors.append("resource baseline must not infer cost evidence from process metrics")
    if artifact["certificationReady"] is not False:
        errors.append("controlled resource baseline must remain non-certifying")
    return errors


def main() -> int:
    errors = validate_contract()
    if errors:
        print("Service resource baseline contract gate failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Service resource baseline contract gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
