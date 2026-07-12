from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
import os
from pathlib import Path
import sys
from typing import Any

import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app.application.data_lifecycle import ReviewScheduledDataLifecycle  # noqa: E402
from app.domain.data_lifecycle.schedule import (  # noqa: E402
    ScheduledLifecycleBlockerCount,
    ScheduledLifecycleReviewEvidence,
)
from app.infrastructure.data_lifecycle.postgres_schedule import (  # noqa: E402
    PostgresScheduledDataLifecycleRepository,
)
from scripts.disaster_recovery_evidence_io import (  # noqa: E402
    write_dataclass_evidence_atomic,
)

DATABASE_URL_ENV = "LOTUS_IDEA_DATABASE_URL"
DEFAULT_OUTPUT_PATH = ROOT / "output/data-lifecycle/scheduled-review-evidence.json"


def run_scheduled_data_lifecycle_review(
    *,
    database_url: str,
    limit: int,
    output_path: Path,
    execution_profile: str = "review_only",
    now: Any | None = None,
    connect: Any = psycopg.connect,
) -> ScheduledLifecycleReviewEvidence:
    clock = now or (lambda: datetime.now(UTC))
    with connect(database_url, row_factory=dict_row) as connection:
        review = ReviewScheduledDataLifecycle(
            PostgresScheduledDataLifecycleRepository(connection),
            now=clock,
        ).execute(limit=limit)
    blocker_counts = Counter(blocker for item in review.items for blocker in item.blockers)
    evidence = ScheduledLifecycleReviewEvidence(
        schema_version="lotus-idea.scheduled-lifecycle-review-evidence.v1",
        generated_at_utc=review.evaluated_at_utc,
        repository=os.environ.get("GITHUB_REPOSITORY", "local/lotus-idea"),
        git_commit=os.environ.get("GITHUB_SHA", "local-uncommitted"),
        git_ref=os.environ.get("GITHUB_REF", "local"),
        ci_run_id=os.environ.get("GITHUB_RUN_ID", "local"),
        execution_profile=execution_profile,
        requested_limit=review.requested_limit,
        scanned_count=len(review.items),
        ready_for_authorized_purge_count=review.ready_count,
        blocked_count=len(review.items) - review.ready_count,
        blocker_counts=tuple(
            ScheduledLifecycleBlockerCount(blocker=blocker, count=count)
            for blocker, count in sorted(blocker_counts.items(), key=lambda entry: entry[0].value)
        ),
        truncated=review.truncated,
    )
    write_dataclass_evidence_atomic(output_path, evidence)
    return evidence


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Produce a bounded source-safe scheduled lifecycle review artifact"
    )
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument(
        "--execution-profile",
        choices=("review_only", "synthetic_disposable_postgres"),
        default="review_only",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    database_url = os.environ.get(DATABASE_URL_ENV, "").strip()
    if not database_url:
        print(f"Scheduled data lifecycle review requires {DATABASE_URL_ENV}")
        return 1
    try:
        evidence = run_scheduled_data_lifecycle_review(
            database_url=database_url,
            limit=args.limit,
            output_path=args.output_path,
            execution_profile=args.execution_profile,
        )
    except (OSError, TypeError, ValueError, psycopg.Error) as exc:
        print(f"Scheduled data lifecycle review failed: {type(exc).__name__}")
        return 1
    print(
        "Scheduled data lifecycle review completed: "
        f"scanned={evidence.scanned_count}, "
        f"ready={evidence.ready_for_authorized_purge_count}, "
        f"blocked={evidence.blocked_count}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
