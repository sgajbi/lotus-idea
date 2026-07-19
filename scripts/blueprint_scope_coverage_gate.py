# ruff: noqa: E402
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.blueprint_scope_coverage import (
    BLUEPRINT_COVERAGE_CONTRACT_PATH,
    BLUEPRINT_PATH,
    blueprint_scope_coverage_errors,
)

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    try:
        blueprint = (ROOT / BLUEPRINT_PATH).read_text(encoding="utf-8")
        contract = _load_json_object(ROOT / BLUEPRINT_COVERAGE_CONTRACT_PATH)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"blueprint scope coverage error: {exc}", file=sys.stderr)
        return 2
    errors = blueprint_scope_coverage_errors(
        blueprint_markdown=blueprint,
        contract=contract,
    )
    if errors:
        print("\n".join(errors))
        return 1
    print("Blueprint scope coverage gate passed")
    return 0


def _load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return payload


if __name__ == "__main__":
    sys.exit(main())
