"""Validate published RFC issue posture against complete live GitHub state."""

from __future__ import annotations

import argparse
import json
import re
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
DATED_NON_REGRESSION_MODE = "dated_non_regression_v1"
ISSUE_REF_PATTERN = re.compile(r"^sgajbi/[a-z0-9-]+#[1-9][0-9]*$")


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
    _validate_issue_count_partition(expected, owner="snapshot crossRepo")
    _validate_issue_count_partition(live_counts, owner="live counts")
    allowed_statuses = _comparison_policy(snapshot)
    exact_comparisons = (
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
            "titleOnlyReferencesExcludedFromGovernedCounts",
            expected.get("titleOnlyReferencesExcludedFromGovernedCounts"),
            _live_title_only_references(live),
        ),
    )
    errors = [
        f"RFC-0002 posture snapshot crossRepo.{field}={expected_value!r} does not match "
        f"live GitHub posture {actual_value!r}"
        for field, expected_value, actual_value in exact_comparisons
        if expected_value != actual_value
    ]
    errors.extend(
        _non_regression_count_errors(
            expected=expected,
            live_counts=live_counts,
            live_blocked=live_blocked,
        )
    )
    errors.extend(_open_issue_ref_errors(expected=expected, live=live))
    errors.extend(
        _open_status_coverage_errors(
            live_counts=live_counts,
            allowed_statuses=allowed_statuses,
        )
    )
    return errors


def _comparison_policy(snapshot: Mapping[str, Any]) -> frozenset[str]:
    raw_policy = snapshot.get("comparisonPolicy")
    if not isinstance(raw_policy, Mapping):
        raise ValueError("RFC-0002 posture snapshot comparisonPolicy must be an object")
    if raw_policy.get("mode") != DATED_NON_REGRESSION_MODE:
        raise ValueError(
            f"RFC-0002 posture snapshot comparisonPolicy.mode must be {DATED_NON_REGRESSION_MODE}"
        )
    raw_statuses = raw_policy.get("allowedOpenStatusLabels")
    if not isinstance(raw_statuses, list) or not raw_statuses:
        raise ValueError(
            "RFC-0002 posture snapshot comparisonPolicy.allowedOpenStatusLabels "
            "must be a non-empty list"
        )
    if any(
        not isinstance(status, str) or not status.startswith("status/") for status in raw_statuses
    ):
        raise ValueError(
            "RFC-0002 posture snapshot allowed open status labels must use status/* vocabulary"
        )
    if len(raw_statuses) != len(set(raw_statuses)):
        raise ValueError("RFC-0002 posture snapshot allowed open status labels must be unique")
    return frozenset(raw_statuses)


def _non_regression_count_errors(
    *,
    expected: Mapping[str, Any],
    live_counts: Mapping[str, Any],
    live_blocked: Mapping[str, Any],
) -> list[str]:
    comparisons = (
        (
            "openRfc0002Issues",
            _non_negative_int(expected, "openRfc0002Issues", owner="snapshot crossRepo"),
            _non_negative_int(live_counts, "openRfc0002Issues", owner="live counts"),
            "same or fewer open issues",
        ),
        (
            "openBlockedIssues",
            _non_negative_int(expected, "openBlockedIssues", owner="snapshot crossRepo"),
            _non_negative_int(live_blocked, "openBlockedIssueCount", owner="live blocked posture"),
            "same or fewer blocked issues",
        ),
        (
            "appActionableBlockedIssues",
            _non_negative_int(
                expected,
                "appActionableBlockedIssues",
                owner="snapshot crossRepo",
            ),
            _non_negative_int(
                live_blocked,
                "appActionableBlockedIssueCount",
                owner="live blocked posture",
            ),
            "same or fewer app-actionable blocked issues",
        ),
    )
    errors = [
        f"RFC-0002 posture snapshot crossRepo.{field} baseline {baseline} regressed to "
        f"live GitHub posture {actual}; dated snapshot permits only {rule}"
        for field, baseline, actual, rule in comparisons
        if actual > baseline
    ]
    baseline_closed = _non_negative_int(
        expected,
        "closedRfc0002Issues",
        owner="snapshot crossRepo",
    )
    live_closed = _non_negative_int(
        live_counts,
        "closedRfc0002Issues",
        owner="live counts",
    )
    if live_closed < baseline_closed:
        errors.append(
            "RFC-0002 posture snapshot crossRepo.closedRfc0002Issues baseline "
            f"{baseline_closed} regressed to live GitHub posture {live_closed}; dated snapshot "
            "permits only the same or more closed issues"
        )
    return errors


def _non_negative_int(payload: Mapping[str, Any], field: str, *, owner: str) -> int:
    value = payload.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"RFC-0002 posture {owner}.{field} must be a non-negative integer")
    return value


def _validate_issue_count_partition(payload: Mapping[str, Any], *, owner: str) -> None:
    total = _non_negative_int(payload, "totalRfc0002Issues", owner=owner)
    open_count = _non_negative_int(payload, "openRfc0002Issues", owner=owner)
    closed_count = _non_negative_int(payload, "closedRfc0002Issues", owner=owner)
    if open_count + closed_count != total:
        raise ValueError(
            f"RFC-0002 posture {owner} open/closed counts must sum to totalRfc0002Issues"
        )


def _open_issue_ref_errors(
    *,
    expected: Mapping[str, Any],
    live: Mapping[str, Any],
) -> list[str]:
    baseline_refs = _canonical_issue_refs(
        expected.get("openIssueRefs"),
        owner="snapshot crossRepo.openIssueRefs",
    )
    baseline_open_count = _non_negative_int(
        expected,
        "openRfc0002Issues",
        owner="snapshot crossRepo",
    )
    if len(baseline_refs) != baseline_open_count:
        raise ValueError(
            "RFC-0002 posture snapshot crossRepo.openIssueRefs must contain exactly "
            f"{baseline_open_count} baseline identities"
        )
    live_ref_items = _live_open_issue_refs(live)
    live_refs = frozenset(live_ref_items)
    live_counts = live.get("counts")
    if not isinstance(live_counts, Mapping):
        raise ValueError("live RFC-0002 posture counts must be an object")
    live_open_count = _non_negative_int(
        live_counts,
        "openRfc0002Issues",
        owner="live counts",
    )
    if len(live_ref_items) != len(live_refs) or len(live_refs) != live_open_count:
        raise ValueError("live RFC-0002 posture open issue identities must be unique and complete")
    unexpected = sorted(live_refs - baseline_refs)
    if not unexpected:
        return []
    return [
        "RFC-0002 live posture contains newly open or reopened issues outside the dated "
        f"snapshot baseline: {unexpected}"
    ]


def _canonical_issue_refs(raw_refs: object, *, owner: str) -> frozenset[str]:
    if not isinstance(raw_refs, list):
        raise ValueError(f"RFC-0002 posture {owner} must be a list")
    if any(
        not isinstance(ref, str) or ISSUE_REF_PATTERN.fullmatch(ref) is None for ref in raw_refs
    ):
        raise ValueError(f"RFC-0002 posture {owner} contains an invalid canonical issue ref")
    if raw_refs != sorted(raw_refs) or len(raw_refs) != len(set(raw_refs)):
        raise ValueError(f"RFC-0002 posture {owner} must be sorted and unique")
    return frozenset(raw_refs)


def _live_open_issue_refs(live: Mapping[str, Any]) -> list[str]:
    raw_repositories = live.get("repositories")
    if not isinstance(raw_repositories, list):
        raise ValueError("live RFC-0002 posture repositories must be a list")
    refs: list[str] = []
    for raw_repository in raw_repositories:
        if not isinstance(raw_repository, Mapping):
            raise ValueError("live RFC-0002 posture repository item must be an object")
        repository = raw_repository.get("repository")
        raw_issues = raw_repository.get("openRfc0002Issues")
        if not isinstance(repository, str) or not isinstance(raw_issues, list):
            raise ValueError("live RFC-0002 posture repository projection is invalid")
        for raw_issue in raw_issues:
            if not isinstance(raw_issue, Mapping) or not isinstance(raw_issue.get("number"), int):
                raise ValueError("live RFC-0002 posture open issue projection is invalid")
            refs.append(f"{repository}#{raw_issue['number']}")
    return refs


def _open_status_coverage_errors(
    *,
    live_counts: Mapping[str, Any],
    allowed_statuses: frozenset[str],
) -> list[str]:
    raw_status_counts = live_counts.get("openRfc0002IssuesByStatus")
    if not isinstance(raw_status_counts, Mapping):
        raise ValueError("live RFC-0002 posture open status counts must be an object")
    for status, count in raw_status_counts.items():
        if not isinstance(status, str) or not isinstance(count, int) or isinstance(count, bool):
            raise ValueError("live RFC-0002 posture open status counts are invalid")
    unexpected_statuses = sorted(set(raw_status_counts) - allowed_statuses)
    errors = []
    if unexpected_statuses:
        errors.append(
            "RFC-0002 live posture contains ungoverned open lifecycle statuses: "
            f"{unexpected_statuses}"
        )
    live_open = _non_negative_int(live_counts, "openRfc0002Issues", owner="live counts")
    classified_open = sum(raw_status_counts.values())
    if classified_open != live_open:
        errors.append(
            "RFC-0002 live posture lifecycle status coverage does not match open issue count: "
            f"classified={classified_open}, open={live_open}"
        )
    return errors


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
