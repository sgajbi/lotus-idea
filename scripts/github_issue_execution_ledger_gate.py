from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = (
    ROOT / "contracts" / "implementation-proof" / "rfc0002-github-issue-execution-ledger.v1.json"
)
POLICY_PATH = (
    ROOT
    / "contracts"
    / "implementation-proof"
    / "rfc0002-github-issue-execution-ledger-gate-policy.v1.json"
)
EXPECTED_POLICY_SCHEMA_VERSION = "lotus-idea:rfc0002-github-issue-execution-ledger-gate-policy:v1"
OPEN_STATUSES = frozenset(
    "open_tracker open_ready open_blocked open_in_progress open_fixed_local "
    "open_pr_raised open_merged_main_qa_pending open_pending_final_closure "
    "open_pending_post_completion".split()
)
CLOSED_STATUSES = frozenset({"closed_complete"})
AUTO_CLOSE_KEYWORDS = tuple("close closes closed fix fixes fixed resolve resolves resolved".split())


@dataclass(frozen=True)
class GatePolicy:
    ledger_schema_version: str
    rfc_id: str
    repository: str
    expected_issue_numbers: frozenset[int]
    required_evidence_only_sync_policy_fragments: tuple[str, ...]
    required_open_issue_evidence: dict[int, tuple[str, ...]]
    required_closed_issue_evidence: dict[int, tuple[str, ...]]


@dataclass(frozen=True)
class IssueEntry:
    issue_number: int
    github_state: str
    execution_status: str
    allow_pull_request_auto_close: bool
    closure_instruction: str
    rfc_slices: tuple[str, ...]


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"{path.relative_to(ROOT).as_posix()} is missing")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.relative_to(ROOT).as_posix()} must contain a JSON object")
    return payload


def _required_evidence_map(payload: dict[str, Any], key: str) -> dict[int, tuple[str, ...]]:
    raw_map = payload.get(key)
    if not isinstance(raw_map, dict):
        raise ValueError(f"{key} must be an object")

    evidence: dict[int, tuple[str, ...]] = {}
    for raw_issue_number, raw_fragments in raw_map.items():
        try:
            issue_number = int(raw_issue_number)
        except ValueError as exc:
            raise ValueError(f"{key}.{raw_issue_number} must use an integer issue number") from exc
        if not isinstance(raw_fragments, list) or not raw_fragments:
            raise ValueError(f"{key}.{issue_number} must be a non-empty list")
        if not all(isinstance(fragment, str) and fragment for fragment in raw_fragments):
            raise ValueError(f"{key}.{issue_number} must contain non-empty strings")
        evidence[issue_number] = tuple(raw_fragments)
    return evidence


def _load_gate_policy(path: Path = POLICY_PATH) -> GatePolicy:
    payload = _load_json(path)

    if payload.get("schemaVersion") != EXPECTED_POLICY_SCHEMA_VERSION:
        raise ValueError(f"schemaVersion must be {EXPECTED_POLICY_SCHEMA_VERSION}")

    ledger_schema_version = payload.get("ledgerSchemaVersion")
    rfc_id = payload.get("rfcId")
    repository = payload.get("repository")
    expected_issue_numbers = payload.get("expectedIssueNumbers")
    evidence_only_fragments = payload.get("requiredEvidenceOnlySyncPolicyFragments")

    if not isinstance(ledger_schema_version, str) or not ledger_schema_version:
        raise ValueError("ledgerSchemaVersion is required")
    if not isinstance(rfc_id, str) or not rfc_id:
        raise ValueError("rfcId is required")
    if not isinstance(repository, str) or not repository:
        raise ValueError("repository is required")
    if not isinstance(expected_issue_numbers, list) or not expected_issue_numbers:
        raise ValueError("expectedIssueNumbers must be a non-empty list")
    if not all(isinstance(number, int) for number in expected_issue_numbers):
        raise ValueError("expectedIssueNumbers must contain integers")
    if len(expected_issue_numbers) != len(set(expected_issue_numbers)):
        raise ValueError("expectedIssueNumbers must not contain duplicates")
    if not isinstance(evidence_only_fragments, list) or not evidence_only_fragments:
        raise ValueError("requiredEvidenceOnlySyncPolicyFragments must be a non-empty list")
    if not all(isinstance(fragment, str) and fragment for fragment in evidence_only_fragments):
        raise ValueError("requiredEvidenceOnlySyncPolicyFragments must contain non-empty strings")

    return GatePolicy(
        ledger_schema_version=ledger_schema_version,
        rfc_id=rfc_id,
        repository=repository,
        expected_issue_numbers=frozenset(expected_issue_numbers),
        required_evidence_only_sync_policy_fragments=tuple(evidence_only_fragments),
        required_open_issue_evidence=_required_evidence_map(payload, "requiredOpenIssueEvidence"),
        required_closed_issue_evidence=_required_evidence_map(
            payload, "requiredClosedIssueEvidence"
        ),
    )


def _entries(payload: dict[str, Any]) -> list[IssueEntry]:
    raw_issues = payload.get("issues")
    if not isinstance(raw_issues, list):
        raise ValueError("issues must be a list")

    entries: list[IssueEntry] = []
    for index, raw_entry in enumerate(raw_issues):
        if not isinstance(raw_entry, dict):
            raise ValueError(f"issues[{index}] must be an object")
        issue_number = raw_entry.get("issueNumber")
        github_state = raw_entry.get("githubState")
        execution_status = raw_entry.get("executionStatus")
        allow_pull_request_auto_close = raw_entry.get("allowPullRequestAutoClose")
        closure_instruction = raw_entry.get("closureInstruction")
        rfc_slices = raw_entry.get("rfcSlices")
        if not isinstance(issue_number, int):
            raise ValueError(f"issues[{index}].issueNumber must be an integer")
        if github_state not in {"open", "closed"}:
            raise ValueError(f"#{issue_number}: githubState must be open or closed")
        if not isinstance(execution_status, str):
            raise ValueError(f"#{issue_number}: executionStatus must be a string")
        if not isinstance(allow_pull_request_auto_close, bool):
            raise ValueError(f"#{issue_number}: allowPullRequestAutoClose must be boolean")
        if not isinstance(closure_instruction, str) or not closure_instruction.strip():
            raise ValueError(f"#{issue_number}: closureInstruction is required")
        if not isinstance(rfc_slices, list) or not rfc_slices:
            raise ValueError(f"#{issue_number}: rfcSlices must be a non-empty list")
        if not all(isinstance(slice_id, str) for slice_id in rfc_slices):
            raise ValueError(f"#{issue_number}: every rfcSlices entry must be a string")
        entries.append(
            IssueEntry(
                issue_number=issue_number,
                github_state=github_state,
                execution_status=execution_status,
                allow_pull_request_auto_close=allow_pull_request_auto_close,
                closure_instruction=closure_instruction,
                rfc_slices=tuple(rfc_slices),
            )
        )
    return entries


def _auto_close_phrase_re(issue_number: int) -> re.Pattern[str]:
    keywords = "|".join(re.escape(keyword) for keyword in AUTO_CLOSE_KEYWORDS)
    return re.compile(rf"(?<![-\w])(?:{keywords})\s+#{issue_number}\b", re.IGNORECASE)


def validate_github_issue_execution_ledger(
    path: Path = LEDGER_PATH,
    policy_path: Path = POLICY_PATH,
) -> list[str]:
    try:
        payload = _load_json(path)
        gate_policy = _load_gate_policy(policy_path)
        entries = _entries(payload)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        return [str(exc)]

    errors: list[str] = []
    if payload.get("schemaVersion") != gate_policy.ledger_schema_version:
        errors.append(f"schemaVersion must be {gate_policy.ledger_schema_version}")
    if payload.get("rfcId") != gate_policy.rfc_id:
        errors.append(f"rfcId must be {gate_policy.rfc_id}")
    if payload.get("repository") != gate_policy.repository:
        errors.append(f"repository must be {gate_policy.repository}")
    policy = payload.get("policy")
    if not isinstance(policy, dict):
        errors.append("policy must be an object")
    else:
        policy_key = "evidenceOnlySyncPrRule"
        policy_value = policy.get(policy_key)
        if not isinstance(policy_value, str) or not policy_value.strip():
            errors.append(f"policy.{policy_key} is required")
        else:
            for fragment in gate_policy.required_evidence_only_sync_policy_fragments:
                if fragment not in policy_value:
                    errors.append(f"policy.{policy_key} missing required evidence `{fragment}`")

    seen: set[int] = set()
    for entry in entries:
        number = entry.issue_number
        if number in seen:
            errors.append(f"#{number}: duplicate issue entry")
        seen.add(number)
        if number not in gate_policy.expected_issue_numbers:
            errors.append(f"#{number}: issue is not in the RFC-0002 execution issue set")

        if entry.github_state == "open":
            if entry.execution_status not in OPEN_STATUSES:
                errors.append(f"#{number}: open issue has invalid executionStatus")
            if entry.allow_pull_request_auto_close:
                errors.append(f"#{number}: open issue cannot allow PR auto-close")
            if f"Keep #{number} open" not in entry.closure_instruction:
                errors.append(
                    f"#{number}: open issue closureInstruction must contain Keep #{number} open"
                )
            if _auto_close_phrase_re(number).search(entry.closure_instruction):
                errors.append(
                    f"#{number}: open issue closureInstruction must not contain GitHub "
                    "auto-close wording"
                )
            for fragment in gate_policy.required_open_issue_evidence.get(number, ()):
                if fragment not in entry.closure_instruction:
                    errors.append(
                        f"#{number}: closureInstruction missing required evidence `{fragment}`"
                    )
        else:
            if entry.execution_status not in CLOSED_STATUSES:
                errors.append(f"#{number}: closed issue has invalid executionStatus")
            if not entry.allow_pull_request_auto_close:
                errors.append(f"#{number}: closed issue must allow historical PR auto-close")
            if f"Closed #{number}" not in entry.closure_instruction:
                errors.append(
                    f"#{number}: closed issue closureInstruction must contain Closed #{number}"
                )
            for fragment in gate_policy.required_closed_issue_evidence.get(number, ()):
                if fragment not in entry.closure_instruction:
                    errors.append(
                        f"#{number}: closureInstruction missing required closed evidence `{fragment}`"
                    )

    missing = sorted(gate_policy.expected_issue_numbers - seen)
    extra = sorted(seen - gate_policy.expected_issue_numbers)
    if missing:
        errors.append(
            f"Missing RFC-0002 execution issue entries: {', '.join(f'#{n}' for n in missing)}"
        )
    if extra:
        errors.append(
            f"Unexpected RFC-0002 execution issue entries: {', '.join(f'#{n}' for n in extra)}"
        )
    return errors


if __name__ == "__main__":
    validation_errors = validate_github_issue_execution_ledger()
    print("\n".join(validation_errors or ["RFC-0002 GitHub issue execution ledger gate passed"]))
    sys.exit(bool(validation_errors))
