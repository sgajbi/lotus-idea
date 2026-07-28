# ruff: noqa: E402
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.full_live_opportunity_journey_proof import (
    FULL_LIVE_OPPORTUNITY_JOURNEY_PROOF_ENV,
    REQUIRED_FULL_LIVE_JOURNEY_LOCAL_REFS,
    validate_full_live_opportunity_journey_proof,
)
from app.application.source_safe_cross_repo_proof import (
    required_file_evidence_present,
    required_make_target_evidence_present,
)


ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    artifact_path = Path(args[0]) if args else None
    errors = validate_full_live_opportunity_journey_contract(artifact_path=artifact_path)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    return 0


def validate_full_live_opportunity_journey_contract(
    *,
    repository_root: Path = ROOT,
    artifact_path: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    if not required_file_evidence_present(
        repository_root=repository_root,
        sibling_roots={},
        evidence_refs=REQUIRED_FULL_LIVE_JOURNEY_LOCAL_REFS,
        non_file_ref_prefixes=("make ",),
    ):
        errors.append("full-live journey localEvidenceRefs must point to repository evidence")
    if not required_make_target_evidence_present(
        repository_root=repository_root,
        evidence_refs=REQUIRED_FULL_LIVE_JOURNEY_LOCAL_REFS,
    ):
        errors.append("full-live journey localEvidenceRefs must include an implemented Make target")
    candidate_path = artifact_path or _optional_artifact_path_from_environment()
    if candidate_path is not None:
        errors.extend(validate_full_live_opportunity_journey_file(candidate_path))
    return errors


def validate_full_live_opportunity_journey_file(path: Path) -> list[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{path} could not be read as a JSON proof artifact: {exc}"]
    if not isinstance(payload, dict):
        return [f"{path} must contain a JSON object"]
    return validate_full_live_opportunity_journey_proof(cast(dict[str, Any], payload))


def _optional_artifact_path_from_environment() -> Path | None:
    configured = os.getenv(FULL_LIVE_OPPORTUNITY_JOURNEY_PROOF_ENV)
    return Path(configured) if configured else None


if __name__ == "__main__":
    sys.exit(main())
