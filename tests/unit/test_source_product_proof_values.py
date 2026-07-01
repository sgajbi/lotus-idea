from __future__ import annotations

from app.application.source_product_proof_values import text_sequence


def test_text_sequence_uses_default_for_missing_payload_value() -> None:
    assert text_sequence(None, default=("risk_profile_missing",)) == ("risk_profile_missing",)


def test_text_sequence_normalizes_list_and_tuple_items_to_text() -> None:
    assert text_sequence(["risk_profile_missing", 123]) == ("risk_profile_missing", "123")
    assert text_sequence(("mandate_restriction_review_required",)) == (
        "mandate_restriction_review_required",
    )


def test_text_sequence_rejects_scalar_payload_values() -> None:
    assert text_sequence("risk_profile_missing") == ()
    assert text_sequence({"code": "risk_profile_missing"}) == ()
