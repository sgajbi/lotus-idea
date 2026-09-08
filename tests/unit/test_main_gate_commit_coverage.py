from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

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
    "abcc119ea48d286cf7336fb687a51e0b40d38404 --limit 60 --fail-on-gap"
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
    than the wrapper.
    """

    workflow = (WORKFLOW_ROOT / "main-gate-coverage-audit.yml").read_text(encoding="utf-8")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "schedule:" in workflow
    assert "workflow_dispatch" in workflow

    # Same script, same arguments, in both places: the Makefile stays the
    # canonical definition without CI having to route through it.
    assert AUDIT_INVOCATION in makefile
    assert AUDIT_INVOCATION in workflow

    # Fail-closed, and not through a pipe - a pipe would report its own exit
    # status and leave the step green while the audit failed.
    assert "--fail-on-gap" in workflow
    assert "| tee" not in workflow
    assert "| tail" not in workflow


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


def test_audit_fails_for_missing_cancelled_and_unverifiable_evidence(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    commits = {
        "a" * 40: ["success"],
        "b" * 40: ["cancelled"],
        "c" * 40: None,
        "d" * 40: [],
    }
    monkeypatch.setattr(audit, "_arguments", lambda: argparse.Namespace(limit=60, fail_on_gap=True))
    monkeypatch.setattr(
        audit,
        "_git",
        lambda *args: [f"{sha} {sha[:9]} subject line" for sha in commits],
    )
    monkeypatch.setattr(audit, "_run_conclusions", lambda sha: commits[sha])
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/gh")

    assert audit.main() == 1
    output = capsys.readouterr().out
    assert "UNGATED  ddddddddd" in output
    assert "UNKNOWN  ccccccccc" in output
    assert "UNKNOWN  bbbbbbbbb" in output
    assert "1 passing, 0 with a failing verdict" in output


def test_failing_verdict_counts_as_evaluated_without_becoming_a_pass(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    commits = {"a" * 40: ["success"], "b" * 40: ["failure", "cancelled"]}
    monkeypatch.setattr(audit, "_arguments", lambda: argparse.Namespace(limit=60, fail_on_gap=True))
    monkeypatch.setattr(
        audit,
        "_git",
        lambda *args: [f"{sha} {sha[:9]} subject line" for sha in commits],
    )
    monkeypatch.setattr(audit, "_run_conclusions", lambda sha: commits[sha])
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/gh")

    assert audit.main() == 0
    output = capsys.readouterr().out
    assert "1 passing, 1 with a failing verdict" in output
    assert "FAILING  bbbbbbbbb" in output


def test_empty_main_history_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audit, "_arguments", lambda: argparse.Namespace(limit=60, fail_on_gap=True))
    monkeypatch.setattr(audit, "_git", lambda *args: [])
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/gh")

    assert audit.main() == 1


def test_empty_post_rollout_history_is_fully_covered(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        audit,
        "_arguments",
        lambda: argparse.Namespace(
            limit=60,
            fail_on_gap=True,
            baseline_sha="a" * 40,
        ),
    )
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
    monkeypatch.setattr(
        audit,
        "_arguments",
        lambda: argparse.Namespace(
            limit=60,
            fail_on_gap=True,
            baseline_sha="a" * 40,
        ),
    )
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1),
    )
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/gh")

    assert audit.main() == 1


def test_missing_gh_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audit, "_arguments", lambda: argparse.Namespace(limit=60, fail_on_gap=True))
    monkeypatch.setattr(shutil, "which", lambda name: None)

    assert audit.main() == 1


def test_malformed_run_listing_is_unverifiable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="not-json"),
    )

    assert audit._run_conclusions("a" * 40) is None


def test_non_list_run_listing_is_unverifiable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=json.dumps({"status": "ok"})),
    )

    assert audit._run_conclusions("a" * 40) is None
