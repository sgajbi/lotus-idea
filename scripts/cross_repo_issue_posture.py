from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_REPOSITORIES = (
    "sgajbi/lotus-idea",
    "sgajbi/lotus-core",
    "sgajbi/lotus-performance",
    "sgajbi/lotus-risk",
    "sgajbi/lotus-advise",
    "sgajbi/lotus-manage",
    "sgajbi/lotus-report",
    "sgajbi/lotus-render",
    "sgajbi/lotus-archive",
    "sgajbi/lotus-ai",
    "sgajbi/lotus-platform",
    "sgajbi/lotus-gateway",
    "sgajbi/lotus-workbench",
)

EXPECTED_RFC_LABEL = "rfc/RFC-0002"
GITHUB_ISSUE_FIELDS = "number,state,title,labels,url,updatedAt"
STATUS_PREFIXES = ("status/", "status:")
PRIORITY_PREFIXES = ("priority/", "priority:")
RFC_SLICE_PREFIX = "rfc/RFC-0002/slice-"


@dataclass(frozen=True)
class IssueSnapshot:
    repository: str
    number: int
    state: str
    title: str
    url: str
    updated_at: str
    labels: frozenset[str]

    @property
    def status_labels(self) -> tuple[str, ...]:
        return tuple(sorted(_labels_with_prefixes(self.labels, STATUS_PREFIXES)))

    @property
    def priority_labels(self) -> tuple[str, ...]:
        return tuple(sorted(_labels_with_prefixes(self.labels, PRIORITY_PREFIXES)))

    @property
    def slice_labels(self) -> tuple[str, ...]:
        return tuple(sorted(label for label in self.labels if label.startswith(RFC_SLICE_PREFIX)))


def build_cross_repo_issue_posture(
    *,
    repositories: Sequence[str] = DEFAULT_REPOSITORIES,
    fixture_path: Path | None = None,
    limit: int = 1000,
) -> dict[str, Any]:
    repo_payloads = (
        load_fixture_payload(fixture_path)
        if fixture_path is not None
        else fetch_repository_payloads(
            repositories=repositories,
            limit=limit,
        )
    )

    repo_summaries: list[dict[str, Any]] = []
    all_rfc_issues: list[IssueSnapshot] = []
    total_open_issues = 0

    for repository in repositories:
        repo_payload = _repo_payload(repo_payloads, repository)
        open_issue_count = _open_issue_count(repo_payload)
        rfc_issues = _parse_issues(repository, repo_payload["rfc0002Issues"])
        all_rfc_issues.extend(rfc_issues)
        total_open_issues += open_issue_count
        repo_summaries.append(_repository_summary(repository, open_issue_count, rfc_issues))

    return {
        "schemaVersion": "lotus-idea:rfc0002-cross-repo-issue-posture:v1",
        "rfcId": "RFC-0002",
        "source": {
            "type": "github",
            "repositories": list(repositories),
            "rfcLabel": EXPECTED_RFC_LABEL,
        },
        "counts": _aggregate_counts(repo_summaries),
        "repositories": repo_summaries,
        "openAttentionIssues": _attention_issues(all_rfc_issues),
        "usageBoundary": (
            "This is live GitHub issue posture for RFC-0002 execution coordination. "
            "It is not product-support evidence, implementation proof, or a substitute "
            "for repo-local ledgers and exact-main validation."
        ),
        "totalOpenIssuesAcrossRepositories": total_open_issues,
    }


def fetch_repository_payloads(*, repositories: Sequence[str], limit: int) -> dict[str, Any]:
    return {
        repository: {
            "openIssues": _fetch_issues(repository=repository, state="open", limit=limit),
            "rfc0002Issues": _fetch_issues(
                repository=repository,
                state="all",
                limit=limit,
                label=EXPECTED_RFC_LABEL,
            ),
        }
        for repository in repositories
    }


def load_fixture_payload(path: Path | None) -> dict[str, Any]:
    if path is None:
        raise ValueError("fixture path is required")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("cross-repo issue posture fixture must be a JSON object")
    return payload


def render_markdown(summary: Mapping[str, Any]) -> str:
    counts = summary["counts"]
    lines = [
        f"# {summary['rfcId']} Cross-Repo Issue Posture",
        "",
        f"- Repositories checked: {counts['repositories']}",
        f"- Total open issues across repositories: {summary['totalOpenIssuesAcrossRepositories']}",
        f"- Open RFC-0002 issues: {counts['openRfc0002Issues']}",
        f"- Closed RFC-0002 issues: {counts['closedRfc0002Issues']}",
        f"- Total RFC-0002 issues: {counts['totalRfc0002Issues']}",
        "",
        "## Open RFC-0002 Status Counts",
        "",
    ]
    lines.extend(
        f"- `{status}`: {count}"
        for status, count in sorted(counts["openRfc0002IssuesByStatus"].items())
    )
    lines.extend(["", "## Repository Summary", ""])
    lines.append("| Repository | Open issues | Open RFC-0002 | Closed RFC-0002 | Status posture |")
    lines.append("| --- | ---: | ---: | ---: | --- |")
    for repo_summary in summary["repositories"]:
        status_posture = _format_status_counts(repo_summary["openRfc0002IssuesByStatus"])
        lines.append(
            "| "
            f"`{repo_summary['repository']}` | "
            f"{repo_summary['openIssueCount']} | "
            f"{repo_summary['openRfc0002IssueCount']} | "
            f"{repo_summary['closedRfc0002IssueCount']} | "
            f"{status_posture} |"
        )
    lines.extend(["", "## Attention Issues", ""])
    attention_issues = summary["openAttentionIssues"]
    if not attention_issues:
        lines.append("_None._")
    else:
        for issue in attention_issues:
            lines.append(
                f"- `{issue['repository']}#{issue['number']}` "
                f"`{issue['status']}` {issue['title']} - {issue['url']}"
            )
    lines.extend(["", "## Usage Boundary", "", str(summary["usageBoundary"])])
    return "\n".join(lines).rstrip() + "\n"


def _fetch_issues(
    *,
    repository: str,
    state: str,
    limit: int,
    label: str | None = None,
) -> list[dict[str, Any]]:
    command = [
        "gh",
        "issue",
        "list",
        "--repo",
        repository,
        "--state",
        state,
        "--limit",
        str(limit),
        "--json",
        GITHUB_ISSUE_FIELDS,
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
    return payload


def _repo_payload(repo_payloads: Mapping[str, Any], repository: str) -> Mapping[str, Any]:
    raw_repo_payload = repo_payloads.get(repository)
    if not isinstance(raw_repo_payload, Mapping):
        raise ValueError(f"fixture is missing repository payload for {repository}")
    raw_open = raw_repo_payload.get("openIssues")
    raw_rfc = raw_repo_payload.get("rfc0002Issues")
    if not isinstance(raw_open, list):
        raise ValueError(f"{repository}: openIssues must be a list")
    if not isinstance(raw_rfc, list):
        raise ValueError(f"{repository}: rfc0002Issues must be a list")
    return raw_repo_payload


def _open_issue_count(repo_payload: Mapping[str, Any]) -> int:
    open_issues = repo_payload["openIssues"]
    if not isinstance(open_issues, list):
        raise ValueError("openIssues must be a list")
    return len(open_issues)


def _parse_issues(repository: str, payload: Sequence[Mapping[str, Any]]) -> list[IssueSnapshot]:
    return [_parse_issue(repository, raw_issue, index) for index, raw_issue in enumerate(payload)]


def _parse_issue(repository: str, raw_issue: Mapping[str, Any], index: int) -> IssueSnapshot:
    number = raw_issue.get("number")
    state = raw_issue.get("state")
    title = raw_issue.get("title")
    url = raw_issue.get("url")
    updated_at = raw_issue.get("updatedAt")
    labels = raw_issue.get("labels")
    if not isinstance(number, int):
        raise ValueError(f"{repository}: issue item {index} has non-integer number")
    if state not in {"OPEN", "CLOSED"}:
        raise ValueError(f"{repository}#{number}: invalid state")
    if not isinstance(title, str):
        raise ValueError(f"{repository}#{number}: invalid title")
    if not isinstance(url, str):
        raise ValueError(f"{repository}#{number}: invalid url")
    if not isinstance(updated_at, str):
        raise ValueError(f"{repository}#{number}: invalid updatedAt")
    if not isinstance(labels, list):
        raise ValueError(f"{repository}#{number}: invalid labels")
    return IssueSnapshot(
        repository=repository,
        number=number,
        state=state,
        title=title,
        url=url,
        updated_at=updated_at,
        labels=frozenset(_label_names(labels, repository=repository, issue_number=number)),
    )


def _label_names(
    labels: Sequence[object],
    *,
    repository: str,
    issue_number: int,
) -> tuple[str, ...]:
    names: list[str] = []
    for index, raw_label in enumerate(labels):
        if not isinstance(raw_label, Mapping):
            raise ValueError(f"{repository}#{issue_number}: label {index} is not an object")
        name = raw_label.get("name")
        if not isinstance(name, str):
            raise ValueError(f"{repository}#{issue_number}: label {index} has invalid name")
        names.append(name)
    return tuple(names)


def _repository_summary(
    repository: str,
    open_issue_count: int,
    rfc_issues: Sequence[IssueSnapshot],
) -> dict[str, Any]:
    open_rfc_issues = [issue for issue in rfc_issues if issue.state == "OPEN"]
    closed_rfc_issues = [issue for issue in rfc_issues if issue.state == "CLOSED"]
    return {
        "repository": repository,
        "openIssueCount": open_issue_count,
        "totalRfc0002IssueCount": len(rfc_issues),
        "openRfc0002IssueCount": len(open_rfc_issues),
        "closedRfc0002IssueCount": len(closed_rfc_issues),
        "openRfc0002IssuesByStatus": _status_counts(open_rfc_issues),
        "openRfc0002Issues": [_issue_projection(issue) for issue in open_rfc_issues],
    }


def _aggregate_counts(repo_summaries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    status_counter: Counter[str] = Counter()
    open_rfc_count = 0
    closed_rfc_count = 0
    total_rfc_count = 0
    for repo_summary in repo_summaries:
        open_rfc_count += int(repo_summary["openRfc0002IssueCount"])
        closed_rfc_count += int(repo_summary["closedRfc0002IssueCount"])
        total_rfc_count += int(repo_summary["totalRfc0002IssueCount"])
        status_counter.update(repo_summary["openRfc0002IssuesByStatus"])
    return {
        "repositories": len(repo_summaries),
        "totalRfc0002Issues": total_rfc_count,
        "openRfc0002Issues": open_rfc_count,
        "closedRfc0002Issues": closed_rfc_count,
        "openRfc0002IssuesByStatus": dict(sorted(status_counter.items())),
    }


def _status_counts(issues: Sequence[IssueSnapshot]) -> dict[str, int]:
    counter: Counter[str] = Counter(_status_key(issue) for issue in issues)
    return dict(sorted(counter.items()))


def _status_key(issue: IssueSnapshot) -> str:
    if not issue.status_labels:
        return "status/unlabeled"
    return ",".join(issue.status_labels)


def _issue_projection(issue: IssueSnapshot) -> dict[str, Any]:
    return {
        "number": issue.number,
        "title": issue.title,
        "url": issue.url,
        "updatedAt": issue.updated_at,
        "status": _status_key(issue),
        "priorityLabels": list(issue.priority_labels),
        "sliceLabels": list(issue.slice_labels),
    }


def _attention_issues(issues: Sequence[IssueSnapshot]) -> list[dict[str, Any]]:
    attention_statuses = {
        "status/fixed-local",
        "status/in-progress",
        "status/merged-main",
        "status/pr-open",
        "status/ready",
    }
    open_attention = [
        issue
        for issue in issues
        if issue.state == "OPEN" and set(issue.status_labels).intersection(attention_statuses)
    ]
    return [
        _issue_projection(issue) | {"repository": issue.repository.removeprefix("sgajbi/")}
        for issue in sorted(open_attention, key=lambda item: (item.repository, item.number))
    ]


def _labels_with_prefixes(labels: frozenset[str], prefixes: Sequence[str]) -> list[str]:
    return [label for label in labels if label.startswith(tuple(prefixes))]


def _format_status_counts(status_counts: Mapping[str, int]) -> str:
    if not status_counts:
        return "_none_"
    return "; ".join(f"`{status}` {count}" for status, count in sorted(status_counts.items()))


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize live cross-repo GitHub issue posture for Lotus Idea RFC-0002."
    )
    parser.add_argument(
        "--repo",
        action="append",
        dest="repositories",
        help="Repository in owner/name form. Defaults to the governed RFC-0002 repo set.",
    )
    parser.add_argument("--fixture-json", type=Path)
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repositories = tuple(args.repositories) if args.repositories else DEFAULT_REPOSITORIES
    try:
        summary = build_cross_repo_issue_posture(
            repositories=repositories,
            fixture_path=args.fixture_json,
            limit=args.limit,
        )
        rendered = (
            json.dumps(summary, indent=2, sort_keys=True) + "\n"
            if args.format == "json"
            else render_markdown(summary)
        )
        if args.output is None:
            print(rendered, end="")
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
