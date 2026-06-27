from __future__ import annotations

from pathlib import Path

from app.application.source_safe_cross_repo_proof import (
    required_make_target_evidence_present,
    text_file_contains_all,
)


def test_required_make_target_evidence_fails_when_makefile_is_missing(tmp_path: Path) -> None:
    assert (
        required_make_target_evidence_present(
            repository_root=tmp_path,
            evidence_refs=("make opportunity-archetype-contract-gate",),
        )
        is False
    )


def test_required_make_target_evidence_fails_when_target_is_missing(tmp_path: Path) -> None:
    (tmp_path / "Makefile").write_text("lint:\n\tpython -m ruff check .\n", encoding="utf-8")

    assert (
        required_make_target_evidence_present(
            repository_root=tmp_path,
            evidence_refs=("make opportunity-archetype-contract-gate",),
        )
        is False
    )


def test_text_file_contains_all_fails_when_file_is_missing(tmp_path: Path) -> None:
    assert text_file_contains_all(tmp_path / "missing.md", ("required fragment",)) is False
