from __future__ import annotations

from app.api.conversion_governance import _error_code_from_conversion_decision
from app.api.review_workflow import _error_code_from_review_decision
from app.api.telemetry_buckets import bounded_count_bucket
from app.domain.persistence import ConversionPersistenceDecision, ReviewPersistenceDecision


def test_review_api_error_mapping_is_bounded_and_source_safe() -> None:
    assert (
        _error_code_from_review_decision(ReviewPersistenceDecision.NOT_FOUND)
        == "candidate_not_found"
    )
    assert (
        _error_code_from_review_decision(ReviewPersistenceDecision.CONFLICT)
        == "idempotency_conflict"
    )
    assert _error_code_from_review_decision(ReviewPersistenceDecision.ACCEPTED) is None


def test_conversion_api_error_mapping_is_bounded_and_source_safe() -> None:
    assert (
        _error_code_from_conversion_decision(ConversionPersistenceDecision.NOT_FOUND)
        == "conversion_resource_not_found"
    )
    assert (
        _error_code_from_conversion_decision(ConversionPersistenceDecision.CONFLICT)
        == "idempotency_conflict"
    )
    assert _error_code_from_conversion_decision(ConversionPersistenceDecision.ACCEPTED) is None


def test_outbox_delivery_operation_count_buckets_are_bounded() -> None:
    assert bounded_count_bucket(0) == "0"
    assert bounded_count_bucket(1) == "1-10"
    assert bounded_count_bucket(10) == "1-10"
    assert bounded_count_bucket(11) == "11-100"
    assert bounded_count_bucket(100) == "11-100"
    assert bounded_count_bucket(101) == "100+"


def test_runtime_trust_count_bucket_preserves_legacy_overflow_label() -> None:
    assert bounded_count_bucket(101, overflow_label="101+") == "101+"
