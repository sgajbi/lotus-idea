from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from scripts.reclaim_main_releasability_tag import CommandResult, reclaim_dispatch_tag

SHA = "a" * 40
TAG = f"main-releasability-{SHA}"


class StubRunner:
    def __init__(self, results: list[CommandResult] | None = None) -> None:
        self.results = list(results or [])
        self.calls: list[list[str]] = []

    def run(self, arguments: Sequence[str]) -> CommandResult:
        self.calls.append(list(arguments))
        return self.results.pop(0)


def _environment(**overrides: str) -> dict[str, str]:
    environment = {
        "DISPATCH_REF": TAG,
        "EXPECTED_SHA": SHA,
        "GITHUB_REF_TYPE": "tag",
        "GITHUB_REPOSITORY": "sgajbi/lotus-idea",
    }
    environment.update(overrides)
    return environment


@pytest.mark.parametrize(
    "overrides",
    [
        {"GITHUB_REF_TYPE": "branch"},
        {"DISPATCH_REF": "release-v1"},
        {"DISPATCH_REF": f"main-releasability-{'b' * 40}"},
        {"EXPECTED_SHA": ""},
        {"GITHUB_REPOSITORY": ""},
    ],
)
def test_invalid_identity_never_calls_github(overrides: dict[str, str]) -> None:
    runner = StubRunner()

    assert reclaim_dispatch_tag(_environment(**overrides), runner) is False
    assert runner.calls == []


def test_lookup_failure_never_attempts_deletion() -> None:
    runner = StubRunner([CommandResult(1)])

    assert reclaim_dispatch_tag(_environment(), runner) is False
    assert len(runner.calls) == 1
    assert "--method" not in runner.calls[0]


def test_mismatched_target_never_attempts_deletion() -> None:
    runner = StubRunner([CommandResult(0, "b" * 40)])

    assert reclaim_dispatch_tag(_environment(), runner) is False
    assert len(runner.calls) == 1


def test_exact_identity_deletes_the_tag_once() -> None:
    runner = StubRunner([CommandResult(0, f"{SHA}\n"), CommandResult(0)])

    assert reclaim_dispatch_tag(_environment(), runner) is True
    assert runner.calls[-1] == [
        "gh",
        "api",
        "--method",
        "DELETE",
        f"repos/sgajbi/lotus-idea/git/refs/tags/{TAG}",
    ]


def test_delete_failure_is_non_blocking() -> None:
    runner = StubRunner([CommandResult(0, SHA), CommandResult(1)])

    assert reclaim_dispatch_tag(_environment(), runner) is False
    assert len(runner.calls) == 2


def test_reclaim_job_runs_after_gate_without_changing_its_verdict() -> None:
    workflow_path = Path(__file__).resolve().parents[2] / (
        ".github/workflows/main-releasability-tag-reclamation.yml"
    )
    workflow = workflow_path.read_text(encoding="utf-8")

    assert 'workflows: ["Main Releasability Gate"]' in workflow
    assert "types: [completed]" in workflow
    assert "github.event.workflow_run.head_branch" in workflow
    assert "github.event.workflow_run.head_sha" in workflow
    assert "contents: write" in workflow
    assert "run: python scripts/reclaim_main_releasability_tag.py" in workflow


def test_release_verdict_workflow_remains_read_only_and_fail_closed() -> None:
    workflow_path = Path(__file__).resolve().parents[2] / (
        ".github/workflows/main-releasability.yml"
    )
    workflow = workflow_path.read_text(encoding="utf-8")

    assert "contents: write" not in workflow
    assert "continue-on-error:" not in workflow
