"""Validate published RFC issue posture against complete live GitHub state."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any

from cross_repo_issue_posture import (
    DEFAULT_BLOCKER_CLASSIFICATION_PATH,
    DEFAULT_REPOSITORIES,
    build_cross_repo_issue_posture,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT_PATH = (
    ROOT / "contracts" / "implementation-proof" / "rfc0002-issue-posture-snapshot.v1.json"
)
EXPECTED_SCHEMA_VERSION = "lotus-idea:rfc0002-issue-posture-snapshot:v1"
DEFAULT_MAX_SNAPSHOT_AGE_DAYS = 7


def live_posture_errors(
    *,
    snapshot_path: Path = DEFAULT_SNAPSHOT_PATH,
    repositories: Sequence[str] = DEFAULT_REPOSITORIES,
    fixture_path: Path | None = None,
    blocker_classification_path: Path | None = DEFAULT_BLOCKER_CLASSIFICATION_PATH,
    today: date | None = None,
    max_snapshot_age_days: int = DEFAULT_MAX_SNAPSHOT_AGE_DAYS,
) -> list[str]:
    snapshot = _load_snapshot(snapshot_path)
    live = build_cross_repo_issue_posture(
        repositories=repositories,
        fixture_path=fixture_path,
        blocker_classification_path=blocker_classification_path,
    )
    errors = _snapshot_age_errors(
        snapshot,
        today=today or date.today(),
        max_snapshot_age_days=max_snapshot_age_days,
    )
    errors.extend(_cross_repo_count_errors(snapshot=snapshot, live=live))
    return errors


def _load_snapshot(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: snapshot must be a JSON object")
    if payload.get("schemaVersion") != EXPECTED_SCHEMA_VERSION:
        raise ValueError(f"{path}: schemaVersion must be {EXPECTED_SCHEMA_VERSION}")
    return payload


def _snapshot_age_errors(
    snapshot: Mapping[str, Any],
    *,
    today: date,
    max_snapshot_age_days: int,
) -> list[str]:
    if max_snapshot_age_days < 0:
        raise ValueError("max snapshot age must be zero or greater")
    raw_as_of_date = snapshot.get("asOfDate")
    if not isinstance(raw_as_of_date, str):
        return ["RFC-0002 posture snapshot asOfDate must be an ISO date"]
    try:
        as_of_date = date.fromisoformat(raw_as_of_date)
    except ValueError:
        return ["RFC-0002 posture snapshot asOfDate must be an ISO date"]
    age_days = (today - as_of_date).days
    if age_days < 0:
        return [f"RFC-0002 posture snapshot asOfDate {raw_as_of_date} is in the future"]
    if age_days > max_snapshot_age_days:
        return [
            f"RFC-0002 posture snapshot is {age_days} days old; maximum allowed age is "
            f"{max_snapshot_age_days} days"
        ]
    return []


def _cross_repo_count_errors(
    *,
    snapshot: Mapping[str, Any],
    live: Mapping[str, Any],
) -> list[str]:
    expected = snapshot.get("crossRepo")
    live_counts = live.get("counts")
    live_blocked = live.get("blockedActionability")
    if not isinstance(expected, Mapping):
        return ["RFC-0002 posture snapshot crossRepo must be an object"]
    if not isinstance(live_counts, Mapping) or not isinstance(live_blocked, Mapping):
        raise ValueError("live RFC-0002 posture returned an invalid count payload")

    comparisons = (
        (
            "repositoriesChecked",
            expected.get("repositoriesChecked"),
            live_counts.get("repositories"),
        ),
        (
            "totalRfc0002Issues",
            expected.get("totalRfc0002Issues"),
            live_counts.get("totalRfc0002Issues"),
        ),
        (
            "openRfc0002Issues",
            expected.get("openRfc0002Issues"),
            live_counts.get("openRfc0002Issues"),
        ),
        (
            "closedRfc0002Issues",
            expected.get("closedRfc0002Issues"),
            live_counts.get("closedRfc0002Issues"),
        ),
        (
            "openBlockedIssues",
            expected.get("openBlockedIssues"),
            live_blocked.get("openBlockedIssueCount"),
        ),
        (
            "appActionableBlockedIssues",
            expected.get("appActionableBlockedIssues"),
            live_blocked.get("appActionableBlockedIssueCount"),
        ),
        (
            "openStatusCounts",
            expected.get("openStatusCounts"),
            live_counts.get("openRfc0002IssuesByStatus"),
        ),
        (
            "titleOnlyReferencesExcludedFromGovernedCounts",
            expected.get("titleOnlyReferencesExcludedFromGovernedCounts"),
            _live_title_only_references(live),
        ),
    )
    return [
        f"RFC-0002 posture snapshot crossRepo.{field}={expected_value!r} does not match "
        f"live GitHub posture {actual_value!r}"
        for field, expected_value, actual_value in comparisons
        if expected_value != actual_value
    ]


def _live_title_only_references(live: Mapping[str, Any]) -> list[str]:
    raw_references = live.get("titleOnlyRfc0002References", [])
    if not isinstance(raw_references, list):
        raise ValueError("live RFC-0002 posture title-only references must be a list")
    references: list[str] = []
    for item in raw_references:
        if not isinstance(item, Mapping):
            raise ValueError("live RFC-0002 posture title-only reference must be an object")
        repository = item.get("repository")
        number = item.get("number")
        if not isinstance(repository, str) or not isinstance(number, int):
            raise ValueError("live RFC-0002 posture title-only reference identity is invalid")
        references.append(f"sgajbi/{repository}#{number}")
    return references


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fail when the published RFC-0002 issue-posture snapshot is stale or differs "
            "from live label-backed GitHub issue state."
        )
    )
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT_PATH)
    parser.add_argument("--fixture-json", type=Path)
    parser.add_argument(
        "--blocker-classification-json",
        type=Path,
        default=DEFAULT_BLOCKER_CLASSIFICATION_PATH,
    )
    parser.add_argument(
        "--max-snapshot-age-days",
        type=int,
        default=DEFAULT_MAX_SNAPSHOT_AGE_DAYS,
    )
    parser.add_argument("--repo", action="append", dest="repositories")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repositories = tuple(args.repositories) if args.repositories else DEFAULT_REPOSITORIES
    try:
        errors = live_posture_errors(
            snapshot_path=args.snapshot,
            repositories=repositories,
            fixture_path=args.fixture_json,
            blocker_classification_path=args.blocker_classification_json,
            max_snapshot_age_days=args.max_snapshot_age_days,
        )
    except (json.JSONDecodeError, OSError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("RFC-0002 live issue-posture snapshot gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
