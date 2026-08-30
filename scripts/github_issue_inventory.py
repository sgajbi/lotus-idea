from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RepositoryIssueCounts:
    total: int
    open: int
    labeled: int | None


def fetch_repository_issue_counts(
    *,
    repository: str,
    label: str | None = None,
) -> RepositoryIssueCounts:
    owner, name = _repository_identity(repository)
    labeled_selection = (
        f"labeled: issues(labels: [{json.dumps(label)}]) {{ totalCount }}"
        if label is not None
        else ""
    )
    query = " ".join(
        (
            "query($owner: String!, $name: String!) {",
            "repository(owner: $owner, name: $name) {",
            "total: issues { totalCount }",
            "open: issues(states: OPEN) { totalCount }",
            labeled_selection,
            "}",
            "}",
        )
    )
    result = subprocess.run(
        [
            "gh",
            "api",
            "graphql",
            "--field",
            f"owner={owner}",
            "--field",
            f"name={name}",
            "--raw-field",
            f"query={query}",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"GitHub repository issue-count query failed: {stderr}")
    payload = json.loads(result.stdout)
    try:
        repository_payload = payload["data"]["repository"]
        total = repository_payload["total"]["totalCount"]
        open_count = repository_payload["open"]["totalCount"]
        labeled = repository_payload["labeled"]["totalCount"] if label is not None else None
    except (KeyError, TypeError) as exc:
        raise ValueError("GitHub repository issue-count query returned an invalid payload") from exc
    for field, value in (("total", total), ("open", open_count), ("labeled", labeled)):
        if value is not None and (not isinstance(value, int) or value < 0):
            raise ValueError(
                f"GitHub repository issue-count query returned an invalid {field} count"
            )
    if open_count > total:
        raise ValueError("GitHub repository open issue count cannot exceed total issue count")
    if labeled is not None and labeled > total:
        raise ValueError("GitHub repository labeled issue count cannot exceed total issue count")
    return RepositoryIssueCounts(total=total, open=open_count, labeled=labeled)


def fetch_complete_issue_list(
    *,
    repository: str,
    state: str,
    fields: str,
    expected_count: int,
    label: str | None = None,
) -> list[dict[str, Any]]:
    if state not in {"all", "open", "closed"}:
        raise ValueError("GitHub issue-list state must be all, open, or closed")
    if expected_count < 0:
        raise ValueError("GitHub issue-list expected count must be zero or greater")
    if expected_count == 0:
        return []
    command = [
        "gh",
        "issue",
        "list",
        "--repo",
        repository,
        "--state",
        state,
        "--limit",
        str(expected_count),
        "--json",
        fields,
    ]
    if label is not None:
        command.extend(["--label", label])
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"gh issue list failed for {repository}: {stderr}")
    payload = json.loads(result.stdout)
    if not isinstance(payload, list):
        raise ValueError(f"gh issue list for {repository} returned non-list JSON")
    if len(payload) != expected_count:
        qualifier = f" with label {label}" if label is not None else ""
        raise RuntimeError(
            f"gh issue list returned {len(payload)} {state} issues{qualifier} for "
            f"{repository}, but GitHub reports {expected_count}; complete pagination is required"
        )
    return payload


def _repository_identity(repository: str) -> tuple[str, str]:
    owner, separator, name = repository.partition("/")
    if separator != "/" or not owner or not name or "/" in name:
        raise ValueError("repository must use owner/name form")
    return owner, name
