from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PROOF_READINESS_HEADINGS = (
    "## What It Proves",
    "## What It Does Not Prove",
    "## Current Blockers",
    "## Response Shape",
    "## Evidence",
    "## Example",
)

PROHIBITED_STALE_CLAIMS = (
    (
        "docs/operations/api-certification.md",
        (
            "Core publishes explicit maturity summary facts",
            "Core holdings maturity evidence",
        ),
        "bond-maturity API certification must describe current PortfolioMaturitySummary:v1 consumption, not the superseded Core #686 blocker",
    ),
)

RFC0002_POSTURE_SNAPSHOT_SURFACES = (
    "REPOSITORY-ENGINEERING-CONTEXT.md",
    "docs/rfcs/README.md",
    "docs/operations/implementation-proof-readiness.md",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
    "RFC-0002-slice-18-documentation-wiki-support-and-agent-context.md",
    "wiki/Home.md",
    "wiki/RFC-Index.md",
    "wiki/RFC-0002-Execution-Status.md",
    "wiki/Supported-Features.md",
    "wiki/Validation-and-CI.md",
)
RFC0002_POSTURE_CONTRACT_PATH = (
    "contracts/implementation-proof/rfc0002-issue-posture-snapshot.v1.json"
)
EXPECTED_RFC0002_POSTURE_CONTRACT_SCHEMA = "lotus-idea:rfc0002-issue-posture-snapshot:v1"
SUPERSEDED_RFC0002_POSTURE_SNAPSHOTS = (
    "77 tracked RFC-0002 issues",
    "80 tracked issues",
    "93 label-backed",
)
CURRENT_POSTURE_MARKERS = (
    "Current governed",
    "current governed",
    "Current live",
    "current live",
    "Current source truth",
    "current source truth",
    "Live governed",
    "live cross-repo",
    "governed posture remains",
    "governed posture stays",
    "This keeps the governed posture",
)
HISTORICAL_POSTURE_MARKERS = (
    "then-current",
    "Then-current",
    "At that point",
    "At that snapshot",
    "historical",
    "Historical",
    "earlier",
    "Earlier",
)
LOCAL_POSTURE_MARKERS = (
    "Idea ledger",
    "Idea-local",
    "tracked Idea RFC-0002 issues",
    "tracked RFC-0002 issues",
)
CROSS_REPO_POSTURE_MARKERS = (
    "cross-repo",
    "cross-repository",
    "label-backed RFC-0002 issues",
    "GitHub issue posture",
    "governed posture",
)


def _load_rfc0002_posture_contract(*, root: Path) -> dict:
    contract_path = root / RFC0002_POSTURE_CONTRACT_PATH
    if not contract_path.exists():
        contract_path = ROOT / RFC0002_POSTURE_CONTRACT_PATH
    payload = json.loads(contract_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{RFC0002_POSTURE_CONTRACT_PATH} must contain a JSON object")
    if payload.get("schemaVersion") != EXPECTED_RFC0002_POSTURE_CONTRACT_SCHEMA:
        raise ValueError(
            f"{RFC0002_POSTURE_CONTRACT_PATH}: schemaVersion must be "
            f"{EXPECTED_RFC0002_POSTURE_CONTRACT_SCHEMA}"
        )
    return payload


def _expected_fragments(contract: dict, family: str) -> tuple[str, ...]:
    expected = contract.get("expectedCurrentFragments", {})
    if not isinstance(expected, dict):
        raise ValueError(
            f"{RFC0002_POSTURE_CONTRACT_PATH}: expectedCurrentFragments must be an object"
        )
    fragments = expected.get(family)
    if not isinstance(fragments, list) or not fragments:
        raise ValueError(
            f"{RFC0002_POSTURE_CONTRACT_PATH}: expectedCurrentFragments.{family} "
            "must be a non-empty list"
        )
    if not all(isinstance(fragment, str) and fragment for fragment in fragments):
        raise ValueError(
            f"{RFC0002_POSTURE_CONTRACT_PATH}: expectedCurrentFragments.{family} "
            "must contain non-empty strings"
        )
    return tuple(fragments)


def _normalize_prose(text: str) -> str:
    return " ".join(text.split())


def _is_current_posture_paragraph(paragraph: str) -> bool:
    if not ("RFC-0002" in paragraph and "issue" in paragraph.lower()):
        return False
    if any(marker in paragraph for marker in HISTORICAL_POSTURE_MARKERS):
        return False
    return (
        any(marker in paragraph for marker in CURRENT_POSTURE_MARKERS)
        or "GitHub issue posture" in paragraph
        or "Current summary" in paragraph
        or "Current support summary" in paragraph
    )


def _posture_families(paragraph: str) -> tuple[str, ...]:
    families: list[str] = []
    if any(marker in paragraph for marker in LOCAL_POSTURE_MARKERS):
        families.append("ideaLedger")
    if any(marker in paragraph for marker in CROSS_REPO_POSTURE_MARKERS):
        families.append("crossRepo")
    return tuple(families)


def rfc0002_issue_posture_snapshot_errors(*, root) -> list[str]:
    errors: list[str] = []
    root = Path(root)
    try:
        contract = _load_rfc0002_posture_contract(root=root)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [str(exc)]

    for relative_path in RFC0002_POSTURE_SNAPSHOT_SURFACES:
        path = root / relative_path
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        for paragraph_number, paragraph in enumerate(content.split("\n\n"), start=1):
            if not any(snapshot in paragraph for snapshot in SUPERSEDED_RFC0002_POSTURE_SNAPSHOTS):
                if not _is_current_posture_paragraph(paragraph):
                    continue
                for family in _posture_families(paragraph):
                    normalized_paragraph = _normalize_prose(paragraph)
                    missing_fragments = [
                        fragment
                        for fragment in _expected_fragments(contract, family)
                        if _normalize_prose(fragment) not in normalized_paragraph
                    ]
                    if missing_fragments:
                        errors.append(
                            f"{relative_path}: paragraph {paragraph_number} describes current/live "
                            "RFC-0002 issue posture without contract-backed "
                            f"{family} fragment(s): "
                            f"{', '.join(f'`{fragment}`' for fragment in missing_fragments)}"
                        )
                continue
            if any(marker in paragraph for marker in HISTORICAL_POSTURE_MARKERS):
                continue
            if any(marker in paragraph for marker in CURRENT_POSTURE_MARKERS):
                errors.append(
                    f"{relative_path}: paragraph {paragraph_number} describes a superseded "
                    "RFC-0002 issue-count snapshot as current/live posture; use `then-current` "
                    "or update the count from `make rfc0002-cross-repo-issue-posture`"
                )
    return errors
