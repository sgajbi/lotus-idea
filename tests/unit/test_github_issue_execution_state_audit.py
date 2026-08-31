from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from types import SimpleNamespace
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
        "open_ready": "status/ready",
        "open_blocked": "status/blocked",
        "open_in_progress": "status/in-progress",
        "open_fixed_local": "status/fixed-local",
        "open_pr_raised": "status/pr-open",
        "open_merged_main_qa_pending": "status/merged-main",
        "open_tracker": "status/tracker",
        "open_pending_final_closure": "status/blocked",
        "open_pending_post_completion": "status/blocked",
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


def _current_blocker_states(module: ModuleType, ledger: dict[str, Any]) -> dict[str, Any]:
    issue_refs = {
        issue_ref
        for entry in ledger["issues"]
        if isinstance(entry, dict)
        for issue_ref in entry.get("currentBlockerIssueRefs", [])
    }
    return {
        issue_ref: module.GitHubIssueState(
            issue_number=int(issue_ref.rsplit("#", maxsplit=1)[1]),
            state="OPEN",
            labels=frozenset({"status/blocked", "rfc/RFC-0002"}),
            title=f"Current blocker {issue_ref}",
            url=f"https://github.com/{issue_ref.replace('#', '/issues/')}",
        )
        for issue_ref in issue_refs
    }


def test_github_issue_execution_state_audit_passes_matching_issue_state() -> None:
    module = _load_audit()
    ledger = _load_ledger()
    github_issues = module._parse_github_issue_states(_github_issue_payload(ledger))

    assert (
        module.audit_github_issue_execution_state(
            github_issues=github_issues,
            current_blocker_issues=_current_blocker_states(module, ledger),
        )
        == []
    )


def test_github_issue_execution_state_audit_rejects_closed_current_blocker() -> None:
    module = _load_audit()
    ledger = _load_ledger()
    github_issues = module._parse_github_issue_states(_github_issue_payload(ledger))
    blocker_issues = _current_blocker_states(module, ledger)
    blocker_issues["sgajbi/lotus-workbench#904"] = module.GitHubIssueState(
        issue_number=904,
        state="CLOSED",
        labels=frozenset({"status/merged-main"}),
        title="Resolved Workbench blocker",
        url="https://github.com/sgajbi/lotus-workbench/issues/904",
    )

    errors = module.audit_github_issue_execution_state(
        github_issues=github_issues,
        current_blocker_issues=blocker_issues,
    )

    assert "#814: current blocker sgajbi/lotus-workbench#904 is closed on GitHub" in errors


def test_github_issue_execution_state_audit_rejects_missing_current_blocker() -> None:
    module = _load_audit()
    ledger = _load_ledger()
    github_issues = module._parse_github_issue_states(_github_issue_payload(ledger))
    blocker_issues = _current_blocker_states(module, ledger)
    blocker_issues.pop("sgajbi/lotus-advise#557")

    errors = module.audit_github_issue_execution_state(
        github_issues=github_issues,
        current_blocker_issues=blocker_issues,
    )

    assert (
        "#814: current blocker sgajbi/lotus-advise#557 is missing from GitHub blocker issue state"
        in errors
    )


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


def test_fetch_github_issue_states_recovers_required_issue_outside_list_window(
    monkeypatch: Any,
) -> None:
    module = _load_audit()
    ledger = _load_ledger()
    scoped_entries = [
        entry
        for entry in ledger["issues"]
        if isinstance(entry, dict) and entry["issueNumber"] in {340, 681}
    ]
    ledger["issues"] = scoped_entries
    payload_by_number = {issue["number"]: issue for issue in _github_issue_payload(ledger)}
    commands: list[list[str]] = []

    monkeypatch.setattr(
        module,
        "fetch_repository_issue_counts",
        lambda **kwargs: SimpleNamespace(total=1),
    )
    monkeypatch.setattr(
        module,
        "fetch_complete_issue_list",
        lambda **kwargs: [payload_by_number[681]],
    )

    def fake_run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> SimpleNamespace:
        assert check is False
        assert capture_output is True
        assert text is True
        commands.append(command)
        if command[:3] == ["gh", "issue", "view"]:
            return SimpleNamespace(
                returncode=0,
                stdout=json.dumps(payload_by_number[int(command[3])]),
                stderr="",
            )
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    states = module.fetch_github_issue_states(
        repository="sgajbi/lotus-idea",
        required_issue_numbers={340, 681},
    )

    assert sorted(states) == [340, 681]
    assert commands == [
        [
            "gh",
            "issue",
            "view",
            "340",
            "--repo",
            "sgajbi/lotus-idea",
            "--json",
            module.GITHUB_ISSUE_FIELDS,
        ]
    ]


def test_fetch_github_issue_reference_states_queries_owning_repository(
    monkeypatch: Any,
) -> None:
    module = _load_audit()
    commands: list[list[str]] = []

    def fake_run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> SimpleNamespace:
        commands.append(command)
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "number": 904,
                    "state": "OPEN",
                    "title": "Workbench blocker",
                    "url": "https://github.com/sgajbi/lotus-workbench/issues/904",
                    "labels": [{"name": "status/blocked"}],
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    states = module.fetch_github_issue_reference_states(
        ["sgajbi/lotus-workbench#904", "sgajbi/lotus-workbench#904"]
    )

    assert states["sgajbi/lotus-workbench#904"].state == "OPEN"
    assert commands == [
        [
            "gh",
            "issue",
            "view",
            "904",
            "--repo",
            "sgajbi/lotus-workbench",
            "--json",
            module.GITHUB_ISSUE_FIELDS,
        ]
    ]


def test_github_issue_execution_state_audit_allows_github_owned_issue_outside_legacy_ledger(
    tmp_path: Path,
) -> None:
    module = _load_audit()
    ledger = _load_ledger()
    github_payload = _github_issue_payload(ledger)
    github_payload.append(
        {
            "number": 999,
            "state": "OPEN",
            "title": "RFC-labeled issue outside ledger",
            "url": "https://github.com/sgajbi/lotus-idea/issues/999",
            "labels": [{"name": "rfc/RFC-0002"}, {"name": "status/blocked"}],
        }
    )
    github_issues = module._parse_github_issue_states(github_payload)

    assert (
        module.audit_github_issue_execution_state(
            ledger_path=_write_ledger(tmp_path, ledger),
            github_issues=github_issues,
        )
        == []
    )


def test_github_issue_execution_state_audit_rejects_auto_closed_open_issue(
    tmp_path: Path,
) -> None:
    module = _load_audit()
    ledger = _load_ledger()
    ledger["issues"] = [
        entry
        for entry in ledger["issues"]
        if isinstance(entry, dict) and entry["issueNumber"] == 691
    ]
    github_payload = _github_issue_payload(ledger)
    github_payload[0]["state"] = "CLOSED"
    github_issues = module._parse_github_issue_states(github_payload)

    errors = module.audit_github_issue_execution_state(
        ledger_path=_write_ledger(tmp_path, ledger),
        github_issues=github_issues,
    )

    assert "#691: ledger githubState=open but GitHub state=closed" in errors


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
    status_label = next(
        label["name"]
        for label in github_payload[0]["labels"]
        if label["name"].startswith("status/")
    )
    github_payload[0]["labels"] = [
        label for label in github_payload[0]["labels"] if label["name"] != status_label
    ]
    github_issues = module._parse_github_issue_states(github_payload)

    errors = module.audit_github_issue_execution_state(
        ledger_path=_write_ledger(tmp_path, ledger),
        github_issues=github_issues,
    )

    issue_681_execution_status = ledger["issues"][0]["executionStatus"]
    assert (
        f"#681: executionStatus={issue_681_execution_status} requires GitHub label {status_label}"
    ) in errors


def test_github_issue_execution_state_audit_rejects_conflicting_status_labels(
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
    status_label = next(
        label["name"]
        for label in github_payload[0]["labels"]
        if label["name"].startswith("status/")
    )
    github_payload[0]["labels"].append({"name": "status/ready"})
    github_issues = module._parse_github_issue_states(github_payload)

    errors = module.audit_github_issue_execution_state(
        ledger_path=_write_ledger(tmp_path, ledger),
        github_issues=github_issues,
    )

    issue_681_execution_status = ledger["issues"][0]["executionStatus"]
    assert (
        f"#681: executionStatus={issue_681_execution_status} allows only GitHub status label "
        f"{status_label}; found conflicting status label(s): status/ready"
    ) in errors


def test_github_issue_execution_state_audit_accepts_merged_main_status_label() -> None:
    module = _load_audit()
    ledger = _load_ledger()
    github_payload = _github_issue_payload(ledger)
    issue_689 = next(issue for issue in github_payload if issue["number"] == 689)

    assert issue_689["state"] == "CLOSED"
    assert {"name": "status/merged-main"} in issue_689["labels"]
    github_issues = module._parse_github_issue_states(github_payload)
    assert module.audit_github_issue_execution_state(github_issues=github_issues) == []


def test_github_issue_execution_state_audit_rejects_tracker_without_tracker_label(
    tmp_path: Path,
) -> None:
    module = _load_audit()
    ledger = _load_ledger()
    ledger["issues"] = [
        entry
        for entry in ledger["issues"]
        if isinstance(entry, dict) and entry["issueNumber"] == 673
    ]
    github_payload = _github_issue_payload(ledger)
    github_payload[0]["labels"] = [
        label for label in github_payload[0]["labels"] if label["name"] != "status/tracker"
    ]
    github_issues = module._parse_github_issue_states(github_payload)

    errors = module.audit_github_issue_execution_state(
        ledger_path=_write_ledger(tmp_path, ledger),
        github_issues=github_issues,
    )

    assert "#673: executionStatus=open_tracker requires GitHub label status/tracker" in errors


def test_github_issue_execution_state_audit_rejects_pending_final_closure_ready_label(
    tmp_path: Path,
) -> None:
    module = _load_audit()
    ledger = _load_ledger()
    ledger["issues"] = [
        entry
        for entry in ledger["issues"]
        if isinstance(entry, dict) and entry["issueNumber"] == 683
    ]
    github_payload = _github_issue_payload(ledger)
    github_payload[0]["labels"] = [
        {"name": "rfc/RFC-0002"},
        {"name": "rfc/RFC-0002/slice-20"},
        {"name": "status/ready"},
    ]
    github_issues = module._parse_github_issue_states(github_payload)

    errors = module.audit_github_issue_execution_state(
        ledger_path=_write_ledger(tmp_path, ledger),
        github_issues=github_issues,
    )

    assert (
        "#683: executionStatus=open_pending_final_closure requires GitHub label status/blocked"
    ) in errors


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
