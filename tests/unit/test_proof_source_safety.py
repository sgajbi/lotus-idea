from __future__ import annotations

from scripts.proof_source_safety import validate_forbidden_content


def test_validate_forbidden_content_reports_nested_forbidden_key_path() -> None:
    errors: list[str] = []

    validate_forbidden_content(
        {"proof": {"portfolioId": "redacted"}},
        errors,
        forbidden_keys={"portfolioId"},
        forbidden_text_fragments=set(),
    )

    assert errors == ["$.proof.portfolioId: forbidden source-sensitive key is present"]


def test_validate_forbidden_content_recurses_through_lists_and_tuples() -> None:
    errors: list[str] = []

    validate_forbidden_content(
        {"items": [{"safe": True}, ({"traceId": "redacted"},)]},
        errors,
        forbidden_keys={"traceId"},
        forbidden_text_fragments=set(),
    )

    assert errors == ["$.items[1][0].traceId: forbidden source-sensitive key is present"]


def test_validate_forbidden_content_reports_forbidden_text_fragment() -> None:
    errors: list[str] = []

    validate_forbidden_content(
        {"evidenceRef": "request-body-redacted"},
        errors,
        forbidden_keys=set(),
        forbidden_text_fragments={"request-body"},
    )

    assert errors == ["$.evidenceRef: forbidden source-sensitive text `request-body` is present"]


def test_validate_forbidden_content_allows_safe_payload() -> None:
    errors: list[str] = []

    validate_forbidden_content(
        {"proof": {"sourceAuthority": "lotus-core", "evidenceRefs": ["contract:path"]}},
        errors,
        forbidden_keys={"portfolioId"},
        forbidden_text_fragments={"PB_SG_GLOBAL_BAL_001"},
    )

    assert errors == []


def test_validate_forbidden_content_keeps_text_fragments_case_sensitive() -> None:
    errors: list[str] = []

    validate_forbidden_content(
        {"evidenceRef": "REQUEST-BODY-redacted"},
        errors,
        forbidden_keys=set(),
        forbidden_text_fragments={"request-body"},
    )

    assert errors == []
