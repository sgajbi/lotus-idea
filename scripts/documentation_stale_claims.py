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
