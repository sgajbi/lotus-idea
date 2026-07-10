from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APPLICATION_MODULE = Path("src/app/application/review_queue.py")
PORT_MODULE = Path("src/app/ports/idea_repository.py")
POSTGRES_MODULE = Path("src/app/infrastructure/postgres_review_queue.py")
API_MODULE = Path("src/app/api/review_queues.py")
API_MODEL_MODULE = Path("src/app/api/review_queue_models.py")


def validate_review_queue_snapshot_contract(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    modules = {
        relative_path: _read_module(root, relative_path, errors)
        for relative_path in (
            APPLICATION_MODULE,
            PORT_MODULE,
            POSTGRES_MODULE,
            API_MODULE,
            API_MODEL_MODULE,
        )
    }
    if any(tree is None for tree in modules.values()):
        return sorted(errors)

    _require_function_arguments(
        modules[PORT_MODULE],
        PORT_MODULE,
        "review_queue_candidate_page",
        {"evaluated_at_utc", "expected_snapshot_token", "policy_version"},
        errors,
    )
    _require_function_arguments(
        modules[POSTGRES_MODULE],
        POSTGRES_MODULE,
        "load_review_queue_candidate_page",
        {"evaluated_at_utc", "expected_snapshot_token", "policy_version"},
        errors,
    )
    _require_function_arguments(
        modules[API_MODULE],
        API_MODULE,
        "get_advisor_review_queue",
        {"evaluated_at_utc", "snapshot_token"},
        errors,
    )
    _require_class_fields(
        modules[APPLICATION_MODULE],
        APPLICATION_MODULE,
        "BuildReviewQueueFromRepositoryCommand",
        {"evaluated_at_utc", "snapshot_token"},
        errors,
    )
    _require_class_fields(
        modules[API_MODEL_MODULE],
        API_MODEL_MODULE,
        "ReviewQueuePageResponse",
        {"snapshot_token"},
        errors,
    )

    application_source = (root / APPLICATION_MODULE).read_text(encoding="utf-8")
    postgres_source = (root / POSTGRES_MODULE).read_text(encoding="utf-8")
    api_source = (root / API_MODULE).read_text(encoding="utf-8")
    required_fragments = {
        APPLICATION_MODULE: (
            "ReviewQueueSnapshotTokenRequiredError",
            "require_matching_review_queue_snapshot",
            "visible_review_queue_candidate_records",
        ),
        POSTGRES_MODULE: (
            "(candidate_json->>'created_at_utc')::timestamptz <= %s",
            "snapshot_fingerprint",
            "verification_identity.token != snapshot_identity.token",
        ),
        API_MODULE: (
            "review_queue_snapshot_token_required",
            "invalid_review_queue_snapshot_token",
            "review_queue_snapshot_conflict",
        ),
    }
    sources = {
        APPLICATION_MODULE: application_source,
        POSTGRES_MODULE: postgres_source,
        API_MODULE: api_source,
    }
    for relative_path, fragments in required_fragments.items():
        for fragment in fragments:
            if fragment not in sources[relative_path]:
                errors.append(
                    f"{relative_path.as_posix()}: required snapshot contract `{fragment}` is missing"
                )
    return sorted(errors)


def _read_module(root: Path, relative_path: Path, errors: list[str]) -> ast.Module | None:
    path = root / relative_path
    if not path.is_file():
        errors.append(f"{relative_path.as_posix()}: module is missing")
        return None
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _require_function_arguments(
    tree: ast.Module | None,
    relative_path: Path,
    function_name: str,
    required: set[str],
    errors: list[str],
) -> None:
    if tree is None:
        return
    function = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == function_name
        ),
        None,
    )
    if function is None:
        errors.append(f"{relative_path.as_posix()}: `{function_name}` is missing")
        return
    arguments = {
        argument.arg
        for argument in (
            *function.args.posonlyargs,
            *function.args.args,
            *function.args.kwonlyargs,
        )
    }
    for field_name in sorted(required - arguments):
        errors.append(f"{relative_path.as_posix()}: `{function_name}` must accept `{field_name}`")


def _require_class_fields(
    tree: ast.Module | None,
    relative_path: Path,
    class_name: str,
    required: set[str],
    errors: list[str],
) -> None:
    if tree is None:
        return
    class_node = next(
        (node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name),
        None,
    )
    if class_node is None:
        errors.append(f"{relative_path.as_posix()}: `{class_name}` is missing")
        return
    fields = {
        node.target.id
        for node in class_node.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    }
    for field_name in sorted(required - fields):
        errors.append(f"{relative_path.as_posix()}: `{class_name}` must define `{field_name}`")


def main() -> int:
    errors = validate_review_queue_snapshot_contract()
    if errors:
        print("Review queue snapshot contract gate failed:")
        print("\n".join(errors))
        return 1
    print("Review queue snapshot contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
