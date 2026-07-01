from __future__ import annotations

from pathlib import Path

from scripts.runtime_dependency_closure_gate import validate_runtime_dependency_closure


ROOT = Path(__file__).resolve().parents[2]


def test_runtime_dependency_closure_gate_passes_current_repository() -> None:
    assert validate_runtime_dependency_closure() == []


def test_runtime_dependency_closure_gate_blocks_direct_only_runtime_lock(
    tmp_path: Path,
) -> None:
    lock_path = tmp_path / "runtime-resolved.lock.txt"
    dependency_graph_path = tmp_path / "requirements.txt"
    direct_only_requirements = (ROOT / "requirements" / "shared-runtime.lock.txt").read_text(
        encoding="utf-8"
    )
    lock_path.write_text(
        direct_only_requirements,
        encoding="utf-8",
    )
    dependency_graph_path.write_text(
        direct_only_requirements,
        encoding="utf-8",
    )

    errors = validate_runtime_dependency_closure(
        lock_path=lock_path,
        dependency_graph_path=dependency_graph_path,
    )

    assert (
        "runtime-resolved.lock.txt must include transitive runtime dependencies, "
        "not only direct pyproject dependencies"
    ) in errors
    assert "runtime-resolved.lock.txt missing runtime dependency `anyio`" in errors


def test_runtime_dependency_closure_gate_blocks_dependency_graph_mirror_drift(
    tmp_path: Path,
) -> None:
    lock_path = ROOT / "requirements" / "runtime-resolved.lock.txt"
    dependency_graph_path = tmp_path / "requirements.txt"
    dependency_graph_path.write_text(
        lock_path.read_text(encoding="utf-8").replace("anyio==4.14.0", "anyio==4.14.1"),
        encoding="utf-8",
    )

    errors = validate_runtime_dependency_closure(
        lock_path=lock_path,
        dependency_graph_path=dependency_graph_path,
    )

    assert (
        "requirements/requirements.txt must mirror "
        "requirements/runtime-resolved.lock.txt for GitHub dependency graph support"
    ) in errors
