from __future__ import annotations

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
    "docs/operations/implementation-proof-readiness.md",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
    "RFC-0002-slice-18-documentation-wiki-support-and-agent-context.md",
    "wiki/Validation-and-CI.md",
)
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
    "At that point",
    "At that snapshot",
    "historical",
    "Historical",
    "earlier",
    "Earlier",
)


def rfc0002_issue_posture_snapshot_errors(*, root) -> list[str]:
    errors: list[str] = []
    for relative_path in RFC0002_POSTURE_SNAPSHOT_SURFACES:
        path = root / relative_path
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        for paragraph_number, paragraph in enumerate(content.split("\n\n"), start=1):
            if not any(snapshot in paragraph for snapshot in SUPERSEDED_RFC0002_POSTURE_SNAPSHOTS):
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
