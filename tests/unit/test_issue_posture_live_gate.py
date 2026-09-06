"""Regression tests for complete live issue-posture validation."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, cast


ROOT = Path(__file__).resolve().parents[2]
REPOSITORY = "sgajbi/lotus-idea"


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "issue_posture_live_gate.py"
    scripts_path = str(script_path.parent)
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)
    spec = importlib.util.spec_from_file_location("issue_posture_live_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _issue(number: int, *, state: str, status_labels: list[str]) -> dict[str, Any]:
    return {
        "number": number,
        "state": state,
        "title": f"RFC-0002 issue {number}",
        "url": f"https://github.com/{REPOSITORY}/issues/{number}",
        "updatedAt": "2026-09-06T00:00:00Z",
        "labels": [
            {"name": "rfc/RFC-0002"},
            {"name": "rfc/RFC-0002/slice-18"},
            *({"name": label} for label in status_labels),
        ],
    }


def _write_fixture(
    tmp_path: Path,
    *,
    open_issues: list[dict[str, Any]],
    closed_issues: list[dict[str, Any]] | None = None,
) -> tuple[Path, Path]:
    closed = closed_issues or []
    fixture = tmp_path / "issues.json"
    fixture.write_text(
        json.dumps(
            {
                REPOSITORY: {
                    "openIssues": open_issues,
                    "allIssues": [*open_issues, *closed],
                    "rfc0002Issues": [*open_issues, *closed],
                }
            }
        ),
        encoding="utf-8",
    )
    blocker_classification = tmp_path / "blockers.json"
    blocker_classification.write_text(
        json.dumps(
            {
                "schemaVersion": ("lotus-idea:rfc0002-cross-repo-blocker-classification:v1"),
                "rfcId": "RFC-0002",
                "classifications": [],
            }
        ),
        encoding="utf-8",
    )
    return fixture, blocker_classification


def _live_errors(
    module: ModuleType,
    *,
    fixture: Path,
    blocker_classification: Path,
) -> list[str]:
    return cast(
        list[str],
        module.live_posture_errors(
            repositories=(REPOSITORY,),
            fixture_path=fixture,
            blocker_classification_path=blocker_classification,
        ),
    )


def test_live_posture_gate_accepts_current_lifecycle_state(tmp_path: Path) -> None:
    module = _load_gate()
    fixture, blockers = _write_fixture(
        tmp_path,
        open_issues=[_issue(1248, state="OPEN", status_labels=["status/in-progress"])],
        closed_issues=[_issue(1247, state="CLOSED", status_labels=["status/merged-main"])],
    )

    assert _live_errors(module, fixture=fixture, blocker_classification=blockers) == []


def test_live_posture_gate_accepts_new_and_reopened_issues(tmp_path: Path) -> None:
    module = _load_gate()
    fixture, blockers = _write_fixture(
        tmp_path,
        open_issues=[
            _issue(1248, state="OPEN", status_labels=["status/pr-open"]),
            _issue(1300, state="OPEN", status_labels=["status/ready"]),
        ],
    )

    assert _live_errors(module, fixture=fixture, blocker_classification=blockers) == []


def test_live_posture_gate_accepts_repository_specific_merged_label(tmp_path: Path) -> None:
    module = _load_gate()
    fixture, blockers = _write_fixture(
        tmp_path,
        open_issues=[_issue(615, state="OPEN", status_labels=["status/merged-to-main"])],
    )

    assert _live_errors(module, fixture=fixture, blocker_classification=blockers) == []


def test_live_posture_gate_rejects_missing_lifecycle_label(tmp_path: Path) -> None:
    module = _load_gate()
    fixture, blockers = _write_fixture(
        tmp_path,
        open_issues=[_issue(1248, state="OPEN", status_labels=[])],
    )

    assert _live_errors(module, fixture=fixture, blocker_classification=blockers) == [
        f"{REPOSITORY}#1248: open RFC-0002 issue has ungoverned lifecycle label status/unlabeled"
    ]


def test_live_posture_gate_rejects_conflicting_lifecycle_labels(tmp_path: Path) -> None:
    module = _load_gate()
    fixture, blockers = _write_fixture(
        tmp_path,
        open_issues=[
            _issue(
                1248,
                state="OPEN",
                status_labels=["status/in-progress", "status/pr-open"],
            )
        ],
    )

    assert _live_errors(module, fixture=fixture, blocker_classification=blockers) == [
        f"{REPOSITORY}#1248: open RFC-0002 issue requires exactly one status/* "
        "lifecycle label; found status/in-progress,status/pr-open"
    ]


def test_live_posture_gate_rejects_unknown_lifecycle_label(tmp_path: Path) -> None:
    module = _load_gate()
    fixture, blockers = _write_fixture(
        tmp_path,
        open_issues=[_issue(1248, state="OPEN", status_labels=["status/imagined"])],
    )

    assert _live_errors(module, fixture=fixture, blocker_classification=blockers) == [
        f"{REPOSITORY}#1248: open RFC-0002 issue has ungoverned lifecycle label status/imagined"
    ]


def test_live_posture_gate_rejects_app_actionable_blocked_work() -> None:
    module = _load_gate()
    live = {
        "counts": {
            "repositories": 1,
            "totalRfc0002Issues": 0,
            "openRfc0002Issues": 0,
            "closedRfc0002Issues": 0,
        },
        "blockedActionability": {"appActionableBlockedIssueCount": 1},
        "repositories": [],
    }

    assert module._live_posture_errors(live=live, expected_repository_count=1) == [
        "RFC-0002 live posture contains 1 app-actionable issue(s) incorrectly marked blocked"
    ]


def test_live_posture_gate_rejects_inconsistent_counts() -> None:
    module = _load_gate()
    live = {
        "counts": {
            "repositories": 2,
            "totalRfc0002Issues": 4,
            "openRfc0002Issues": 2,
            "closedRfc0002Issues": 1,
        },
        "blockedActionability": {"appActionableBlockedIssueCount": 0},
        "repositories": [],
    }

    assert module._live_posture_errors(live=live, expected_repository_count=1) == [
        "RFC-0002 live posture repository count 2 does not match requested repository count 1",
        "RFC-0002 live posture open/closed counts do not sum to total issues: "
        "open=2, closed=1, total=4",
        "RFC-0002 live posture projected open issues do not match aggregate count: "
        "projected=0, aggregate=2",
    ]


def test_live_posture_workflow_runs_on_schedule_dispatch_and_live_control_change() -> None:
    workflow = (ROOT / ".github/workflows/issue-posture-audit.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "schedule:" in workflow
    assert 'cron: "23 3 * * *"' in workflow
    assert "push:" in workflow
    assert '"scripts/issue_posture_live_gate.py"' in workflow
    assert '"scripts/github_issue_inventory.py"' in workflow
    assert '"contracts/implementation-proof/rfc0002-issue-posture-snapshot.v1.json"' not in workflow
    assert "python scripts/issue_posture_live_gate.py" in workflow
