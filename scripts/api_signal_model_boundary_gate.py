from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SHARED_SIGNAL_MODELS = frozenset(
    {
        "IdeaCandidateSummaryResponse",
        "ReviewAccessScopeRequest",
        "SourceRefRequest",
        "SourceRefResponse",
    }
)


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _imported_names(node: ast.ImportFrom) -> set[str]:
    return {alias.asname or alias.name for alias in node.names}


def validate_api_signal_model_boundary(root: Path = ROOT) -> list[str]:
    api_dir = root / "src" / "app" / "api"
    errors: list[str] = []
    for path in sorted(api_dir.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.module != "app.api.idea_signals":
                continue
            imported_shared_models = sorted(_imported_names(node) & SHARED_SIGNAL_MODELS)
            if not imported_shared_models:
                continue
            names = ", ".join(imported_shared_models)
            errors.append(
                f"{_relative(path, root)}:{node.lineno}: shared signal API DTOs ({names}) "
                "must be imported from `app.api.signal_models`, not from the `idea_signals` "
                "route module"
            )
    return errors


def main() -> int:
    errors = validate_api_signal_model_boundary()
    if errors:
        print("API signal model boundary gate failed:")
        print("\n".join(errors))
        return 1
    print("API signal model boundary gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
