from __future__ import annotations

from pathlib import Path

from scripts.duplicate_implementation_inventory import (
    build_duplicate_inventory,
    validate_duplicate_inventory,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_duplicate_inventory_reports_known_forbidden_content_helper_cluster(
    tmp_path: Path,
) -> None:
    helper_body = """
def _validate_forbidden_content(value, errors, path="$"):
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key).lower()
            child_path = f"{path}.{key}"
            if key_text in FORBIDDEN_KEYS:
                errors.append(child_path)
            _validate_forbidden_content(child, errors, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_forbidden_content(child, errors, f"{path}[{index}]")
    elif isinstance(value, str):
        lowered = value.lower()
        for fragment in FORBIDDEN_TEXT_FRAGMENTS:
            if fragment in lowered:
                errors.append(path)
"""
    _write(tmp_path / "scripts" / "first_gate.py", helper_body)
    _write(tmp_path / "scripts" / "second_gate.py", helper_body)

    inventory = build_duplicate_inventory(tmp_path, min_function_lines=6)

    assert inventory["thresholdEnforced"] is False
    assert inventory["duplicateClusterCount"] == 1
    assert inventory["clusters"][0]["classification"] == (
        "known_proof_source_safety_content_validation"
    )
    assert inventory["clusters"][0]["count"] == 2


def test_duplicate_inventory_report_only_mode_does_not_fail_duplicates(tmp_path: Path) -> None:
    duplicate_body = """
def calculate(value):
    total = 0
    for item in value:
        total += item
    return total
"""
    _write(tmp_path / "src" / "app" / "first.py", duplicate_body)
    _write(tmp_path / "src" / "app" / "second.py", duplicate_body)

    assert validate_duplicate_inventory(tmp_path, min_function_lines=3) == []


def test_duplicate_inventory_ignores_non_implementation_protocol_stubs(
    tmp_path: Path,
) -> None:
    protocol_body = """
from typing import Protocol


class FirstPort(Protocol):
    def record_event(
        self,
        event_id: str,
        *,
        actor_subject: str,
        payload: dict[str, object],
    ) -> None: ...


class SecondPort(Protocol):
    def publish_event(
        self,
        event_id: str,
        *,
        actor_subject: str,
        payload: dict[str, object],
    ) -> None: ...
"""
    _write(tmp_path / "src" / "app" / "ports.py", protocol_body)

    inventory = build_duplicate_inventory(tmp_path, min_function_lines=6)

    assert inventory["duplicateClusterCount"] == 0
    assert inventory["functionCount"] == 0


def test_duplicate_inventory_explicit_fail_mode_reports_duplicate_clusters(
    tmp_path: Path,
) -> None:
    duplicate_body = """
def calculate(value):
    total = 0
    for item in value:
        total += item
    return total
"""
    _write(tmp_path / "src" / "app" / "first.py", duplicate_body)
    _write(tmp_path / "src" / "app" / "second.py", duplicate_body)

    errors = validate_duplicate_inventory(
        tmp_path,
        fail_on_duplicates=True,
        min_function_lines=3,
    )

    assert errors == [
        "duplicate implementation cluster unclassified_exact_function_body has 2 exact function bodies"
    ]


def test_duplicate_inventory_strict_mode_accepts_unique_functions(tmp_path: Path) -> None:
    _write(
        tmp_path / "src" / "app" / "first.py",
        """
def calculate(value):
    total = 0
    for item in value:
        total += item
    return total
""",
    )
    _write(
        tmp_path / "scripts" / "second.py",
        """
def calculate_differently(value):
    total = 1
    for item in value:
        total *= item
    return total
""",
    )

    assert (
        validate_duplicate_inventory(
            tmp_path,
            fail_on_duplicates=True,
            min_function_lines=3,
        )
        == []
    )
