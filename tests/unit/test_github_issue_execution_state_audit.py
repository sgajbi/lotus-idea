from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, cast


ROOT = Path(__file__).resolve().parents[2]


def _load_audit() -> ModuleType:
    script_path = ROOT / "scripts" / "github_issue_execution_state_audit.py"
    scripts_path = str(script_path.parent)
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)
    spec = importlib.util.spec_from_file_location(
        "github_issue_execution_state_audit",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_ledger() -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads(
            (
                ROOT
                / "contracts"
                / "implementation-proof"
                / "rfc0002-github-issue-execution-ledger.v1.json"
            ).read_text(encoding="utf-8")
        ),
    )


def _write_ledger(tmp_path: Path, payload: dict[str, Any]) -> Path:
    path = tmp_path / "ledger.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _github_issue_payload(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    status_label_by_execution_status = {
        "open_blocked": "status/blocked",
        "open_in_progress": "status/in-progress",
        "open_merged_main_qa_pending": "status/merged-main",
        "closed_complete": "status/merged-main",
    }
    issues: list[dict[str, Any]] = []
    for entry in ledger["issues"]:
        assert isinstance(entry, dict)
        labels = [
            {"name": "rfc/RFC-0002"},
            *({"name": slice_id} for slice_id in entry["rfcSlices"]),
        ]
        status_label = status_label_by_execution_status.get(entry["executionStatus"])
        if status_label is not None:
            labels.append({"name": status_label})
        issues.append(
            {
                "number": entry["issueNumber"],
                "state": entry["githubState"].upper(),
                "title": f"Issue {entry['issueNumber']}",
                "url": entry["url"],
                "labels": labels,
            }
        )
    return issues


def test_github_issue_execution_state_audit_passes_matching_issue_state() -> None:
    module = _load_audit()
    ledger = _load_ledger()
    github_issues = module._parse_github_issue_states(_github_issue_payload(ledger))

    assert module.audit_github_issue_execution_state(github_issues=github_issues) == []


def test_github_issue_execution_state_audit_rejects_missing_github_issue(
    tmp_path: Path,
) -> None:
    module = _load_audit()
    ledger = _load_ledger()
    ledger["issues"] = [
        entry
        for entry in ledger["issues"]
        if isinstance(entry, dict) and entry["issueNumber"] in {681, 690}
    ]
    github_payload = [
        issue
        for issue in _github_issue_payload(ledger)
        if isinstance(issue, dict) and issue["number"] != 690
    ]
    github_issues = module._parse_github_issue_states(github_payload)

    errors = module.audit_github_issue_execution_state(
        ledger_path=_write_ledger(tmp_path, ledger),
        github_issues=github_issues,
    )

    assert "#690: missing from GitHub issue state" in errors
    assert "GitHub state input omitted ledger issues: #690" in errors


def test_github_issue_execution_state_audit_rejects_auto_closed_open_issue(
    tmp_path: Path,
) -> None:
    module = _load_audit()
    ledger = _load_ledger()
    ledger["issues"] = [
        entry
        for entry in ledger["issues"]
        if isinstance(entry, dict) and entry["issueNumber"] == 690
    ]
    github_payload = _github_issue_payload(ledger)
    github_payload[0]["state"] = "CLOSED"
    github_issues = module._parse_github_issue_states(github_payload)

    errors = module.audit_github_issue_execution_state(
        ledger_path=_write_ledger(tmp_path, ledger),
        github_issues=github_issues,
    )

    assert "#690: ledger githubState=open but GitHub state=closed" in errors


def test_github_issue_execution_state_audit_rejects_missing_status_label(
    tmp_path: Path,
) -> None:
    module = _load_audit()
    ledger = _load_ledger()
    ledger["issues"] = [
        entry
        for entry in ledger["issues"]
        if isinstance(entry, dict) and entry["issueNumber"] == 681
    ]
    github_payload = _github_issue_payload(ledger)
    github_payload[0]["labels"] = [
        label for label in github_payload[0]["labels"] if label["name"] != "status/in-progress"
    ]
    github_issues = module._parse_github_issue_states(github_payload)

    errors = module.audit_github_issue_execution_state(
        ledger_path=_write_ledger(tmp_path, ledger),
        github_issues=github_issues,
    )

    assert (
        "#681: executionStatus=open_in_progress requires GitHub label status/in-progress" in errors
    )


def test_github_issue_execution_state_audit_rejects_closed_issue_without_merged_main_label(
    tmp_path: Path,
) -> None:
    module = _load_audit()
    ledger = _load_ledger()
    ledger["issues"] = [
        entry
        for entry in ledger["issues"]
        if isinstance(entry, dict) and entry["issueNumber"] == 695
    ]
    github_payload = _github_issue_payload(ledger)
    github_payload[0]["labels"] = [
        label for label in github_payload[0]["labels"] if label["name"] != "status/merged-main"
    ]
    github_issues = module._parse_github_issue_states(github_payload)

    errors = module.audit_github_issue_execution_state(
        ledger_path=_write_ledger(tmp_path, ledger),
        github_issues=github_issues,
    )

    assert "#695: closed_complete requires GitHub label status/merged-main" in errors
