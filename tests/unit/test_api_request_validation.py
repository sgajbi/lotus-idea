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


REQUESTED_AT = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


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


@pytest.mark.parametrize("identity", ["conversion/intent", "i" * 161])
def test_conversion_intent_request_rejects_non_addressable_identity(identity: str) -> None:
    with pytest.raises(ValidationError, match="conversionIntentId"):
        ConversionIntentRequest.model_validate(
            {
                "conversionIntentId": identity,
                "target": ConversionTarget.ADVISE_PROPOSAL,
                "reasonCodes": [ReasonCode.REVIEW_APPROVED_FOR_CONVERSION],
                "requestedAtUtc": REQUESTED_AT,
            }
        )


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
