# ruff: noqa: E402
from __future__ import annotations

from datetime import UTC, datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.opportunity_archetype_evidence_pack import (
    build_canonical_opportunity_archetype_evidence_pack,
    validate_opportunity_archetype_evidence_pack_payload,
)


def validate_opportunity_archetype_evidence_pack_contract() -> list[str]:
    generated_at_utc = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)
    payload = build_canonical_opportunity_archetype_evidence_pack(
        generated_at_utc=generated_at_utc,
        repository_root=Path.cwd(),
    )
    errors = validate_opportunity_archetype_evidence_pack_payload(
        payload,
        repository_root=Path.cwd(),
    )
    if "PB_SG_GLOBAL_BAL_001" in str(payload):
        errors.append("canonical opportunity archetype evidence pack leaked raw portfolio id")
    overclaimed = dict(payload)
    overclaimed["claimBoundary"] = dict(payload["claimBoundary"])
    overclaimed["claimBoundary"]["demoReady"] = True
    if not validate_opportunity_archetype_evidence_pack_payload(
        overclaimed,
        repository_root=Path.cwd(),
    ):
        errors.append("canonical opportunity archetype evidence pack accepted demo overclaim")
    return errors


def main() -> int:
    errors = validate_opportunity_archetype_evidence_pack_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Opportunity archetype evidence pack contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
