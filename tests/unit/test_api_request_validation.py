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
        lambda: FeedbackRequest.model_validate(
            {
                "feedbackId": "feedback-useful-001",
                "outcome": FeedbackOutcome.USEFUL,
                "reasonCodes": [],
                "recordedAtUtc": REQUESTED_AT,
            }
        ),
    )

    for build_request in invalid_requests:
        with pytest.raises(ValidationError, match="reasonCodes is required"):
            build_request()


def _access_scope_payload() -> dict[str, str]:
    return {
        "tenantId": "tenant-private-bank-sg",
        "bookId": "book-advisor-001",
        "portfolioId": "PB_SG_GLOBAL_BAL_001",
        "clientId": "client-001",
    }
