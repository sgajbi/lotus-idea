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


def test_rfc0002_github_issue_execution_ledger_tracks_issue_874_posture_contract() -> None:
    module = _load_gate()
    payload = _ledger_payload(module)
    issue_874 = next(
        issue
        for issue in payload["issues"]
        if isinstance(issue, dict) and issue["issueNumber"] == 874
    )

    assert issue_874["githubState"] == "open"
    assert issue_874["executionStatus"] == "open_in_progress"
    assert issue_874["allowPullRequestAutoClose"] is False
    assert issue_874["rfcSlices"] == ["slice-18"]
    assert "Keep #874 open and status/in-progress" in issue_874["closureInstruction"]
    assert (
        "contracts/implementation-proof/rfc0002-issue-posture-snapshot.v1.json"
        in issue_874["closureInstruction"]
    )
    assert "scripts/documentation_stale_claims.py" in issue_874["closureInstruction"]
    assert "documentation-contract-gate" in issue_874["closureInstruction"]
    assert "59 tracked RFC-0002 issues" in issue_874["closureInstruction"]
    assert "128 label-backed RFC-0002 issues" in issue_874["closureInstruction"]
    assert "Keep #681 open" in issue_874["closureInstruction"]
    assert "does not promote supported features" in issue_874["closureInstruction"]
