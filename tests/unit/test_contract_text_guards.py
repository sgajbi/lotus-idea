from __future__ import annotations

from scripts.contract_text_guards import validate_forbidden_contract_text


def test_validate_forbidden_contract_text_reports_nested_mapping_and_sequence_paths() -> None:
    errors: list[str] = []

    validate_forbidden_contract_text(
        {
            "safe": "declared contract only",
            "nested": [{"claim": "client-ready supported"}],
        },
        errors,
        ("client-ready supported",),
    )

    assert errors == ["$.nested[0].claim: forbidden contract text `client-ready supported`"]


def test_validate_forbidden_contract_text_ignores_non_string_values() -> None:
    errors: list[str] = []

    validate_forbidden_contract_text(
        {"count": 1, "nested": [False, None]},
        errors,
        ("client-ready supported",),
    )

    assert errors == []
