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


def test_evidence_workflow_cannot_cancel_a_live_revision_verdict() -> None:
    workflow = (WORKFLOW_ROOT / "main-releasability.yml").read_text(encoding="utf-8")

    assert "cancel-in-progress: false" in workflow


def test_scheduled_workflow_uses_the_repo_native_fail_closed_audit() -> None:
    workflow = (WORKFLOW_ROOT / "main-gate-coverage-audit.yml").read_text(encoding="utf-8")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "schedule:" in workflow
    assert "workflow_dispatch" in workflow
    assert "run: make main-gate-coverage-audit" in workflow
    assert (
        "scripts/audit_main_gate_coverage.py --baseline-sha "
        "abcc119ea48d286cf7336fb687a51e0b40d38404 --limit 60 --fail-on-gap"
    ) in makefile


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
