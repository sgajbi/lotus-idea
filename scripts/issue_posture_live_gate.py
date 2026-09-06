"""Validate complete live RFC-0002 posture without mirroring volatile state."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from cross_repo_issue_posture import (
    DEFAULT_BLOCKER_CLASSIFICATION_PATH,
    DEFAULT_REPOSITORIES,
    build_cross_repo_issue_posture,
)


GOVERNED_OPEN_STATUS_LABELS = frozenset(
    {
        "status/blocked",
        "status/fixed-local",
        "status/in-progress",
        "status/merged-main",
        "status/merged-to-main",
        "status/pr-open",
        "status/ready",
        "status/tracker",
    }
)


def live_posture_errors(
    *,
    repositories: Sequence[str] = DEFAULT_REPOSITORIES,
    fixture_path: Path | None = None,
    blocker_classification_path: Path | None = DEFAULT_BLOCKER_CLASSIFICATION_PATH,
) -> list[str]:
    live = build_cross_repo_issue_posture(
        repositories=repositories,
        fixture_path=fixture_path,
        blocker_classification_path=blocker_classification_path,
    )
    return _live_posture_errors(live=live, expected_repository_count=len(repositories))


def _live_posture_errors(
    *,
    live: Mapping[str, Any],
    expected_repository_count: int,
) -> list[str]:
    counts = _required_mapping(live, "counts", owner="live RFC-0002 posture")
    blocked = _required_mapping(live, "blockedActionability", owner="live RFC-0002 posture")
    errors = _count_errors(counts=counts, expected_repository_count=expected_repository_count)
    errors.extend(_open_issue_lifecycle_errors(live))
    app_actionable = _non_negative_int(
        blocked,
        "appActionableBlockedIssueCount",
        owner="live blocked posture",
    )
    if app_actionable:
        errors.append(
            "RFC-0002 live posture contains "
            f"{app_actionable} app-actionable issue(s) incorrectly marked blocked"
        )
    return errors


def _count_errors(
    *,
    counts: Mapping[str, Any],
    expected_repository_count: int,
) -> list[str]:
    repository_count = _non_negative_int(counts, "repositories", owner="live counts")
    total = _non_negative_int(counts, "totalRfc0002Issues", owner="live counts")
    open_count = _non_negative_int(counts, "openRfc0002Issues", owner="live counts")
    closed_count = _non_negative_int(counts, "closedRfc0002Issues", owner="live counts")
    errors: list[str] = []
    if repository_count != expected_repository_count:
        errors.append(
            "RFC-0002 live posture repository count "
            f"{repository_count} does not match requested repository count "
            f"{expected_repository_count}"
        )
    if open_count + closed_count != total:
        errors.append(
            "RFC-0002 live posture open/closed counts do not sum to total issues: "
            f"open={open_count}, closed={closed_count}, total={total}"
        )
    return errors


def _open_issue_lifecycle_errors(live: Mapping[str, Any]) -> list[str]:
    raw_repositories = live.get("repositories")
    if not isinstance(raw_repositories, list):
        raise ValueError("live RFC-0002 posture repositories must be a list")
    errors: list[str] = []
    projected_open_count = 0
    for raw_repository in raw_repositories:
        repository = _required_repository_name(raw_repository)
        raw_issues = raw_repository.get("openRfc0002Issues")
        if not isinstance(raw_issues, list):
            raise ValueError(f"{repository}: openRfc0002Issues must be a list")
        projected_open_count += len(raw_issues)
        errors.extend(_repository_lifecycle_errors(repository, raw_issues))

    counts = _required_mapping(live, "counts", owner="live RFC-0002 posture")
    aggregate_open_count = _non_negative_int(
        counts,
        "openRfc0002Issues",
        owner="live counts",
    )
    if projected_open_count != aggregate_open_count:
        errors.append(
            "RFC-0002 live posture projected open issues do not match aggregate count: "
            f"projected={projected_open_count}, aggregate={aggregate_open_count}"
        )
    return errors


def _repository_lifecycle_errors(
    repository: str,
    raw_issues: Sequence[object],
) -> list[str]:
    errors: list[str] = []
    for index, raw_issue in enumerate(raw_issues):
        if not isinstance(raw_issue, Mapping):
            raise ValueError(f"{repository}: open issue projection {index} must be an object")
        number = raw_issue.get("number")
        status = raw_issue.get("status")
        if not isinstance(number, int) or isinstance(number, bool):
            raise ValueError(f"{repository}: open issue projection {index} has invalid number")
        if not isinstance(status, str):
            raise ValueError(f"{repository}#{number}: open issue status must be a string")
        status_labels = status.split(",") if status else []
        if len(status_labels) != 1:
            errors.append(
                f"{repository}#{number}: open RFC-0002 issue requires exactly one "
                f"status/* lifecycle label; found {status or 'none'}"
            )
            continue
        if status not in GOVERNED_OPEN_STATUS_LABELS:
            errors.append(
                f"{repository}#{number}: open RFC-0002 issue has ungoverned lifecycle "
                f"label {status}"
            )
    return errors


def _required_mapping(
    payload: Mapping[str, Any],
    field: str,
    *,
    owner: str,
) -> Mapping[str, Any]:
    value = payload.get(field)
    if not isinstance(value, Mapping):
        raise ValueError(f"{owner}.{field} must be an object")
    return value


def _required_repository_name(raw_repository: object) -> str:
    if not isinstance(raw_repository, Mapping):
        raise ValueError("live RFC-0002 posture repository item must be an object")
    repository = raw_repository.get("repository")
    if not isinstance(repository, str) or not repository:
        raise ValueError("live RFC-0002 posture repository name must be a string")
    return repository


def _non_negative_int(payload: Mapping[str, Any], field: str, *, owner: str) -> int:
    value = payload.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"RFC-0002 posture {owner}.{field} must be a non-negative integer")
    return value


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fail when complete live RFC-0002 posture has invalid lifecycle labels, "
            "incomplete counts, or app-actionable blocked work."
        )
    )
    parser.add_argument("--fixture-json", type=Path)
    parser.add_argument(
        "--blocker-classification-json",
        type=Path,
        default=DEFAULT_BLOCKER_CLASSIFICATION_PATH,
    )
    parser.add_argument("--repo", action="append", dest="repositories")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repositories = tuple(args.repositories) if args.repositories else DEFAULT_REPOSITORIES
    try:
        errors = live_posture_errors(
            repositories=repositories,
            fixture_path=args.fixture_json,
            blocker_classification_path=args.blocker_classification_json,
        )
    except (json.JSONDecodeError, OSError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("RFC-0002 live issue-posture gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
