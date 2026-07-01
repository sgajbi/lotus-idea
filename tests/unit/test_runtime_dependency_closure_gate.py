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
    lock_path.write_text(
        (ROOT / "requirements" / "shared-runtime.lock.txt").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    errors = validate_runtime_dependency_closure(lock_path=lock_path)

    assert (
        "runtime-resolved.lock.txt must include transitive runtime dependencies, "
        "not only direct pyproject dependencies"
    ) in errors
    assert "runtime-resolved.lock.txt missing runtime dependency `anyio`" in errors
