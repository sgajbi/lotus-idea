from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


APP_PACKAGE_NAME = "app"
IMPORT_GUARD_ERROR_CODE = "proof_import_worktree_mismatch"


def ensure_worktree_imports(
    entrypoint_file: str | Path,
    *,
    package_name: str = APP_PACKAGE_NAME,
) -> Path:
    """Pin proof-generator imports to the worktree that owns the entrypoint.

    Proof artifacts bind Git provenance from one repository root. The Python
    modules used to build that artifact must resolve from the same root, even
    when a developer reuses a virtualenv editable install from a sibling
    worktree.
    """

    repository_root = _repository_root_for_entrypoint(Path(entrypoint_file))
    src_root = repository_root / "src"
    _promote_import_root(src_root)
    _promote_import_root(repository_root)
    _fail_if_package_already_loaded_from_other_worktree(
        package_name=package_name,
        repository_root=repository_root,
    )
    _validate_package_spec(package_name=package_name, repository_root=repository_root)
    return repository_root


def _repository_root_for_entrypoint(entrypoint_file: Path) -> Path:
    resolved_entrypoint = entrypoint_file.resolve()
    for candidate in (resolved_entrypoint.parent, *resolved_entrypoint.parents):
        if (candidate / "src" / APP_PACKAGE_NAME).is_dir() and (candidate / "scripts").is_dir():
            return candidate
    raise RuntimeError(
        f"{IMPORT_GUARD_ERROR_CODE}: could not locate repository root for {resolved_entrypoint}"
    )


def _promote_import_root(path: Path) -> None:
    resolved = str(path.resolve())
    sys.path[:] = [entry for entry in sys.path if _normalized(entry) != resolved]
    sys.path.insert(0, resolved)


def _fail_if_package_already_loaded_from_other_worktree(
    *,
    package_name: str,
    repository_root: Path,
) -> None:
    loaded = sys.modules.get(package_name)
    if loaded is None:
        return
    loaded_file = getattr(loaded, "__file__", None)
    if loaded_file is None:
        return
    _require_path_inside_worktree(
        path=Path(loaded_file),
        repository_root=repository_root,
        context=f"loaded package {package_name}",
    )


def _validate_package_spec(*, package_name: str, repository_root: Path) -> None:
    spec = importlib.util.find_spec(package_name)
    if spec is None:
        raise RuntimeError(
            f"{IMPORT_GUARD_ERROR_CODE}: package {package_name!r} is not importable "
            f"from {repository_root}"
        )
    origin = spec.origin
    if origin is None and spec.submodule_search_locations:
        origin = next(iter(spec.submodule_search_locations), None)
    if origin is None:
        raise RuntimeError(
            f"{IMPORT_GUARD_ERROR_CODE}: package {package_name!r} has no resolved origin"
        )
    _require_path_inside_worktree(
        path=Path(origin),
        repository_root=repository_root,
        context=f"resolved package {package_name}",
    )


def _require_path_inside_worktree(
    *,
    path: Path,
    repository_root: Path,
    context: str,
) -> None:
    resolved_path = path.resolve()
    resolved_root = repository_root.resolve()
    if not _is_relative_to(resolved_path, resolved_root):
        raise RuntimeError(
            f"{IMPORT_GUARD_ERROR_CODE}: {context} resolves to {resolved_path}, "
            f"outside proof worktree {resolved_root}"
        )


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _normalized(path: str) -> str:
    return str(Path(path or ".").resolve())
