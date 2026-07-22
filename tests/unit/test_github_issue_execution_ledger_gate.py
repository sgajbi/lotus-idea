from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, cast


ROOT = Path(__file__).resolve().parents[2]


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "github_issue_execution_ledger_gate.py"
    spec = importlib.util.spec_from_file_location(
        "github_issue_execution_ledger_gate",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _ledger_payload(module: ModuleType) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(module.LEDGER_PATH.read_text(encoding="utf-8")))


def _write_ledger(tmp_path: Path, payload: dict[str, Any]) -> Path:
    path = tmp_path / "ledger.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def test_rfc0002_github_issue_execution_ledger_gate_passes_current_ledger() -> None:
    module = _load_gate()

    assert module.validate_github_issue_execution_ledger() == []


def test_rfc0002_github_issue_execution_ledger_requires_current_issue_690(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    payload["issues"] = [
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] != 690
    ]

    errors = module.validate_github_issue_execution_ledger(_write_ledger(tmp_path, payload))

    assert "Missing RFC-0002 execution issue entries: #690" in errors


def test_rfc0002_github_issue_execution_ledger_keeps_advise_live_proof_blocked() -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    issue_688 = next(
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 688
    )

    assert issue_688["githubState"] == "open"
    assert issue_688["executionStatus"] == "open_blocked"
    assert issue_688["allowPullRequestAutoClose"] is False
    assert "Keep #688 open" in issue_688["closureInstruction"]
    assert "advise_live_contract_proof_missing" in issue_688["closureInstruction"]


def test_rfc0002_github_issue_execution_ledger_keeps_report_live_proof_blocked() -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    issue_690 = next(
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 690
    )

    assert issue_690["githubState"] == "open"
    assert issue_690["executionStatus"] == "open_blocked"
    assert issue_690["allowPullRequestAutoClose"] is False
    assert "Keep #690 open" in issue_690["closureInstruction"]
    assert "live Report intake/materialization" in issue_690["closureInstruction"]
    assert "Render output" in issue_690["closureInstruction"]
    assert "Archive record" in issue_690["closureInstruction"]


def test_rfc0002_github_issue_execution_ledger_blocks_auto_close_wording_for_open_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    for issue in payload["issues"]:
        if isinstance(issue, dict) and issue["issueNumber"] == 690:
            issue["closureInstruction"] = "Closes #690 after partial Report source proof."
            break

    errors = module.validate_github_issue_execution_ledger(_write_ledger(tmp_path, payload))

    assert "#690: open issue closureInstruction must contain Keep #690 open" in errors
    assert (
        "#690: open issue closureInstruction must not contain GitHub auto-close wording" in errors
    )


def test_rfc0002_github_issue_execution_ledger_blocks_open_issue_auto_close_flag(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    for issue in payload["issues"]:
        if isinstance(issue, dict) and issue["issueNumber"] == 681:
            issue["allowPullRequestAutoClose"] = True
            break

    errors = module.validate_github_issue_execution_ledger(_write_ledger(tmp_path, payload))

    assert "#681: open issue cannot allow PR auto-close" in errors


def test_rfc0002_github_issue_execution_ledger_blocks_closed_issue_without_closed_instruction(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    for issue in payload["issues"]:
        if isinstance(issue, dict) and issue["issueNumber"] == 695:
            issue["closureInstruction"] = "Keep #695 open for more dependency evidence."
            break

    errors = module.validate_github_issue_execution_ledger(_write_ledger(tmp_path, payload))

    assert "#695: closed issue closureInstruction must contain Closed #695" in errors
