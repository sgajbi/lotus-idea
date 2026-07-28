# ruff: noqa: E402
from __future__ import annotations

import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.downstream_outcome_certification import (  # noqa: E402
    DOWNSTREAM_OUTCOME_CERTIFICATION_ENV,
    validate_downstream_outcome_certification_contract,
)

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    artifact_path = Path(args[0]) if args else _optional_artifact_path_from_environment()
    errors = validate_downstream_outcome_certification_contract(
        repository_root=ROOT,
        artifact_path=artifact_path,
    )
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    return 0


def _optional_artifact_path_from_environment() -> Path | None:
    configured = os.getenv(DOWNSTREAM_OUTCOME_CERTIFICATION_ENV)
    return Path(configured) if configured else None


if __name__ == "__main__":
    sys.exit(main())
