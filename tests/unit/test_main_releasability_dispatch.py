from __future__ import annotations

import json
from dataclasses import replace
from email.message import Message
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from scripts import main_releasability_dispatch as dispatch_module
from scripts.main_releasability_dispatch import (
    DispatchError,
    GitHubApiError,
    GitHubRestClient,
    MergedPullRequest,
    dispatch_merged_pull_request,
    merged_pull_request_from_event,
)

REVISION_ONE = "1" * 40
REVISION_TWO = "2" * 40


class StubResponse:
    def __init__(self, payload: dict[str, Any] | None) -> None:
        self._body = b"" if payload is None else json.dumps(payload).encode("utf-8")

    def __enter__(self) -> StubResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


class FakeGitHub:
    def __init__(self) -> None:
        self.policy = (False, False, True)
        self.refs: dict[str, str] = {}
        self.created: list[tuple[str, str]] = []
        self.dispatched: list[tuple[str, str, int]] = []
        self.create_error: GitHubApiError | None = None

    def merge_methods(self) -> tuple[bool, bool, bool]:
        return self.policy

    def dispatch_ref_sha(self, dispatch_ref: str) -> str | None:
        return self.refs.get(dispatch_ref)

    def create_dispatch_ref(self, dispatch_ref: str, revision: str) -> None:
        if self.create_error is not None:
            error = self.create_error
            self.create_error = None
            self.refs.setdefault(dispatch_ref, revision)
            raise error
        self.refs[dispatch_ref] = revision
        self.created.append((dispatch_ref, revision))

    def dispatch_workflow(self, dispatch_ref: str, revision: str, pr_number: int) -> None:
        self.dispatched.append((dispatch_ref, revision, pr_number))


def _merged_pr() -> MergedPullRequest:
    return MergedPullRequest(
        repository="sgajbi/lotus-idea",
        merge_commit_sha=REVISION_TWO,
        commit_count=2,
        number=123,
    )


def _event(**overrides: Any) -> dict[str, Any]:
    pull_request: dict[str, Any] = {
        "merged": True,
        "base": {"ref": "main"},
        "merge_commit_sha": REVISION_TWO,
        "commits": 2,
        "number": 123,
    }
    pull_request.update(overrides)
    return {"action": "closed", "pull_request": pull_request}


def test_dispatch_creates_and_dispatches_every_revision_oldest_first() -> None:
    github = FakeGitHub()

    revisions = dispatch_merged_pull_request(
        _merged_pr(),
        github=github,
        revision_source=lambda _sha, _count: (REVISION_ONE, REVISION_TWO),
    )

    assert revisions == (REVISION_ONE, REVISION_TWO)
    assert github.created == [
        (f"main-releasability-{REVISION_ONE}", REVISION_ONE),
        (f"main-releasability-{REVISION_TWO}", REVISION_TWO),
    ]
    assert github.dispatched == [
        (f"main-releasability-{REVISION_ONE}", REVISION_ONE, 123),
        (f"main-releasability-{REVISION_TWO}", REVISION_TWO, 123),
    ]


def test_dispatch_reuses_only_an_exact_existing_ref() -> None:
    github = FakeGitHub()
    dispatch_ref = f"main-releasability-{REVISION_TWO}"
    github.refs[dispatch_ref] = REVISION_TWO

    dispatch_merged_pull_request(
        replace(_merged_pr(), commit_count=1),
        github=github,
        revision_source=lambda _sha, _count: (REVISION_TWO,),
    )

    assert github.created == []
    assert github.dispatched == [(dispatch_ref, REVISION_TWO, 123)]


def test_dispatch_fails_closed_for_an_existing_ref_mismatch() -> None:
    github = FakeGitHub()
    github.refs[f"main-releasability-{REVISION_TWO}"] = REVISION_ONE

    with pytest.raises(DispatchError, match="points to"):
        dispatch_merged_pull_request(
            replace(_merged_pr(), commit_count=1),
            github=github,
            revision_source=lambda _sha, _count: (REVISION_TWO,),
        )

    assert github.dispatched == []


def test_dispatch_accepts_a_same_revision_ref_creation_race() -> None:
    github = FakeGitHub()
    github.create_error = GitHubApiError(operation="create ref", status=422)

    dispatch_merged_pull_request(
        replace(_merged_pr(), commit_count=1),
        github=github,
        revision_source=lambda _sha, _count: (REVISION_TWO,),
    )

    assert github.dispatched == [(f"main-releasability-{REVISION_TWO}", REVISION_TWO, 123)]


def test_dispatch_fails_before_git_or_api_mutation_when_merge_policy_drifts() -> None:
    github = FakeGitHub()
    github.policy = (True, False, True)
    revision_source_called = False

    def revisions(_sha: str, _count: int) -> tuple[str, ...]:
        nonlocal revision_source_called
        revision_source_called = True
        return (REVISION_ONE, REVISION_TWO)

    with pytest.raises(DispatchError, match="rebase-only"):
        dispatch_merged_pull_request(_merged_pr(), github=github, revision_source=revisions)

    assert revision_source_called is False
    assert github.created == []
    assert github.dispatched == []


@pytest.mark.parametrize(
    "revisions",
    [
        (),
        (REVISION_TWO,),
        (REVISION_ONE, REVISION_ONE),
        (REVISION_TWO, REVISION_ONE),
        (REVISION_ONE, "not-a-sha"),
    ],
)
def test_dispatch_fails_closed_for_invalid_revision_sets(revisions: tuple[str, ...]) -> None:
    github = FakeGitHub()

    with pytest.raises(DispatchError):
        dispatch_merged_pull_request(
            _merged_pr(),
            github=github,
            revision_source=lambda _sha, _count: revisions,
        )

    assert github.created == []
    assert github.dispatched == []


@pytest.mark.parametrize(
    ("event", "repository"),
    [
        ({}, "sgajbi/lotus-idea"),
        ({"action": "opened", "pull_request": _event()["pull_request"]}, "sgajbi/lotus-idea"),
        (_event(merged=False), "sgajbi/lotus-idea"),
        (_event(base={"ref": "release"}), "sgajbi/lotus-idea"),
        (_event(merge_commit_sha="short"), "sgajbi/lotus-idea"),
        (_event(commits=0), "sgajbi/lotus-idea"),
        (_event(commits=True), "sgajbi/lotus-idea"),
        (_event(number=0), "sgajbi/lotus-idea"),
        (_event(), "invalid"),
    ],
)
def test_event_contract_rejects_unsafe_or_incomplete_payloads(
    event: dict[str, Any],
    repository: str,
) -> None:
    with pytest.raises(DispatchError):
        merged_pull_request_from_event(event, repository=repository)


def test_event_contract_maps_the_exact_merged_pull_request() -> None:
    assert (
        merged_pull_request_from_event(
            _event(),
            repository="sgajbi/lotus-idea",
        )
        == _merged_pr()
    )


def test_rest_client_uses_exact_github_api_paths_and_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[Request] = []
    responses = iter(
        (
            StubResponse(
                {
                    "allow_squash_merge": False,
                    "allow_merge_commit": False,
                    "allow_rebase_merge": True,
                }
            ),
            StubResponse({"object": {"sha": REVISION_TWO}}),
            StubResponse({"ref": f"refs/tags/main-releasability-{REVISION_TWO}"}),
            StubResponse(None),
        )
    )

    def open_request(request: Request, *, timeout: int) -> StubResponse:
        assert timeout == 30
        requests.append(request)
        return next(responses)

    monkeypatch.setattr(dispatch_module, "urlopen", open_request)
    client = GitHubRestClient(
        api_url="https://api.github.com",
        repository="sgajbi/lotus-idea",
        token="test-token",
    )

    assert client.merge_methods() == (False, False, True)
    assert client.dispatch_ref_sha(f"main-releasability-{REVISION_TWO}") == REVISION_TWO
    client.create_dispatch_ref(f"main-releasability-{REVISION_TWO}", REVISION_TWO)
    client.dispatch_workflow(f"main-releasability-{REVISION_TWO}", REVISION_TWO, 123)

    assert [request.method for request in requests] == ["GET", "GET", "POST", "POST"]
    assert requests[1].full_url.endswith(
        f"/repos/sgajbi/lotus-idea/git/ref/tags/main-releasability-{REVISION_TWO}"
    )
    create_ref_body = requests[2].data
    dispatch_body = requests[3].data
    assert isinstance(create_ref_body, bytes)
    assert isinstance(dispatch_body, bytes)
    assert json.loads(create_ref_body) == {
        "ref": f"refs/tags/main-releasability-{REVISION_TWO}",
        "sha": REVISION_TWO,
    }
    assert json.loads(dispatch_body) == {
        "ref": f"main-releasability-{REVISION_TWO}",
        "inputs": {"expected_sha": REVISION_TWO, "triggering_pr": "123"},
    }


def test_rest_client_distinguishes_absent_refs_from_api_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    status = 404

    def fail_request(request: Request, *, timeout: int) -> StubResponse:
        raise HTTPError(request.full_url, status, "failure", hdrs=Message(), fp=None)

    monkeypatch.setattr(dispatch_module, "urlopen", fail_request)
    client = GitHubRestClient(
        api_url="https://api.github.com",
        repository="sgajbi/lotus-idea",
        token="test-token",
    )

    assert client.dispatch_ref_sha(f"main-releasability-{REVISION_TWO}") is None
    status = 500
    with pytest.raises(GitHubApiError, match="HTTP 500"):
        client.dispatch_ref_sha(f"main-releasability-{REVISION_TWO}")
