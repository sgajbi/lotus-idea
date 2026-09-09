from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.api.candidate_lifecycle import (
    CandidateLifecycleTransitionRequest,
    CallerSettableIdeaLifecycleStatus,
)
from app.api.conversion_governance import ConversionIntentRequest
from app.api.conversion_governance_models import ConversionOutcomeRequest
from app.api.report_evidence import ReportEvidencePackRequest
from app.api.request_validation import require_non_empty_reason_codes
from app.api.review_workflow import (
    FeedbackRequest,
    ReviewActionRequest,
)
from app.domain import (
    ConversionTarget,
    FeedbackOutcome,
    ReasonCode,
    ReportEvidencePackPurpose,
    ReviewAction,
)
from app.domain.evidence_digest import REVISION_VECTOR_DIGEST_PATTERN, SHA256_DIGEST_PATTERN


REQUESTED_AT = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)
CONVERSION_AUTHORITY_FIELDS = {
    "expectedReviewId": "review-approve-001",
    "expectedMaterialVersion": 1,
    "expectedEvidenceVersion": 1,
    "expectedEvidencePacketId": "evidence-packet-001",
    "expectedEvidenceContentHash": "sha256:130db97f723f60c45a5e85a5794d11fab3a339ffa6d17a4341ab1e15582b0a21",
    "expectedSourceRevisionVectorDigest": "sha256:73735e44a8921cf0f0829e9a7d0d637e57a15ec43f6cf1836da0d5208cdf772d",
    "expectedSourceCutPosture": "coherent",
}


def _conversion_intent_request_payload() -> dict[str, object]:
    return {
        "conversionIntentId": "conversion-report-001",
        "target": ConversionTarget.REPORT_EVIDENCE,
        "reasonCodes": [ReasonCode.REVIEW_APPROVED_FOR_CONVERSION],
        "requestedAtUtc": REQUESTED_AT,
        **CONVERSION_AUTHORITY_FIELDS,
    }


def _review_action_request_payload() -> dict[str, object]:
    return {
        "reviewId": "review-reject-001",
        "action": ReviewAction.REJECT,
        "reasonCodes": [ReasonCode.REVIEW_REQUIRED],
        "decidedAtUtc": REQUESTED_AT,
        "reviewChannel": "workbench",
        "expectedMaterialVersion": 1,
        "expectedEvidenceVersion": 1,
        "expectedEvidencePacketId": "evidence-packet-001",
        "expectedEvidenceContentHash": CONVERSION_AUTHORITY_FIELDS["expectedEvidenceContentHash"],
        "expectedSourceRevisionVectorDigest": CONVERSION_AUTHORITY_FIELDS[
            "expectedSourceRevisionVectorDigest"
        ],
        "expectedSourceCutPosture": "coherent",
        "presentationReceiptId": "receipt-001",
    }


def test_require_non_empty_reason_codes_preserves_tuple_values() -> None:
    assert require_non_empty_reason_codes((ReasonCode.REVIEW_REQUIRED,)) == (
        ReasonCode.REVIEW_REQUIRED,
    )


def test_require_non_empty_reason_codes_rejects_empty_tuple() -> None:
    with pytest.raises(ValueError, match="reasonCodes is required"):
        require_non_empty_reason_codes(())


def test_mutating_workflow_requests_reject_empty_reason_codes() -> None:
    invalid_requests: tuple[Callable[[], object], ...] = (
        lambda: CandidateLifecycleTransitionRequest.model_validate(
            {
                "transitionId": "lifecycle-enriched-001",
                "targetLifecycleStatus": CallerSettableIdeaLifecycleStatus.ENRICHED,
                "changedAtUtc": REQUESTED_AT,
                "reasonCodes": [],
            }
        ),
        lambda: ConversionIntentRequest.model_validate(
            {
                "conversionIntentId": "conversion-report-001",
                "target": ConversionTarget.REPORT_EVIDENCE,
                "reasonCodes": [],
                "requestedAtUtc": REQUESTED_AT,
                **CONVERSION_AUTHORITY_FIELDS,
            }
        ),
        lambda: ReportEvidencePackRequest.model_validate(
            {
                "reportEvidencePackId": "report-pack-001",
                "purpose": ReportEvidencePackPurpose.CLIENT_REVIEW_REPORT_SECTION,
                "reasonCodes": [],
                "requestedAtUtc": REQUESTED_AT,
                "retentionPolicyRef": "lotus-report:idea-evidence-retention:v1",
                "clientReadyPublicationRequested": False,
            }
        ),
        lambda: ReviewActionRequest.model_validate(
            {
                "reviewId": "review-suppress-001",
                "action": ReviewAction.SUPPRESS,
                "reasonCodes": [],
                "decidedAtUtc": REQUESTED_AT,
            }
        ),
    )

    for build_request in invalid_requests:
        with pytest.raises(ValidationError, match="reasonCodes is required"):
            build_request()


def test_conversion_intent_request_preserves_opaque_identity() -> None:
    request = ConversionIntentRequest.model_validate(
        {
            "conversionIntentId": "legacy/conversion intent?version=1",
            "target": ConversionTarget.ADVISE_PROPOSAL,
            "reasonCodes": [ReasonCode.REVIEW_APPROVED_FOR_CONVERSION],
            "requestedAtUtc": REQUESTED_AT,
            **CONVERSION_AUTHORITY_FIELDS,
        }
    )

    assert request.conversion_intent_id == "legacy/conversion intent?version=1"


def test_conversion_intent_request_rejects_oversized_identity() -> None:
    with pytest.raises(ValidationError, match="conversionIntentId"):
        ConversionIntentRequest.model_validate(
            {
                "conversionIntentId": "i" * 161,
                "target": ConversionTarget.ADVISE_PROPOSAL,
                "reasonCodes": [ReasonCode.REVIEW_APPROVED_FOR_CONVERSION],
                "requestedAtUtc": REQUESTED_AT,
                **CONVERSION_AUTHORITY_FIELDS,
            }
        )


@pytest.mark.parametrize(
    ("request_type", "payload_factory"),
    (
        (ConversionIntentRequest, _conversion_intent_request_payload),
        (ReviewActionRequest, _review_action_request_payload),
    ),
)
@pytest.mark.parametrize(
    ("field_name", "malformed_value"),
    (
        ("expectedEvidenceContentHash", "x"),
        ("expectedEvidenceContentHash", f"sha256:{'A' * 64}"),
        ("expectedSourceRevisionVectorDigest", "a" * 64),
        ("expectedSourceRevisionVectorDigest", f"sha256:{'a' * 63} "),
    ),
)
def test_human_authority_requests_reject_malformed_evidence_digests(
    request_type: type[ConversionIntentRequest] | type[ReviewActionRequest],
    payload_factory: Callable[[], dict[str, object]],
    field_name: str,
    malformed_value: str,
) -> None:
    payload = payload_factory()
    payload[field_name] = malformed_value

    with pytest.raises(ValidationError, match="string_pattern_mismatch"):
        request_type.model_validate(payload)


@pytest.mark.parametrize(
    ("request_type", "payload_factory"),
    (
        (ConversionIntentRequest, _conversion_intent_request_payload),
        (ReviewActionRequest, _review_action_request_payload),
    ),
)
def test_human_authority_requests_preserve_historical_revision_vector_sentinel(
    request_type: type[ConversionIntentRequest] | type[ReviewActionRequest],
    payload_factory: Callable[[], dict[str, object]],
) -> None:
    payload = payload_factory()
    payload["expectedSourceRevisionVectorDigest"] = "legacy:unknown"

    request = request_type.model_validate(payload)

    assert request.expected_source_revision_vector_digest == "legacy:unknown"


@pytest.mark.parametrize("request_type", (ConversionIntentRequest, ReviewActionRequest))
def test_human_authority_request_schema_publishes_digest_constraints(
    request_type: type[ConversionIntentRequest] | type[ReviewActionRequest],
) -> None:
    properties = request_type.model_json_schema(by_alias=True)["properties"]

    assert properties["expectedEvidenceContentHash"]["pattern"] == SHA256_DIGEST_PATTERN.pattern
    assert (
        properties["expectedSourceRevisionVectorDigest"]["pattern"]
        == REVISION_VECTOR_DIGEST_PATTERN.pattern
    )


def test_human_authority_requests_reject_blank_or_ambiguous_fields() -> None:
    conversion_payload = _conversion_intent_request_payload()
    conversion_payload["expectedReviewId"] = " "
    with pytest.raises(ValidationError, match="review authority identity fields are required"):
        ConversionIntentRequest.model_validate(conversion_payload)

    review_payload = _review_action_request_payload()
    review_payload["snoozedUntilUtc"] = None
    assert ReviewActionRequest.model_validate(review_payload).snoozed_until_utc is None
    review_payload["expectedEvidencePacketId"] = " "
    with pytest.raises(ValidationError, match="reviewId is required"):
        ReviewActionRequest.model_validate(review_payload)


def test_feedback_request_requires_the_explicit_taxonomy_contract() -> None:
    with pytest.raises(ValidationError, match="taxonomyVersion"):
        FeedbackRequest.model_validate(
            {
                "feedbackId": "feedback-useful-001",
                "outcome": FeedbackOutcome.USEFUL,
                "reason": "relevant",
                "recordedAtUtc": REQUESTED_AT,
            }
        )


@pytest.mark.parametrize(
    "field_name",
    ("supersedesConversionOutcomeId", "correctionReason"),
)
def test_conversion_outcome_request_rejects_blank_correction_fields(field_name: str) -> None:
    payload = {
        "conversionOutcomeId": "conversion-outcome-correction-001",
        "status": "accepted",
        "sourceSystem": "lotus-report",
        "sourceEventVersion": 2,
        "recordedAtUtc": REQUESTED_AT,
        "supersedesConversionOutcomeId": "conversion-outcome-rejected-001",
        "correctionReason": "source correction",
    }
    payload[field_name] = " "

    with pytest.raises(ValidationError, match="correction fields cannot be blank"):
        ConversionOutcomeRequest.model_validate(payload)


def _access_scope_payload() -> dict[str, str]:
    return {
        "tenantId": "tenant-private-bank-sg",
        "bookId": "book-advisor-001",
        "portfolioId": "PB_SG_GLOBAL_BAL_001",
        "clientId": "client-001",
    }
