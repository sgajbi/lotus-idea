from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence, cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
WORKFLOW_NAME = "main-releasability.yml"


class DispatchError(RuntimeError):
    """Raised when exact-revision dispatch cannot be proven safe."""


class GitHubApiError(DispatchError):
    def __init__(self, *, operation: str, status: int) -> None:
        super().__init__(f"GitHub API {operation} failed with HTTP {status}")
        self.status = status


@dataclass(frozen=True)
class MergedPullRequest:
    repository: str
    merge_commit_sha: str
    commit_count: int
    number: int


class GitHubClient(Protocol):
    def merge_methods(self) -> tuple[bool, bool, bool]: ...

    def dispatch_ref_sha(self, dispatch_ref: str) -> str | None: ...

    def create_dispatch_ref(self, dispatch_ref: str, revision: str) -> None: ...

    def dispatch_workflow(self, dispatch_ref: str, revision: str, pr_number: int) -> None: ...


class GitHubRestClient:
    def __init__(self, *, api_url: str, repository: str, token: str) -> None:
        if not api_url.startswith("https://"):
            raise DispatchError("GITHUB_API_URL must use HTTPS")
        if not REPOSITORY.fullmatch(repository):
            raise DispatchError("GITHUB_REPOSITORY must be an owner/repository pair")
        if not token:
            raise DispatchError("GH_TOKEN is required")
        self._api_url = api_url.rstrip("/")
        self._repository = repository
        self._token = token

    def merge_methods(self) -> tuple[bool, bool, bool]:
        payload = self._request_json("GET", f"/repos/{self._repository}")
        if not isinstance(payload, dict):
            raise DispatchError("GitHub repository response must be an object")
        values = (
            payload.get("allow_squash_merge"),
            payload.get("allow_merge_commit"),
            payload.get("allow_rebase_merge"),
        )
        if not all(isinstance(value, bool) for value in values):
            raise DispatchError("GitHub repository merge-method response is incomplete")
        return cast(tuple[bool, bool, bool], values)

    def dispatch_ref_sha(self, dispatch_ref: str) -> str | None:
        encoded_ref = quote(dispatch_ref, safe="")
        payload = self._request_json(
            "GET",
            f"/repos/{self._repository}/git/ref/tags/{encoded_ref}",
            allow_not_found=True,
        )
        if payload is None:
            return None
        if not isinstance(payload, dict) or not isinstance(payload.get("object"), dict):
            raise DispatchError("GitHub dispatch-ref response is incomplete")
        sha = payload["object"].get("sha")
        if not isinstance(sha, str) or not FULL_SHA.fullmatch(sha):
            raise DispatchError("GitHub dispatch-ref response has an invalid SHA")
        return sha

    def create_dispatch_ref(self, dispatch_ref: str, revision: str) -> None:
        self._request_json(
            "POST",
            f"/repos/{self._repository}/git/refs",
            payload={"ref": f"refs/tags/{dispatch_ref}", "sha": revision},
        )

    def dispatch_workflow(self, dispatch_ref: str, revision: str, pr_number: int) -> None:
        workflow = quote(WORKFLOW_NAME, safe="")
        self._request_json(
            "POST",
            f"/repos/{self._repository}/actions/workflows/{workflow}/dispatches",
            payload={
                "ref": dispatch_ref,
                "inputs": {
                    "expected_sha": revision,
                    "triggering_pr": str(pr_number),
                },
            },
        )

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
        allow_not_found: bool = False,
    ) -> Any:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self._api_url}{path}",
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed HTTPS API origin
                body = response.read()
        except HTTPError as exc:
            if allow_not_found and exc.code == 404:
                return None
            raise GitHubApiError(operation=f"{method} {path}", status=exc.code) from exc
        except URLError as exc:
            raise DispatchError(f"GitHub API {method} {path} was unavailable") from exc
        if not body:
            return None
        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise DispatchError(f"GitHub API {method} {path} returned invalid JSON") from exc


RevisionSource = Callable[[str, int], Sequence[str]]


def dispatch_merged_pull_request(
    merged_pr: MergedPullRequest,
    *,
    github: GitHubClient,
    revision_source: RevisionSource,
) -> tuple[str, ...]:
    if github.merge_methods() != (False, False, True):
        raise DispatchError(
            "Repository merge methods must remain rebase-only before per-commit dispatch"
        )

    revisions = tuple(revision_source(merged_pr.merge_commit_sha, merged_pr.commit_count))
    if len(revisions) != merged_pr.commit_count:
        raise DispatchError("Git history did not yield the merged pull request commit count")
    if not revisions or revisions[-1] != merged_pr.merge_commit_sha:
        raise DispatchError("Git history is not anchored to the pull request merge commit")
    if len(set(revisions)) != len(revisions) or any(
        not FULL_SHA.fullmatch(revision) for revision in revisions
    ):
        raise DispatchError("Git history yielded invalid or duplicate revisions")

    for revision in revisions:
        dispatch_ref = f"main-releasability-{revision}"
        existing_sha = github.dispatch_ref_sha(dispatch_ref)
        if existing_sha is None:
            try:
                github.create_dispatch_ref(dispatch_ref, revision)
            except GitHubApiError as exc:
                if exc.status != 422 or github.dispatch_ref_sha(dispatch_ref) != revision:
                    raise
        elif existing_sha != revision:
            raise DispatchError(
                f"Dispatch ref {dispatch_ref} points to {existing_sha}, expected {revision}"
            )
        github.dispatch_workflow(dispatch_ref, revision, merged_pr.number)
    return revisions


def merged_pull_request_from_event(
    event: Mapping[str, Any],
    *,
    repository: str,
) -> MergedPullRequest:
    pull_request = event.get("pull_request")
    if not isinstance(pull_request, dict):
        raise DispatchError("GitHub event must contain a pull_request object")
    base = pull_request.get("base")
    if (
        event.get("action") != "closed"
        or pull_request.get("merged") is not True
        or not isinstance(base, dict)
        or base.get("ref") != "main"
    ):
        raise DispatchError("Dispatcher accepts only merged pull requests targeting main")

    merge_commit_sha = pull_request.get("merge_commit_sha")
    commit_count = pull_request.get("commits")
    number = pull_request.get("number")
    if not isinstance(merge_commit_sha, str) or not FULL_SHA.fullmatch(merge_commit_sha):
        raise DispatchError("pull_request.merge_commit_sha must be a full lowercase Git SHA")
    if isinstance(commit_count, bool) or not isinstance(commit_count, int) or commit_count < 1:
        raise DispatchError("pull_request.commits must be a positive integer")
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        raise DispatchError("pull_request.number must be a positive integer")
    if not REPOSITORY.fullmatch(repository):
        raise DispatchError("GITHUB_REPOSITORY must be an owner/repository pair")
    return MergedPullRequest(
        repository=repository,
        merge_commit_sha=merge_commit_sha,
        commit_count=commit_count,
        number=number,
    )


def git_revisions(merge_commit_sha: str, commit_count: int) -> tuple[str, ...]:
    completed = subprocess.run(
        ["git", "rev-list", "-n", str(commit_count), merge_commit_sha],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise DispatchError("Unable to enumerate merged pull request revisions")
    return tuple(reversed(tuple(line.strip() for line in completed.stdout.splitlines() if line)))


def _load_event(path: str) -> Mapping[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DispatchError("GITHUB_EVENT_PATH must contain valid JSON") from exc
    if not isinstance(payload, dict):
        raise DispatchError("GitHub event payload must be an object")
    return payload


def main() -> int:
    try:
        repository = os.environ.get("GITHUB_REPOSITORY", "")
        event_path = os.environ.get("GITHUB_EVENT_PATH", "")
        if not event_path:
            raise DispatchError("GITHUB_EVENT_PATH is required")
        merged_pr = merged_pull_request_from_event(
            _load_event(event_path),
            repository=repository,
        )
        github = GitHubRestClient(
            api_url=os.environ.get("GITHUB_API_URL", "https://api.github.com"),
            repository=repository,
            token=os.environ.get("GH_TOKEN", ""),
        )
        subprocess.run(
            ["git", "fetch", "origin", "main", "--quiet"],
            check=True,
            capture_output=True,
            text=True,
        )
        revisions = dispatch_merged_pull_request(
            merged_pr,
            github=github,
            revision_source=git_revisions,
        )
    except (DispatchError, subprocess.CalledProcessError) as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1
    for revision in revisions:
        print(f"Dispatched main releasability for {revision} (PR #{merged_pr.number})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
