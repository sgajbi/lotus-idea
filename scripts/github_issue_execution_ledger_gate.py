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

EXPECTED_SCHEMA_VERSION = "lotus-idea:rfc0002-github-issue-execution-ledger:v1"
EXPECTED_RFC_ID = "RFC-0002"
EXPECTED_REPOSITORY = "sgajbi/lotus-idea"
EXPECTED_EXECUTION_ISSUES = frozenset(
    {
        340,
        343,
        344,
        345,
        375,
        379,
        380,
        482,
        542,
        673,
        674,
        675,
        676,
        677,
        678,
        679,
        680,
        681,
        682,
        683,
        684,
        685,
        686,
        687,
        688,
        689,
        690,
        691,
        692,
        693,
        694,
        695,
        696,
        697,
        698,
        699,
        700,
        701,
        702,
        704,
        756,
        782,
    }
)
OPEN_STATUSES = frozenset(
    {
        "open_tracker",
        "open_ready",
        "open_blocked",
        "open_in_progress",
        "open_fixed_local",
        "open_pr_raised",
        "open_merged_main_qa_pending",
        "open_pending_final_closure",
        "open_pending_post_completion",
    }
)
CLOSED_STATUSES = frozenset({"closed_complete"})
AUTO_CLOSE_KEYWORDS = (
    "close",
    "closes",
    "closed",
    "fix",
    "fixes",
    "fixed",
    "resolve",
    "resolves",
    "resolved",
)
REQUIRED_OPEN_ISSUE_EVIDENCE = {
    343: (
        "Keep #343 open and status/blocked",
        "versioned DR contract",
        "logical backup/restore drill workflow",
        "managed-provider PITR/failover certification",
        "2026-07-29",
        "This issue is not QA-pending",
        "continuous WAL/PITR health",
        "Do not claim production DR",
    ),
    344: (
        "Keep #344 open and status/blocked",
        "versioned lifecycle contract",
        "signed Archive lifecycle posture consumer",
        "scheduled lifecycle review workflow",
        "This issue is not QA-pending",
        "live bank producer/key-discovery proof",
        "provider-native AI deletion conformance",
        "Do not claim legal retention approval",
    ),
    375: (
        "Keep #375 open and status/blocked",
        "exact-image deployment migration contract",
        "protected workflow",
        "2026-07-29 live GitHub configuration recheck",
        "total_count=0",
        "Deployment Migration Evidence workflow has no runs",
        "This issue is not QA-pending",
        "Do not claim production migration certification",
    ),
    379: (
        "Keep #379 open and status/blocked",
        "sgajbi/lotus-advise#461",
        "sgajbi/lotus-manage#621",
        "sgajbi/lotus-report#152",
        "consumes sgajbi/lotus-manage#620 Manage temporal receipt identity",
        "closed v3 Manage mandate runtime proof contract",
        "sgajbi/lotus-manage#624",
        "sgajbi/lotus-report#136",
        "sgajbi/lotus-archive#55",
        "production/certification evidence",
    ),
    380: (
        "PR #746 corrected stale ready posture",
        "open_blocked",
        "6f8875dc6784dd17975e6700c09b9ff71d66fb8b",
        "30327202465",
        "30327193673",
    ),
    681: (
        "PR #765 merged the Slice 18 cross-repo issue posture command",
        "3ab78c4e9ba23b08eec5396f0641acf21c98f74a",
        "30411606383",
        "lotus-idea.wiki commit 0aea688",
        "PR #767 rendered pending final-closure and post-completion issue sections",
        "PR #768 added keep-open PR text enforcement",
        "PR #769 synchronized Manage temporal receipt identity consumption",
        "PR #770 reconciled historical Manage #620 closure truth",
        "c4a58683a05cb0c78bea5848a287abda682aea8f",
        "30418344813",
        "30418340512",
        "PR #776 synchronized #690 final QA closure truth",
        "aa492aedd46f30b854c8478edb919605dbdd58fc",
        "30432065538",
        "30432058627",
        "lotus-idea.wiki commit c08509a",
        "PR #777 synchronized #681 evidence after #690 QA closure",
        "39d51c5cb63df360f1e97e6e9e862784a9ad9178",
        "30434057675",
        "30434051218",
        "lotus-idea.wiki commit d0a1fa1",
        "rfc0002-issue681-pr776-evidence-sync",
        "PR #779 hardened operations blocker truth",
        "655d1245e96b7a67dea6c5d9ff0c78d0a32ee9e6",
        "30437706105",
        "30437690255",
        "lotus-idea.wiki commit b3359fa",
        "rfc0002-slice15-operations-blocker-truth",
        "Current Idea ledger posture after PR #779 remains 41 tracked issues, 24 open, and 17 closed",
        "strict DiffCount 0",
        "coordination and documentation truth only",
        "does not clear RFC-0002 blockers",
    ),
    691: (
        "Keep #691 open and status/blocked",
        "PR #725 merged to main",
        "29972535964",
        "rendered_output_creation_missing",
        "archive_record_creation_missing",
        "lotus-archive #55",
        "This issue is not QA-pending",
    ),
    692: (
        "Keep #692 open and status/blocked",
        "Platform PR #630 merged bounded mesh-readiness proof consumption",
        "c0fb028a440a24622fe162e934c3469fcafb4055",
        "30335871870",
        "30335876432",
        "clears only the catalog/policy/telemetry-consumable dependency marker",
        "This issue is not QA-pending",
    ),
    685: (
        "Keep #685 open and status/blocked",
        "sgajbi/lotus-core#840",
        "valuation and aggregation jobs drained to zero",
        "DPM_CORE_CONTEXT_INCOMPLETE",
        "POST http://manage.dev.lotus/api/v1/rebalance/simulate",
    ),
    686: (
        "Keep #686 open and status/blocked",
        "Workbench PR #501 merged the browser-action proof path",
        "sgajbi/lotus-core#840",
        "This issue is not QA-pending",
    ),
    345: (
        "Platform PR #629 merged bounded cost-attribution",
        "823e2641778aaf7db4e1df6218cf84eab0084526",
        "sgajbi/lotus-platform#495",
        "capacity-production-like environment",
        "No supported-feature, production capacity, billing, scaling, or production certification claim is made.",
    ),
    693: (
        "Platform PR #629 merged bounded cost-attribution",
        "823e2641778aaf7db4e1df6218cf84eab0084526",
        "platform issue #495 remains the protected FinOps execution",
        "does not provision self-hosted runners",
    ),
    699: (
        "Keep #699 open and status/blocked",
        "PR #740 merged to main",
        "30319531736",
        "This records the Slice 17 proof-control tranche only",
        "sgajbi/lotus-ai#122 / PR #123",
        "937501833b4c2a9d3031a108368ca113204b5db9",
        "30402022877",
        "deterministic local-dev idea_explanation.pack@v1 proof-contract execution",
        "approved non-stub live-provider execution",
        "This issue is not QA-pending",
        "full live journey validation remains blocked",
    ),
    782: (
        "Keep #782 open and status/in-progress",
        "aiWorkflowPackRuntimeExecutionProofValid=true",
        "generatedAtUtc was 2026-06-21T10:10:00+00:00",
        "runtimeReceipt.completed_at_utc was 2026-07-29T09:48:05.014851Z",
        "lotus_ai_runtime_execution_missing",
        "Do not claim live-provider execution",
    ),
}
REQUIRED_CLOSED_ISSUE_EVIDENCE = {
    340: (
        "QA closed #340",
        "3ee62ed5947a0491362f5d080fd1c7deb5ff3567",
        "30383665975",
        "30383650543",
        "154 passed",
        "51 passed",
        "sgajbi/lotus-ai#113",
    ),
    690: (
        "Closed #690 after QA passed",
        "5f53c4ac6ac519c7e6b0019e00f5286109e1628c",
        "30428715937",
        "30428711385",
        "800f682c4f7ae20a2c0634eb112323d7936cca73",
        "30430120214",
        "30430108647",
        "lotus-idea.wiki commit 3ebd0f0",
        "PR #776 then synchronized the closed-complete execution state",
        "aa492aedd46f30b854c8478edb919605dbdd58fc",
        "30432065538",
        "30432058627",
        "lotus-idea.wiki commit c08509a",
        "make report-intake-runtime-execution-proof-gate",
        "make implementation-proof-readiness-check",
        "clears only lotus_report_live_intake_route_proof_missing",
    ),
}


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
    return re.compile(rf"\b(?:{keywords})\s+#{issue_number}\b", re.IGNORECASE)


def validate_github_issue_execution_ledger(path: Path = LEDGER_PATH) -> list[str]:
    try:
        payload = _load_json(path)
        entries = _entries(payload)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        return [str(exc)]

    errors: list[str] = []
    if payload.get("schemaVersion") != EXPECTED_SCHEMA_VERSION:
        errors.append("schemaVersion must be lotus-idea:rfc0002-github-issue-execution-ledger:v1")
    if payload.get("rfcId") != EXPECTED_RFC_ID:
        errors.append("rfcId must be RFC-0002")
    if payload.get("repository") != EXPECTED_REPOSITORY:
        errors.append("repository must be sgajbi/lotus-idea")

    seen: set[int] = set()
    for entry in entries:
        number = entry.issue_number
        if number in seen:
            errors.append(f"#{number}: duplicate issue entry")
        seen.add(number)
        if number not in EXPECTED_EXECUTION_ISSUES:
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
            for fragment in REQUIRED_OPEN_ISSUE_EVIDENCE.get(number, ()):
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
            for fragment in REQUIRED_CLOSED_ISSUE_EVIDENCE.get(number, ()):
                if fragment not in entry.closure_instruction:
                    errors.append(
                        f"#{number}: closureInstruction missing required closed evidence `{fragment}`"
                    )

    missing = sorted(EXPECTED_EXECUTION_ISSUES - seen)
    extra = sorted(seen - EXPECTED_EXECUTION_ISSUES)
    if missing:
        errors.append(
            f"Missing RFC-0002 execution issue entries: {', '.join(f'#{n}' for n in missing)}"
        )
    if extra:
        errors.append(
            f"Unexpected RFC-0002 execution issue entries: {', '.join(f'#{n}' for n in extra)}"
        )
    return errors


def main() -> int:
    errors = validate_github_issue_execution_ledger()
    if errors:
        print("\n".join(errors))
        return 1
    print("RFC-0002 GitHub issue execution ledger gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
