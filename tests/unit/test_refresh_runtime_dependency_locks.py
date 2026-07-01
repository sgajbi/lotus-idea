from __future__ import annotations

from pathlib import Path

from scripts.refresh_runtime_dependency_locks import (
    runtime_lock_lines_from_closure,
    validate_runtime_lock_text,
    write_runtime_dependency_locks,
)


def test_runtime_lock_lines_are_sorted_and_exactly_pinned() -> None:
    lines = runtime_lock_lines_from_closure(
        {
            "uvicorn": "0.49.0",
            "fastapi": "0.138.0",
            "pydantic-core": "2.46.4",
        }
    )

    assert lines == [
        "fastapi==0.138.0",
        "pydantic-core==2.46.4",
        "uvicorn==0.49.0",
    ]


def test_validate_runtime_lock_text_accepts_matching_runtime_and_graph_mirror(
    tmp_path: Path,
) -> None:
    runtime_lock = tmp_path / "runtime-resolved.lock.txt"
    dependency_graph = tmp_path / "requirements.txt"
    write_runtime_dependency_locks(
        ["fastapi==0.138.0", "uvicorn==0.49.0"],
        runtime_lock,
        dependency_graph,
    )

    assert (
        validate_runtime_lock_text(
            ["fastapi==0.138.0", "uvicorn==0.49.0"],
            runtime_lock,
            dependency_graph,
        )
        == []
    )


def test_validate_runtime_lock_text_reports_stale_runtime_lock(tmp_path: Path) -> None:
    runtime_lock = tmp_path / "runtime-resolved.lock.txt"
    dependency_graph = tmp_path / "requirements.txt"
    write_runtime_dependency_locks(
        ["fastapi==0.138.0", "uvicorn==0.49.0"],
        runtime_lock,
        dependency_graph,
    )

    errors = validate_runtime_lock_text(
        ["fastapi==0.138.2", "uvicorn==0.49.0"],
        runtime_lock,
        dependency_graph,
    )

    assert (
        "requirements/runtime-resolved.lock.txt is stale; run `make dependency-refresh`" in errors
    )


def test_validate_runtime_lock_text_reports_dependency_graph_mirror_drift(
    tmp_path: Path,
) -> None:
    runtime_lock = tmp_path / "runtime-resolved.lock.txt"
    dependency_graph = tmp_path / "requirements.txt"
    runtime_lock.write_text("fastapi==0.138.0\n", encoding="utf-8")
    dependency_graph.write_text("fastapi==0.138.2\n", encoding="utf-8")

    errors = validate_runtime_lock_text(["fastapi==0.138.0"], runtime_lock, dependency_graph)

    assert "requirements/requirements.txt is stale; run `make dependency-refresh`" in errors
    assert (
        "requirements/requirements.txt must mirror requirements/runtime-resolved.lock.txt" in errors
    )
