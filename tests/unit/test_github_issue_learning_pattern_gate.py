from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, cast


ROOT = Path(__file__).resolve().parents[2]


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "github_issue_learning_pattern_gate.py"
    spec = importlib.util.spec_from_file_location(
        "github_issue_learning_pattern_gate",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _pattern_payload(module: ModuleType) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(module.PATTERN_LEDGER_PATH.read_text(encoding="utf-8")))


def _write_pattern_payload(tmp_path: Path, payload: dict[str, Any]) -> Path:
    path = tmp_path / "issue-learning-patterns.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def test_github_issue_learning_pattern_gate_passes_current_ledger() -> None:
    module = _load_gate()

    assert module.validate_github_issue_learning_patterns() == []


def test_github_issue_learning_pattern_gate_requires_all_non_complete_issues(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    payload = _pattern_payload(module)
    for pattern in payload["patterns"]:
        if pattern["patternId"] == "downstream_owner_runtime_proof_boundary":
            pattern["currentLedgerIssueNumbers"].remove(690)
            break

    errors = module.validate_github_issue_learning_patterns(
        _write_pattern_payload(tmp_path, payload)
    )

    assert (
        "non-complete RFC-0002 execution issues missing from issue-learning patterns: #690"
        in errors
    )


def test_github_issue_learning_pattern_gate_rejects_unknown_current_issue(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    payload = _pattern_payload(module)
    payload["patterns"][0]["currentLedgerIssueNumbers"].append(999999)

    errors = module.validate_github_issue_learning_patterns(
        _write_pattern_payload(tmp_path, payload)
    )

    assert (
        "github_execution_control_and_context_sync.currentLedgerIssueNumbers "
        "contains non-ledger issues: #999999"
    ) in errors
    assert (
        "issue-learning patterns reference issues outside the RFC-0002 execution ledger: #999999"
        in errors
    )


def test_github_issue_learning_pattern_gate_rejects_missing_local_control(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    payload = _pattern_payload(module)
    payload["patterns"][0]["durableControls"][0]["ref"] = "scripts/missing_gate.py"

    errors = module.validate_github_issue_learning_patterns(
        _write_pattern_payload(tmp_path, payload)
    )

    assert (
        "github_execution_control_and_context_sync.durableControls[0].ref "
        "does not exist: scripts/missing_gate.py"
    ) in errors


def test_github_issue_learning_pattern_gate_rejects_weak_future_rule(
    tmp_path: Path,
) -> None:
    module = _load_gate()
    payload = _pattern_payload(module)
    payload["patterns"][0]["futureAgentRule"] = "Check issues."

    errors = module.validate_github_issue_learning_patterns(
        _write_pattern_payload(tmp_path, payload)
    )

    assert (
        "github_execution_control_and_context_sync.futureAgentRule must contain actionable guidance"
        in errors
    )
