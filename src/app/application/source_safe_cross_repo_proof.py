from __future__ import annotations

from pathlib import Path

from app.domain.proof_evidence import (
    is_timezone_aware_datetime_text as is_timezone_aware_datetime_text,
)


def required_file_evidence_present(
    *,
    repository_root: Path,
    sibling_roots: dict[str, Path],
    evidence_refs: tuple[str, ...],
    non_file_ref_prefixes: tuple[str, ...],
) -> bool:
    for ref in evidence_refs:
        if ref.startswith(non_file_ref_prefixes):
            continue
        evidence_path = _evidence_path(
            repository_root=repository_root,
            sibling_roots=sibling_roots,
            ref=ref,
        )
        if not evidence_path.is_file():
            return False
    return True


def required_make_target_evidence_present(
    *,
    repository_root: Path,
    evidence_refs: tuple[str, ...],
) -> bool:
    try:
        makefile_text = (repository_root / "Makefile").read_text(encoding="utf-8")
    except OSError:
        return False
    for ref in evidence_refs:
        if not ref.startswith("make "):
            continue
        target = f"{ref.removeprefix('make ')}:"
        if target not in makefile_text:
            return False
    return True


def text_file_contains_all(path: Path, fragments: tuple[str, ...]) -> bool:
    text = read_text(path)
    return bool(text) and all(fragment in text for fragment in fragments)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _evidence_path(
    *,
    repository_root: Path,
    sibling_roots: dict[str, Path],
    ref: str,
) -> Path:
    for prefix, root in sibling_roots.items():
        if ref.startswith(prefix):
            return root / ref.removeprefix(prefix)
    return repository_root / ref
