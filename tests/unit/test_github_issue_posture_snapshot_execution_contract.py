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


def test_rfc0002_github_issue_execution_ledger_closes_issue_874_posture_contract() -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    issue_874 = next(
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 874
    )

    assert issue_874["githubState"] == "closed"
    assert issue_874["executionStatus"] == "closed_complete"
    assert issue_874["allowPullRequestAutoClose"] is True
    assert issue_874["rfcSlices"] == ["slice-18"]
    assert "Closed #874 after PR #875" in issue_874["closureInstruction"]
    assert "6889123bcbe742ccb3da074a12d5b94f2c1589e1" in issue_874["closureInstruction"]
    assert "31325174863" in issue_874["closureInstruction"]
    assert "lotus-idea.wiki commit 5b52566" in issue_874["closureInstruction"]
    assert (
        "contracts/implementation-proof/rfc0002-issue-posture-snapshot.v1.json"
        in issue_874["closureInstruction"]
    )
    assert "59 tracked RFC-0002 issues" in issue_874["closureInstruction"]
    assert "34 closed and 25 open" in issue_874["closureInstruction"]
    assert "90 closed and 38 open" in issue_874["closureInstruction"]
    assert "does not close #681" in issue_874["closureInstruction"]
    assert "does not promote supported features" in issue_874["closureInstruction"]
