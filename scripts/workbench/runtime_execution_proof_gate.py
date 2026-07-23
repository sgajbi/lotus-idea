# ruff: noqa: E402
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.workbench.runtime_execution import (
    GATEWAY_WORKBENCH_RUNTIME_EXECUTION_ENV,
    REQUIRED_GATEWAY_WORKBENCH_RUNTIME_LOCAL_REFS,
    validate_gateway_workbench_runtime_execution_proof,
)
from app.application.source_safe_cross_repo_proof import (
    required_file_evidence_present,
    required_make_target_evidence_present,
)


ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    _ = argv
    errors = validate_gateway_workbench_runtime_execution_contract()
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    return 0


def validate_gateway_workbench_runtime_execution_contract(
    *,
    repository_root: Path = ROOT,
    artifact_path: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    if not required_file_evidence_present(
        repository_root=repository_root,
        sibling_roots={},
        evidence_refs=REQUIRED_GATEWAY_WORKBENCH_RUNTIME_LOCAL_REFS,
        non_file_ref_prefixes=("make ",),
    ):
        errors.append("runtime localEvidenceRefs must point to existing repository evidence")
    if not required_make_target_evidence_present(
        repository_root=repository_root,
        evidence_refs=REQUIRED_GATEWAY_WORKBENCH_RUNTIME_LOCAL_REFS,
    ):
        errors.append("runtime localEvidenceRefs must include an implemented Make target")
    candidate_path = artifact_path or _optional_artifact_path_from_environment()
    if candidate_path is not None:
        errors.extend(validate_gateway_workbench_runtime_execution_file(candidate_path))
    return errors


def validate_gateway_workbench_runtime_execution_file(path: Path) -> list[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{path} could not be read as a JSON proof artifact: {exc}"]
    if not isinstance(payload, dict):
        return [f"{path} must contain a JSON object"]
    return validate_gateway_workbench_runtime_execution_proof(cast(dict[str, Any], payload))


def _optional_artifact_path_from_environment() -> Path | None:
    configured = os.getenv(GATEWAY_WORKBENCH_RUNTIME_EXECUTION_ENV)
    return Path(configured) if configured else None


if __name__ == "__main__":
    sys.exit(main())
