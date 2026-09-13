from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from scripts import audit_main_gate_coverage as audit

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_ROOT = ROOT / ".github" / "workflows"


def test_dispatch_gates_every_revision_added_by_a_rebase_merged_pr() -> None:
    dispatcher = (WORKFLOW_ROOT / "merged-pr-main-releasability.yml").read_text(encoding="utf-8")
    implementation = (ROOT / "scripts" / "main_releasability_dispatch.py").read_text(
        encoding="utf-8"
    )

    assert "fetch-depth: 0" in dispatcher
    assert "run: python scripts/main_releasability_dispatch.py" in dispatcher
    assert "run: |" not in dispatcher
    assert '["git", "rev-list", "-n", str(commit_count), merge_commit_sha]' in implementation
    assert 'dispatch_ref = f"main-releasability-{revision}"' in implementation
    assert '"expected_sha": revision' in implementation
    assert "github.merge_methods() != (False, False, True)" in implementation
    assert '["git", "rev-parse", "--verify", f"{ref}^{{commit}}"]' in implementation
    assert '["git", "merge-base", "--is-ancestor", revision, main_revision]' in implementation
    assert 'git_commit_sha("FETCH_HEAD")' in implementation


def test_evidence_workflow_cannot_cancel_a_live_revision_verdict() -> None:
    workflow = (WORKFLOW_ROOT / "main-releasability.yml").read_text(encoding="utf-8")

    assert "cancel-in-progress: false" in workflow


AUDIT_INVOCATION = (
    "scripts/audit_main_gate_coverage.py --baseline-sha "
    "abcc119ea48d286cf7336fb687a51e0b40d38404 --end-ref origin/main --fail-on-gap "
    "--ledger-output output/ci/main-gate-coverage-ledger.json"
)


def test_scheduled_workflow_uses_the_repo_native_fail_closed_audit() -> None:
    """The workflow runs the same audit the Makefile defines, on a real interpreter.

    This previously asserted `run: make main-gate-coverage-audit`, which
    mandated the one invocation that could not work: that target runs
    `$(VENV_PYTHON)`, resolving to `.venv/bin/python`, and the job creates no
    virtualenv. Every scheduled run died with `No such file or directory` and
    exit 127 for at least a week, so the test was enforcing a dead gate while
    reading as though it protected a live one.

    The intent behind it was sound - CI and the repo-native command must not
    drift - so that is what is asserted now, by comparing the arguments rather
    than the wrapper. The invocation names the fixed range explicitly and carries
    no rolling `--limit`, so historical gaps and verdicts cannot age out of view.
    """

    workflow = (WORKFLOW_ROOT / "main-gate-coverage-audit.yml").read_text(encoding="utf-8")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "schedule:" in workflow
    assert "workflow_dispatch" in workflow

    # Same script, same arguments, in both places: the Makefile stays the
    # canonical definition without CI having to route through it.
    assert AUDIT_INVOCATION in makefile
    assert AUDIT_INVOCATION in workflow
    assert "--limit" not in workflow
    assert "--limit" not in makefile.split("main-gate-coverage-audit:")[1].split("\n\n")[0]

    # Fail-closed, and not through a pipe - a pipe would report its own exit
    # status and leave the step green while the audit failed.
    assert "--fail-on-gap" in workflow
    assert "| tee" not in workflow
    assert "| tail" not in workflow

    # The ledger is durable evidence even when the audit fails.
    assert "output/ci/main-gate-coverage-ledger.json" in workflow
    assert "if: always()" in workflow


def test_the_scheduled_audit_does_not_depend_on_a_virtualenv_the_job_never_creates() -> None:
    """The specific defect that made this control dead for a week.

    The job checks the repository out and runs; nothing in it creates a
    virtualenv. Any invocation that reaches for one - `make`'s
    `$(VENV_PYTHON)`, or `.venv` directly - exits 127 before the audit starts,
    and a gate that cannot run is indistinguishable in the checks list from a
    gate that ran and found something. Both are red.
    """

    workflow = (WORKFLOW_ROOT / "main-gate-coverage-audit.yml").read_text(encoding="utf-8")

    # Comment lines are excluded deliberately: the comment recording *why* the
    # venv is absent names it, and asserting on raw text would make the
    # explanation trip the check that the explanation exists to justify. The
    # property is about what the job executes, not what it says.
    executed = "\n".join(
        line for line in workflow.splitlines() if not line.lstrip().startswith("#")
    )

    assert ".venv" not in executed
    assert "VENV_PYTHON" not in executed
    assert "run: make " not in executed

    # It must therefore provide its own interpreter.
    assert "actions/setup-python" in executed


def _run(created_at: str, state: str, run_id: int = 0) -> audit.RunEvidence:
    return audit.RunEvidence(created_at=created_at, state=state, run_id=run_id)


def _history(*runs: audit.RunEvidence, complete: bool = True) -> audit.RunHistory:
    return audit.RunHistory(runs=tuple(runs), complete=complete)


@pytest.mark.parametrize(
    ("history", "expected"),
    (
        (_history(_run("T1", "success", 1), _run("T2", "failure", 2)), ("verdict", "failure")),
        (_history(_run("T2", "failure", 2), _run("T1", "success", 1)), ("verdict", "failure")),
        (_history(_run("T1", "failure", 1), _run("T2", "success", 2)), ("verdict", "success")),
        (_history(_run("T1", "success", 1), _run("T2", "cancelled", 2)), ("verdict", "success")),
        (_history(_run("T1", "failure", 1), _run("T2", "in_progress", 2)), ("verdict", "failure")),
        (_history(_run("T1", "cancelled", 1)), ("unverifiable", None)),
        (_history(_run("T1", "timed_out", 1), _run("T2", "skipped", 2)), ("unverifiable", None)),
        (_history(), ("ungated", None)),
        (_history(_run("T1", "cancelled", 1), complete=False), ("unknown", None)),
        (None, ("unknown", None)),
    ),
)
def test_latest_terminal_run_decides_the_outcome_and_non_verdicts_never_do(
    history: audit.RunHistory | None,
    expected: tuple[str, str | None],
) -> None:
    coverage, outcome, _ = audit.classify_revision(history)

    assert (coverage, outcome) == expected


@pytest.mark.parametrize(
    "runs",
    (
        (_run("T1", "failure", 2), _run("T1", "success", 1)),
        (_run("T1", "success", 1), _run("T1", "failure", 2)),
    ),
)
def test_equal_timestamps_are_ordered_by_run_id_in_either_input_order(
    runs: tuple[audit.RunEvidence, ...],
) -> None:
    assert audit.classify_revision(_history(*runs)) == ("verdict", "failure", None)


@pytest.mark.parametrize(
    "runs",
    (
        (_run("T1", "success", 2), _run("T1", "failure", 1)),
        (_run("T1", "failure", 1), _run("T1", "success", 2)),
    ),
)
def test_equal_timestamps_with_a_newer_success_id_pass_in_either_input_order(
    runs: tuple[audit.RunEvidence, ...],
) -> None:
    assert audit.classify_revision(_history(*runs)) == ("verdict", "success", None)


@pytest.mark.parametrize(
    "runs",
    (
        (_run("T1", "failure"), _run("T1", "success")),
        (_run("T1", "success"), _run("T1", "failure")),
    ),
)
def test_unorderable_disagreeing_verdicts_never_manufacture_a_pass(
    runs: tuple[audit.RunEvidence, ...],
) -> None:
    assert audit.classify_revision(_history(*runs)) == (
        "verdict",
        "failure",
        audit.NOTE_AMBIGUOUS_ORDER,
    )


def test_unorderable_agreeing_verdicts_keep_their_shared_conclusion() -> None:
    assert audit.classify_revision(_history(_run("T1", "success"), _run("T1", "success"))) == (
        "verdict",
        "success",
        None,
    )


def test_exhausted_and_unreadable_histories_are_unknown_not_ungated() -> None:
    assert audit.classify_revision(_history(complete=False)) == (
        "unknown",
        None,
        audit.NOTE_HISTORY_EXHAUSTED,
    )
    assert audit.classify_revision(None) == ("unknown", None, audit.NOTE_HISTORY_UNREADABLE)


def _namespace(**overrides: Any) -> argparse.Namespace:
    values: dict[str, Any] = {
        "baseline_sha": None,
        "end_ref": "origin/main",
        "fail_on_gap": True,
        "ledger_output": None,
        "listing_limit": 5000,
        "revision_limit": 200,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def _install_history(
    monkeypatch: pytest.MonkeyPatch,
    commits: dict[str, audit.RunHistory | None],
    *,
    listing: tuple[dict[str, list[audit.RunEvidence]], bool] | None,
    fallback_calls: list[str] | None = None,
) -> None:
    monkeypatch.setattr(
        audit,
        "_git",
        lambda *args: [f"{sha} {sha[:9]} subject line" for sha in commits],
    )
    monkeypatch.setattr(audit, "_list_workflow_runs", lambda limit: listing)

    def fallback(sha: str, limit: int) -> audit.RunHistory | None:
        if fallback_calls is not None:
            fallback_calls.append(sha)
        return commits[sha]

    monkeypatch.setattr(audit, "_runs_for_revision", fallback)
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/gh")


def test_audit_fails_for_missing_cancelled_and_unverifiable_evidence(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    commits: dict[str, audit.RunHistory | None] = {
        "a" * 40: _history(_run("T1", "success", 1)),
        "b" * 40: _history(_run("T1", "cancelled", 1)),
        "c" * 40: None,
        "d" * 40: _history(),
    }
    monkeypatch.setattr(audit, "_arguments", _namespace)
    _install_history(monkeypatch, commits, listing=None)

    assert audit.main() == 1
    output = capsys.readouterr().out
    assert "UNGATED" in output and "ddddddddd" in output
    assert "UNKNOWN" in output and "ccccccccc" in output
    assert "UNVERIFIABLE cancelled  bbbbbbbbb" in output
    assert "coverage: 1 with a terminal main-releasability.yml verdict, 1 unverifiable, " in output
    assert "1 ungated, 1 unknown" in output
    assert "outcome: 1 passing, 0 with a failing verdict" in output


def test_earlier_success_does_not_outrank_a_later_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    commits: dict[str, audit.RunHistory | None] = {
        "a" * 40: _history(_run("T1", "success", 1), _run("T2", "failure", 2)),
        "b" * 40: _history(_run("T1", "failure", 1), _run("T2", "cancelled", 2)),
    }
    listing = ({sha: list(history.runs) for sha, history in commits.items() if history}, False)
    monkeypatch.setattr(audit, "_arguments", _namespace)
    _install_history(monkeypatch, commits, listing=listing)

    assert audit.main() == 0
    output = capsys.readouterr().out
    assert "VERDICT      failure    aaaaaaaaa" in output
    assert "VERDICT      failure    bbbbbbbbb" in output
    assert "outcome: 0 passing, 2 with a failing verdict" in output


def test_bulk_listing_is_used_and_absent_revisions_are_rechecked_individually(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commits: dict[str, audit.RunHistory | None] = {
        "a" * 40: _history(_run("T1", "success", 1)),
        "b" * 40: _history(_run("T1", "failure", 1)),
        "c" * 40: _history(),
    }
    fallback_calls: list[str] = []
    monkeypatch.setattr(audit, "_arguments", _namespace)
    _install_history(
        monkeypatch,
        commits,
        listing=({"a" * 40: [_run("T1", "success", 1)]}, False),
        fallback_calls=fallback_calls,
    )

    assert audit.main() == 1
    assert fallback_calls == ["b" * 40, "c" * 40]


def test_truncated_listing_with_only_a_recent_cancellation_recovers_the_older_verdict(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A revision can appear in a truncated listing only through its newest, non-terminal run.

    The older verdict lies beyond the listing cutoff, so the per-revision history must be
    consulted before any gap is declared; the listed verdict-bearing revision needs no
    re-check because its newest runs are already in hand.
    """

    commits: dict[str, audit.RunHistory | None] = {
        "a" * 40: _history(_run("T9", "cancelled", 9), _run("T1", "success", 1)),
        "b" * 40: _history(_run("T5", "failure", 5)),
    }
    fallback_calls: list[str] = []
    monkeypatch.setattr(audit, "_arguments", _namespace)
    _install_history(
        monkeypatch,
        commits,
        listing=(
            {"a" * 40: [_run("T9", "cancelled", 9)], "b" * 40: [_run("T5", "failure", 5)]},
            True,
        ),
        fallback_calls=fallback_calls,
    )

    assert audit.main() == 0
    output = capsys.readouterr().out
    assert "bulk run listing reached its limit" in output
    assert "VERDICT      success    aaaaaaaaa" in output
    assert "VERDICT      failure    bbbbbbbbb" in output
    assert fallback_calls == ["a" * 40]


def test_exhausted_or_unreadable_revision_history_is_a_gap_not_a_verdict(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    commits: dict[str, audit.RunHistory | None] = {
        "a" * 40: _history(_run("T9", "cancelled", 9), _run("T8", "cancelled", 8), complete=False),
        "b" * 40: None,
    }
    monkeypatch.setattr(audit, "_arguments", _namespace)
    _install_history(
        monkeypatch,
        commits,
        listing=({"a" * 40: [_run("T9", "cancelled", 9)]}, True),
    )

    assert audit.main() == 1
    output = capsys.readouterr().out
    assert f"aaaaaaaaa  subject line  [{audit.NOTE_HISTORY_EXHAUSTED}]" in output
    assert f"bbbbbbbbb  subject line  [{audit.NOTE_HISTORY_UNREADABLE}]" in output
    assert "0 unverifiable, 0 ungated, 2 unknown" in output


def test_ledger_records_every_revision_with_coverage_and_outcome(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    commits: dict[str, audit.RunHistory | None] = {
        "a" * 40: _history(_run("T1", "success", 1), _run("T2", "cancelled", 2)),
        "b" * 40: _history(_run("T1", "cancelled", 1)),
    }
    ledger_path = tmp_path / "ci" / "ledger.json"
    monkeypatch.setattr(
        audit,
        "_arguments",
        lambda: _namespace(ledger_output=str(ledger_path), fail_on_gap=False),
    )
    listing = ({sha: list(history.runs) for sha, history in commits.items() if history}, False)
    _install_history(monkeypatch, commits, listing=listing)

    assert audit.main() == 0
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert ledger["workflow"] == "main-releasability.yml"
    assert ledger["revision_range"] == "origin/main"
    assert ledger["summary"] == {
        "audited": 2,
        "verdict": 1,
        "unverifiable": 1,
        "ungated": 0,
        "unknown": 0,
        "passing": 1,
        "failing": 0,
    }
    assert [(row["short"], row["coverage"], row["outcome"]) for row in ledger["revisions"]] == [
        ("aaaaaaaaa", "verdict", "success"),
        ("bbbbbbbbb", "unverifiable", None),
    ]
    assert ledger["revisions"][0]["run_states"] == ["success", "cancelled"]
    assert ledger["revisions"][0]["note"] is None


def test_empty_main_history_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audit, "_arguments", _namespace)
    monkeypatch.setattr(audit, "_git", lambda *args: [])
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/gh")

    assert audit.main() == 1


def test_empty_post_rollout_history_is_fully_covered(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(audit, "_arguments", lambda: _namespace(baseline_sha="a" * 40))
    monkeypatch.setattr(audit, "_git", lambda *args: [])
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0),
    )
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/gh")

    assert audit.main() == 0
    assert "explicitly classified as pre-gate" in capsys.readouterr().out


def test_non_ancestor_rollout_baseline_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audit, "_arguments", lambda: _namespace(baseline_sha="a" * 40))
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1),
    )
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/gh")

    assert audit.main() == 1


def test_missing_gh_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audit, "_arguments", _namespace)
    monkeypatch.setattr(shutil, "which", lambda name: None)

    assert audit.main() == 1


def test_malformed_run_listing_is_unverifiable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="not-json"),
    )

    assert audit._runs_for_revision("a" * 40, 10) is None
    assert audit._list_workflow_runs(10) is None


def test_non_list_run_listing_is_unverifiable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=json.dumps({"status": "ok"})),
    )

    assert audit._runs_for_revision("a" * 40, 10) is None
    assert audit._list_workflow_runs(10) is None


def test_bulk_listing_groups_runs_by_exact_head_sha_and_reports_truncation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = [
        {
            "databaseId": 11,
            "headSha": "a" * 40,
            "conclusion": "success",
            "status": "completed",
            "createdAt": "T1",
        },
        {
            "databaseId": 12,
            "headSha": "a" * 40,
            "conclusion": None,
            "status": "in_progress",
            "createdAt": "T2",
        },
        {
            "databaseId": 13,
            "headSha": "b" * 40,
            "conclusion": "failure",
            "status": "completed",
            "createdAt": "T1",
        },
        {"conclusion": "success", "status": "completed", "createdAt": "T0"},
    ]
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=json.dumps(payload)),
    )

    assert audit._list_workflow_runs(10) == (
        {
            "a" * 40: [_run("T1", "success", 11), _run("T2", "in_progress", 12)],
            "b" * 40: [_run("T1", "failure", 13)],
        },
        False,
    )
    assert audit._list_workflow_runs(4) == (
        {
            "a" * 40: [_run("T1", "success", 11), _run("T2", "in_progress", 12)],
            "b" * 40: [_run("T1", "failure", 13)],
        },
        True,
    )


def test_revision_history_reports_exhaustion_at_its_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = [
        {"databaseId": 22, "conclusion": None, "status": "cancelled", "createdAt": "T2"},
        {"databaseId": 21, "conclusion": "cancelled", "status": "completed", "createdAt": "T1"},
    ]
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=json.dumps(payload)),
    )

    assert audit._runs_for_revision("a" * 40, 2) == audit.RunHistory(
        runs=(_run("T2", "cancelled", 22), _run("T1", "cancelled", 21)),
        complete=False,
    )
    assert audit._runs_for_revision("a" * 40, 3) == audit.RunHistory(
        runs=(_run("T2", "cancelled", 22), _run("T1", "cancelled", 21)),
        complete=True,
    )
