"""Regression tests for complete live issue-posture validation."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date
from pathlib import Path
from types import ModuleType
from typing import Any


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


def _issue(number: int, *, state: str, labels: list[str], title: str) -> dict[str, Any]:
    return {
        "number": number,
        "state": state,
        "title": title,
        "url": f"https://github.com/{REPOSITORY}/issues/{number}",
        "updatedAt": "2026-08-30T00:00:00Z",
        "labels": [{"name": label} for label in labels],
    }


def _write_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    open_issue = _issue(
        1139,
        state="OPEN",
        title="Live posture audit",
        labels=["rfc/RFC-0002", "rfc/RFC-0002/slice-18", "status/in-progress"],
    )
    closed_issue = _issue(
        1131,
        state="CLOSED",
        title="Closed workflow hardening",
        labels=["rfc/RFC-0002", "rfc/RFC-0002/slice-17", "status/merged-main"],
    )
    title_only = _issue(
        704,
        state="OPEN",
        title="RFC-0002 title-only reference",
        labels=[],
    )
    fixture = tmp_path / "issues.json"
    fixture.write_text(
        json.dumps(
            {
                REPOSITORY: {
                    "openIssues": [open_issue, title_only],
                    "allIssues": [open_issue, closed_issue, title_only],
                    "rfc0002Issues": [open_issue, closed_issue],
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
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(
        json.dumps(
            {
                "schemaVersion": "lotus-idea:rfc0002-issue-posture-snapshot:v1",
                "asOfDate": "2026-08-30",
                "crossRepo": {
                    "repositoriesChecked": 1,
                    "totalRfc0002Issues": 2,
                    "openRfc0002Issues": 1,
                    "closedRfc0002Issues": 1,
                    "openBlockedIssues": 0,
                    "appActionableBlockedIssues": 0,
                    "openStatusCounts": {"status/in-progress": 1},
                    "titleOnlyReferencesExcludedFromGovernedCounts": ["sgajbi/lotus-idea#704"],
                },
            }
        ),
        encoding="utf-8",
    )
    return fixture, blocker_classification, snapshot


def test_live_posture_gate_accepts_current_exact_snapshot(tmp_path: Path) -> None:
    module = _load_gate()
    fixture, blocker_classification, snapshot = _write_inputs(tmp_path)

    errors = module.live_posture_errors(
        snapshot_path=snapshot,
        repositories=(REPOSITORY,),
        fixture_path=fixture,
        blocker_classification_path=blocker_classification,
        today=date(2026, 8, 30),
    )

    assert errors == []


def test_live_posture_gate_rejects_count_drift(tmp_path: Path) -> None:
    module = _load_gate()
    fixture, blocker_classification, snapshot = _write_inputs(tmp_path)
    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    payload["crossRepo"]["openRfc0002Issues"] = 0
    snapshot.write_text(json.dumps(payload), encoding="utf-8")

    errors = module.live_posture_errors(
        snapshot_path=snapshot,
        repositories=(REPOSITORY,),
        fixture_path=fixture,
        blocker_classification_path=blocker_classification,
        today=date(2026, 8, 30),
    )

    assert errors == [
        "RFC-0002 posture snapshot crossRepo.openRfc0002Issues=0 does not match "
        "live GitHub posture 1"
    ]


def test_live_posture_gate_rejects_snapshot_older_than_tolerance(tmp_path: Path) -> None:
    module = _load_gate()
    fixture, blocker_classification, snapshot = _write_inputs(tmp_path)
    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    payload["asOfDate"] = "2026-08-22"
    snapshot.write_text(json.dumps(payload), encoding="utf-8")

    errors = module.live_posture_errors(
        snapshot_path=snapshot,
        repositories=(REPOSITORY,),
        fixture_path=fixture,
        blocker_classification_path=blocker_classification,
        today=date(2026, 8, 30),
        max_snapshot_age_days=7,
    )

    assert errors == ["RFC-0002 posture snapshot is 8 days old; maximum allowed age is 7 days"]


def test_live_posture_gate_rejects_future_snapshot_date(tmp_path: Path) -> None:
    module = _load_gate()
    fixture, blocker_classification, snapshot = _write_inputs(tmp_path)
    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    payload["asOfDate"] = "2026-08-31"
    snapshot.write_text(json.dumps(payload), encoding="utf-8")

    errors = module.live_posture_errors(
        snapshot_path=snapshot,
        repositories=(REPOSITORY,),
        fixture_path=fixture,
        blocker_classification_path=blocker_classification,
        today=date(2026, 8, 30),
    )

    assert errors == ["RFC-0002 posture snapshot asOfDate 2026-08-31 is in the future"]


def test_live_posture_workflow_runs_on_schedule_dispatch_and_main_snapshot_change() -> None:
    workflow = (ROOT / ".github/workflows/issue-posture-audit.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "schedule:" in workflow
    assert 'cron: "23 3 * * *"' in workflow
    assert "push:" in workflow
    assert '"contracts/implementation-proof/rfc0002-issue-posture-snapshot.v1.json"' in workflow
    assert '"scripts/github_issue_inventory.py"' in workflow
    assert "python scripts/issue_posture_live_gate.py" in workflow
