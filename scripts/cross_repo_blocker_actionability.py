from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

DEFAULT_BLOCKER_CLASSIFICATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "contracts"
    / "implementation-proof"
    / "rfc0002-cross-repo-blocker-classification.v1.json"
)
BLOCKED_STATUS_LABEL = "status/blocked"
VALID_ACTIONABILITY = {"core_dependency", "external_or_protected_evidence"}


def load_blocker_classifications(path: Path) -> dict[tuple[str, int], dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("blocker classification contract must be a JSON object")
    if payload.get("schemaVersion") != "lotus-idea:rfc0002-cross-repo-blocker-classification:v1":
        raise ValueError("blocker classification contract has unsupported schemaVersion")
    classifications = payload.get("classifications")
    if not isinstance(classifications, list):
        raise ValueError("blocker classification contract requires classifications array")
    by_issue: dict[tuple[str, int], dict[str, Any]] = {}
    for index, raw_classification in enumerate(classifications):
        if not isinstance(raw_classification, Mapping):
            raise ValueError(f"blocker classification {index} must be an object")
        classification = _parse_classification(raw_classification, index)
        key = (classification["repository"], classification["issueNumber"])
        if key in by_issue:
            raise ValueError(
                f"duplicate blocker classification for {classification['repository']}"
                f"#{classification['issueNumber']}"
            )
        by_issue[key] = classification
    return by_issue


def blocked_actionability_summary(
    *,
    issues: Sequence[Any],
    classifications: Mapping[tuple[str, int], Mapping[str, Any]],
    issue_projection: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    open_blocked = [
        issue
        for issue in issues
        if issue.state == "OPEN" and BLOCKED_STATUS_LABEL in issue.status_labels
    ]
    _require_complete_classification(
        open_blocked=open_blocked,
        classifications=classifications,
        scoped_repositories={issue.repository for issue in issues},
    )

    actionability_counter: Counter[str] = Counter()
    class_counter: Counter[str] = Counter()
    projections: list[dict[str, Any]] = []
    for issue in sorted(open_blocked, key=lambda item: (item.repository, item.number)):
        classification = classifications[(issue.repository, issue.number)]
        actionability = str(classification["actionability"])
        blocker_class = str(classification["blockerClass"])
        actionability_counter[actionability] += 1
        class_counter[blocker_class] += 1
        projections.append(
            issue_projection(issue)
            | {
                "repository": issue.repository.removeprefix("sgajbi/"),
                "actionability": actionability,
                "blockerClass": blocker_class,
                "remainingAuthority": str(classification["remainingAuthority"]),
            }
        )
    return {
        "openBlockedIssueCount": len(open_blocked),
        "appActionableBlockedIssueCount": 0,
        "openBlockedIssuesByActionability": dict(sorted(actionability_counter.items())),
        "openBlockedIssuesByClass": dict(sorted(class_counter.items())),
        "openBlockedIssues": projections,
        "classificationBoundary": (
            "A zero app-actionable blocked count means current status/blocked issues require "
            "Core owner work, production identity/session authority, protected runtime/deployment "
            "evidence, provider/bank/legal approval, or certification evidence before closure. "
            "If a writable app-code issue is found, it must move out of blocked posture."
        ),
    }


def render_blocked_actionability_markdown(blocked_actionability: Mapping[str, Any]) -> list[str]:
    lines = [
        "",
        "## Blocked RFC-0002 Actionability",
        "",
        f"- Open blocked issues: {blocked_actionability['openBlockedIssueCount']}",
        f"- App-actionable blocked issues: {blocked_actionability['appActionableBlockedIssueCount']}",
        "",
        "### Blocked Issues By Actionability",
        "",
    ]
    lines.extend(
        f"- `{actionability}`: {count}"
        for actionability, count in sorted(
            blocked_actionability["openBlockedIssuesByActionability"].items()
        )
    )
    lines.extend(["", "### Blocked Issues By Class", ""])
    lines.extend(
        f"- `{blocker_class}`: {count}"
        for blocker_class, count in sorted(
            blocked_actionability["openBlockedIssuesByClass"].items()
        )
    )
    lines.extend(["", "### Blocked Issue Detail", ""])
    blocked_issues = blocked_actionability.get("openBlockedIssues", [])
    if not blocked_issues:
        lines.append("_None._")
    else:
        lines.extend(_blocked_issue_detail_lines(blocked_issues))

    classification_boundary = blocked_actionability.get("classificationBoundary")
    if classification_boundary:
        lines.extend(["", "Classification boundary: " + str(classification_boundary)])
    return lines


def _parse_classification(raw_classification: Mapping[str, Any], index: int) -> dict[str, Any]:
    repository = raw_classification.get("repository")
    issue_number = raw_classification.get("issueNumber")
    actionability = raw_classification.get("actionability")
    blocker_class = raw_classification.get("blockerClass")
    remaining_authority = raw_classification.get("remainingAuthority")
    if not isinstance(repository, str) or "/" not in repository:
        raise ValueError(f"blocker classification {index} has invalid repository")
    if not isinstance(issue_number, int):
        raise ValueError(f"blocker classification {index} has invalid issueNumber")
    if actionability not in VALID_ACTIONABILITY:
        raise ValueError(
            f"{repository}#{issue_number}: invalid blocker actionability {actionability!r}"
        )
    if not isinstance(blocker_class, str) or not blocker_class:
        raise ValueError(f"{repository}#{issue_number}: blockerClass is required")
    if not isinstance(remaining_authority, str) or not remaining_authority:
        raise ValueError(f"{repository}#{issue_number}: remainingAuthority is required")
    return dict(raw_classification)


def _blocked_issue_detail_lines(blocked_issues: Sequence[Mapping[str, Any]]) -> list[str]:
    return [
        (
            f"- `{issue['actionability']}` / `{issue['blockerClass']}`: "
            f"`{issue['repository']}#{issue['number']}` {issue['title']} - "
            f"{issue['url']}; remaining authority: {issue['remainingAuthority']}"
        )
        for issue in sorted(
            blocked_issues,
            key=lambda item: (item["actionability"], item["repository"], item["number"]),
        )
    ]


def _require_complete_classification(
    *,
    open_blocked: Sequence[Any],
    classifications: Mapping[tuple[str, int], Mapping[str, Any]],
    scoped_repositories: set[str],
) -> None:
    missing = [
        f"{issue.repository}#{issue.number}"
        for issue in open_blocked
        if (issue.repository, issue.number) not in classifications
    ]
    if missing:
        raise ValueError(
            "open blocked RFC-0002 issues missing blocker classification: "
            + ", ".join(sorted(missing))
        )
    stale = [
        f"{repository}#{issue_number}"
        for repository, issue_number in classifications
        if repository in scoped_repositories
        if not any(
            issue.repository == repository
            and issue.number == issue_number
            and issue.state == "OPEN"
            and BLOCKED_STATUS_LABEL in issue.status_labels
            for issue in open_blocked
        )
    ]
    if stale:
        raise ValueError(
            "blocker classification contract contains stale non-open-blocked issue(s): "
            + ", ".join(sorted(stale))
        )
