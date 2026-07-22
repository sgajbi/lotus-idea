# ruff: noqa: E402
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.github_issue_execution_ledger_gate import _load_json

PATTERN_LEDGER_PATH = (
    ROOT / "contracts" / "implementation-proof" / "rfc0002-issue-learning-patterns.v1.json"
)

EXPECTED_SCHEMA_VERSION = "lotus-idea:rfc0002-issue-learning-patterns:v1"
EXPECTED_RFC_ID = "RFC-0002"
EXPECTED_REPOSITORY = "sgajbi/lotus-idea"

CONTROL_TYPES_WITH_LOCAL_REFS = frozenset(
    {"context", "contract", "docs", "gate", "quality", "wiki"}
)
REQUIRED_PATTERN_IDS = frozenset(
    {
        "github_execution_control_and_context_sync",
        "workbench_gateway_surface_proof_boundary",
        "downstream_owner_runtime_proof_boundary",
        "data_mesh_promotion_and_runtime_telemetry",
        "operations_security_resilience_certification",
        "ai_attestation_and_model_governance",
        "demo_commercial_and_live_journey_claims",
    }
)


def _local_ref_exists(ref: str) -> bool:
    path_part = ref.split("#", 1)[0]
    if not path_part:
        return False
    return (ROOT / path_part).exists()


def _require_int_list(
    pattern: dict[str, Any],
    field: str,
    *,
    pattern_id: str,
    allow_empty: bool = False,
) -> list[int]:
    value = pattern.get(field)
    if not isinstance(value, list):
        raise ValueError(f"{pattern_id}.{field} must be a list")
    if not value and not allow_empty:
        raise ValueError(f"{pattern_id}.{field} must not be empty")
    if not all(isinstance(item, int) for item in value):
        raise ValueError(f"{pattern_id}.{field} must contain only issue numbers")
    return value


def _require_string_list(pattern: dict[str, Any], field: str, *, pattern_id: str) -> list[str]:
    value = pattern.get(field)
    if not isinstance(value, list) or not value:
        raise ValueError(f"{pattern_id}.{field} must be a non-empty list")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{pattern_id}.{field} must contain non-empty strings")
    return value


def _load_execution_issues(pattern_payload: dict[str, Any]) -> tuple[set[int], set[int]]:
    ledger_ref = pattern_payload.get("executionLedgerRef")
    if not isinstance(ledger_ref, str) or not ledger_ref.strip():
        raise ValueError("executionLedgerRef is required")
    ledger_payload = _load_json(ROOT / ledger_ref)
    raw_issues = ledger_payload.get("issues")
    if not isinstance(raw_issues, list):
        raise ValueError("execution ledger issues must be a list")

    all_issues: set[int] = set()
    non_complete: set[int] = set()
    for index, issue in enumerate(raw_issues):
        if not isinstance(issue, dict):
            raise ValueError(f"execution ledger issues[{index}] must be an object")
        issue_number = issue.get("issueNumber")
        execution_status = issue.get("executionStatus")
        if not isinstance(issue_number, int):
            raise ValueError(f"execution ledger issues[{index}].issueNumber must be an integer")
        if not isinstance(execution_status, str):
            raise ValueError(f"#{issue_number}: executionStatus must be a string")
        all_issues.add(issue_number)
        if execution_status != "closed_complete":
            non_complete.add(issue_number)
    return all_issues, non_complete


def validate_github_issue_learning_patterns(path: Path = PATTERN_LEDGER_PATH) -> list[str]:
    try:
        payload = _load_json(path)
        execution_issues, non_complete_execution_issues = _load_execution_issues(payload)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        return [str(exc)]

    errors: list[str] = []
    if payload.get("schemaVersion") != EXPECTED_SCHEMA_VERSION:
        errors.append("schemaVersion must be lotus-idea:rfc0002-issue-learning-patterns:v1")
    if payload.get("rfcId") != EXPECTED_RFC_ID:
        errors.append("rfcId must be RFC-0002")
    if payload.get("repository") != EXPECTED_REPOSITORY:
        errors.append("repository must be sgajbi/lotus-idea")

    patterns = payload.get("patterns")
    if not isinstance(patterns, list) or not patterns:
        errors.append("patterns must be a non-empty list")
        return errors

    pattern_ids: list[str] = []
    covered_current_issues: set[int] = set()
    for index, raw_pattern in enumerate(patterns):
        if not isinstance(raw_pattern, dict):
            errors.append(f"patterns[{index}] must be an object")
            continue
        pattern_id = raw_pattern.get("patternId")
        if not isinstance(pattern_id, str) or not pattern_id.strip():
            errors.append(f"patterns[{index}].patternId is required")
            continue
        pattern_ids.append(pattern_id)
        errors.extend(_validate_pattern(raw_pattern, pattern_id, execution_issues))
        current_issues = raw_pattern.get("currentLedgerIssueNumbers")
        if isinstance(current_issues, list):
            covered_current_issues.update(
                issue_number for issue_number in current_issues if isinstance(issue_number, int)
            )

    duplicate_pattern_ids = sorted(
        pattern_id for pattern_id, count in Counter(pattern_ids).items() if count > 1
    )
    if duplicate_pattern_ids:
        errors.append("duplicate patternId values: " + ", ".join(duplicate_pattern_ids))

    missing_pattern_ids = sorted(REQUIRED_PATTERN_IDS - set(pattern_ids))
    if missing_pattern_ids:
        errors.append("missing required patternId values: " + ", ".join(missing_pattern_ids))

    missing_issue_coverage = sorted(non_complete_execution_issues - covered_current_issues)
    if missing_issue_coverage:
        errors.append(
            "non-complete RFC-0002 execution issues missing from issue-learning patterns: "
            + ", ".join(f"#{issue_number}" for issue_number in missing_issue_coverage)
        )
    unknown_current_issues = sorted(covered_current_issues - execution_issues)
    if unknown_current_issues:
        errors.append(
            "issue-learning patterns reference issues outside the RFC-0002 execution ledger: "
            + ", ".join(f"#{issue_number}" for issue_number in unknown_current_issues)
        )
    return errors


def _validate_pattern(
    pattern: dict[str, Any],
    pattern_id: str,
    execution_issues: set[int],
) -> list[str]:
    errors: list[str] = []
    try:
        current_issues = _require_int_list(
            pattern,
            "currentLedgerIssueNumbers",
            pattern_id=pattern_id,
        )
        _require_int_list(pattern, "relatedIssueNumbers", pattern_id=pattern_id)
        _require_string_list(pattern, "rfcSlices", pattern_id=pattern_id)
        non_claim_boundaries = _require_string_list(
            pattern,
            "nonClaimBoundaries",
            pattern_id=pattern_id,
        )
    except ValueError as exc:
        return [str(exc)]

    title = pattern.get("title")
    if not isinstance(title, str) or len(title.strip()) < 20:
        errors.append(f"{pattern_id}.title must be a descriptive string")
    future_agent_rule = pattern.get("futureAgentRule")
    if not isinstance(future_agent_rule, str) or len(future_agent_rule.strip()) < 40:
        errors.append(f"{pattern_id}.futureAgentRule must contain actionable guidance")

    missing_current = sorted(set(current_issues) - execution_issues)
    if missing_current:
        errors.append(
            f"{pattern_id}.currentLedgerIssueNumbers contains non-ledger issues: "
            + ", ".join(f"#{issue_number}" for issue_number in missing_current)
        )
    if len(non_claim_boundaries) < 2:
        errors.append(f"{pattern_id}.nonClaimBoundaries must contain at least two boundaries")

    controls = pattern.get("durableControls")
    if not isinstance(controls, list) or len(controls) < 2:
        errors.append(f"{pattern_id}.durableControls must contain at least two controls")
        return errors
    for control_index, control in enumerate(controls):
        if not isinstance(control, dict):
            errors.append(f"{pattern_id}.durableControls[{control_index}] must be an object")
            continue
        control_type = control.get("type")
        ref = control.get("ref")
        if not isinstance(control_type, str) or not control_type.strip():
            errors.append(f"{pattern_id}.durableControls[{control_index}].type is required")
        if not isinstance(ref, str) or not ref.strip():
            errors.append(f"{pattern_id}.durableControls[{control_index}].ref is required")
            continue
        if control_type in CONTROL_TYPES_WITH_LOCAL_REFS and not _local_ref_exists(ref):
            errors.append(
                f"{pattern_id}.durableControls[{control_index}].ref does not exist: {ref}"
            )
    return errors


def main() -> int:
    errors = validate_github_issue_learning_patterns()
    if errors:
        print("\n".join(errors))
        return 1
    print("RFC-0002 GitHub issue learning pattern gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
