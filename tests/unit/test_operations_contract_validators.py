from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.operations_contract_validators import (
    validate_operations_contract_payload,
    validate_required_labels,
    validate_required_operations,
)


def test_validate_operations_contract_payload_preserves_sorted_errors() -> None:
    def _header(_: dict[str, Any]) -> list[str]:
        return ["z header"]

    def _source(_: dict[str, Any], *, repository_root: Path) -> list[str]:
        assert repository_root == Path("repo")
        return ["a source"]

    assert validate_operations_contract_payload(
        {},
        repository_root=Path("repo"),
        validators=(
            _header,
            _source,
            lambda _: ["m dashboard"],
            lambda _: [],
            lambda _: ["b boundary"],
        ),
    ) == ["a source", "b boundary", "m dashboard", "z header"]


def test_validate_operations_contract_payload_supports_additional_sections() -> None:
    section_calls: list[str] = []

    def _header(_: dict[str, Any]) -> list[str]:
        return []

    def _source(_: dict[str, Any], *, repository_root: Path) -> list[str]:
        assert repository_root == Path("repo")
        return []

    def _section(_: dict[str, Any]) -> list[str]:
        section_calls.append("section")
        return []

    validate_operations_contract_payload(
        {},
        repository_root=Path("repo"),
        validators=(_header, _source, _section, _section, _section, _section),
    )

    assert section_calls == ["section"] * 4


def test_validate_required_operations_uses_code_owned_operation_ids() -> None:
    assert validate_required_operations("control", ["ai_explanation_readiness_read"]) == []
    assert validate_required_operations("control", []) == [
        "control: required_operations must be a non-empty list"
    ]
    assert validate_required_operations("control", ["local_operation"]) == [
        "control: required_operations contain unsupported operations: local_operation"
    ]


def test_validate_required_labels_rejects_unknown_and_sensitive_labels() -> None:
    assert validate_required_labels("control", ["operation", "outcome"]) == []
    assert validate_required_labels("control", []) == [
        "control: required_labels must be a non-empty list"
    ]
    assert validate_required_labels("control", ["portfolio_id"]) == [
        "control: required_labels contain unsupported labels: portfolio_id",
        "control: required_labels contain sensitive labels: portfolio_id",
    ]
