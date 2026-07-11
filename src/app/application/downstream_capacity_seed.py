from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
import hashlib

from app.ports.downstream_capacity_seed import DownstreamCapacitySeedPort


LIFECYCLE_SEQUENCE = ("enriched", "scored", "governance_checked", "ready_for_review")
SYNTHETIC_CAPACITY_NAMESPACE = "CAPACITY_SYNTHETIC_PORTFOLIO_001"


@dataclass(frozen=True)
class SeedDownstreamCapacityResourceCommand:
    run_id: str
    as_of_date: date
    seeded_at_utc: datetime

    def __post_init__(self) -> None:
        if not self.run_id.strip():
            raise ValueError("run_id must not be blank")
        if self.seeded_at_utc.tzinfo is None or self.seeded_at_utc.utcoffset() is None:
            raise ValueError("seeded_at_utc must be timezone-aware")


@dataclass(frozen=True)
class DownstreamCapacitySeedResult:
    conversion_intent_id: str
    downstream_submission_path: str


def seed_downstream_capacity_resource(
    command: SeedDownstreamCapacityResourceCommand,
    *,
    port: DownstreamCapacitySeedPort,
) -> DownstreamCapacitySeedResult:
    seed_key = hashlib.sha256(command.run_id.encode("utf-8")).hexdigest()[:16]
    candidate_id = port.persist_candidate(
        seed_key=seed_key,
        as_of_date=command.as_of_date,
        seeded_at_utc=command.seeded_at_utc,
    )
    for index, target_status in enumerate(LIFECYCLE_SEQUENCE, start=1):
        port.transition_candidate(
            candidate_id=candidate_id,
            seed_key=seed_key,
            target_status=target_status,
            changed_at_utc=command.seeded_at_utc + timedelta(minutes=index),
        )
    port.approve_candidate(
        candidate_id=candidate_id,
        seed_key=seed_key,
        decided_at_utc=command.seeded_at_utc + timedelta(minutes=5),
    )
    conversion_intent_id = f"capacity-conversion-{seed_key}"
    port.record_conversion_intent(
        candidate_id=candidate_id,
        conversion_intent_id=conversion_intent_id,
        seed_key=seed_key,
        requested_at_utc=command.seeded_at_utc + timedelta(minutes=6),
    )
    return DownstreamCapacitySeedResult(
        conversion_intent_id=conversion_intent_id,
        downstream_submission_path=(
            f"/api/v1/conversion-intents/{conversion_intent_id}/downstream-submissions"
        ),
    )


def build_downstream_capacity_seed_artifact(
    result: DownstreamCapacitySeedResult,
    *,
    generated_at_utc: datetime,
    commit_sha: str,
    branch: str,
    run_id: str,
) -> dict[str, object]:
    if generated_at_utc.tzinfo is None or generated_at_utc.utcoffset() is None:
        raise ValueError("generated_at_utc must be timezone-aware")
    for name, value in (("commit_sha", commit_sha), ("branch", branch), ("run_id", run_id)):
        if not value.strip():
            raise ValueError(f"{name} must not be blank")
    return {
        "schemaVersion": "lotus-idea.downstream-capacity-seed.v1",
        "repository": "lotus-idea",
        "proofScope": "synthetic_downstream_capacity_resource_seed",
        "claimPosture": "seed_only_not_capacity_evidence",
        "generatedAtUtc": generated_at_utc.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "commitSha": commit_sha,
        "branch": branch,
        "runId": run_id,
        "syntheticResource": True,
        "syntheticNamespace": SYNTHETIC_CAPACITY_NAMESPACE,
        "conversionIntentId": result.conversion_intent_id,
        "downstreamSubmissionPath": result.downstream_submission_path,
        "productionCapacityCertified": False,
        "supportedFeaturePromoted": False,
    }
