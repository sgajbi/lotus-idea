from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from app.api.candidate_detail_models import CandidateDetailResponse
from app.domain import CandidatePersistenceRecord
from app.domain import DownstreamSubmissionPosture
from app.main import app
from tests.unit.downstream_submission_helpers import build_downstream_submission_record
from tests.unit.test_postgres_repository import access_scope, high_cash_candidate


def test_candidate_detail_response_redacts_source_routes_and_content_hashes() -> None:
    candidate = high_cash_candidate(candidate_scope=access_scope())
    expiry = datetime(2026, 7, 11, tzinfo=UTC)
    candidate = replace(
        candidate,
        evidence_packet=replace(
            candidate.evidence_packet,
            applicability_expires_at_utc=expiry,
        ),
    )
    record = CandidatePersistenceRecord(
        candidate=candidate,
        evidence_hash="sha256:candidate-detail",
        persisted_at_utc=candidate.created_at_utc,
    )

    response = CandidateDetailResponse.from_record(
        record,
        durable_storage_backed=True,
    ).model_dump(by_alias=True)

    assert response["candidate"]["candidateId"] == candidate.candidate_id
    assert response["candidate"]["applicabilityExpiresAtUtc"] == expiry
    assert response["evidence"]["applicabilityExpiresAtUtc"] == expiry
    assert response["evidence"]["evidenceContentHash"] == "sha256:candidate-detail"
    assert response["evidence"]["sourceRefs"][0] == {
        "productId": "lotus-core:PortfolioStateSnapshot:v1",
        "sourceSystem": "lotus-core",
        "productVersion": "v1",
        "asOfDate": candidate.evidence_packet.source_refs[0].as_of_date,
        "generatedAtUtc": candidate.evidence_packet.source_refs[0].generated_at_utc,
        "dataQualityStatus": "complete",
        "freshness": "current",
    }
    assert "route" not in response["evidence"]["sourceRefs"][0]
    assert "contentHash" not in response["evidence"]["sourceRefs"][0]
    assert response["durableStorageBacked"] is True
    assert response["supportedFeaturePromoted"] is False
    assert response["candidate"]["scoreReasonCodes"] == (
        "high_cash_ratio",
        "review_required",
        "materiality_score",
        "evidence_quality_score",
        "freshness_score",
    )
    assert response["candidate"]["scoreComponents"][0] == {
        "component": "materiality",
        "inputScore": "75.00",
        "weight": "0.70",
        "contribution": "52.50",
    }
    assert response["candidate"]["scoreConflictPenaltyApplied"] == "0"


def test_candidate_detail_response_exposes_only_adviser_safe_submission_posture() -> None:
    candidate = high_cash_candidate(candidate_scope=access_scope())
    record = CandidatePersistenceRecord(
        candidate=candidate,
        evidence_hash="sha256:candidate-detail-submission",
        persisted_at_utc=candidate.created_at_utc,
    )
    submission = build_downstream_submission_record(
        idempotency_key="candidate-detail-sensitive-key",
        request_fingerprint="sha256:candidate-detail-sensitive-fingerprint",
        resource_id="conversion-candidate-detail-001",
        submitted_at_utc=candidate.created_at_utc,
        status=DownstreamSubmissionPosture.RECONCILIATION_REQUIRED,
        failure_reason="private downstream diagnostic",
        correlation_id="corr-sensitive-candidate-detail",
        trace_id="trace-sensitive-candidate-detail",
    )

    response = CandidateDetailResponse.from_record(
        record,
        downstream_submissions=(submission,),
    ).model_dump(by_alias=True)

    assert response["downstreamSubmissions"] == (
        {
            "resourceType": "conversion_intent",
            "resourceId": "conversion-candidate-detail-001",
            "target": "advise_proposal",
            "sourceAuthority": "lotus-advise",
            "submissionPosture": "reconciliation_required",
            "submittedAtUtc": candidate.created_at_utc,
            "updatedAtUtc": candidate.created_at_utc,
            "attemptCount": 1,
            "operatorReconciliationRequired": True,
            "ownerReceipt": None,
            "recordsDownstreamOutcome": False,
            "grantsDownstreamAuthority": False,
        },
    )
    serialized = str(response["downstreamSubmissions"])
    assert "candidate-detail-sensitive-key" not in serialized
    assert "sensitive-fingerprint" not in serialized
    assert "private downstream diagnostic" not in serialized
    assert "corr-sensitive" not in serialized
    assert "trace-sensitive" not in serialized
    assert submission.support_reference not in serialized


def test_openapi_exposes_reconstructable_candidate_score_contract() -> None:
    schemas = app.openapi()["components"]["schemas"]
    candidate = schemas["CandidateDetailCandidateResponse"]
    contribution = schemas["ScoreContributionResponse"]

    assert {
        "applicabilityExpiresAtUtc",
        "scoreReasonCodes",
        "scoreComponents",
        "scoreConflictPenaltyApplied",
    } <= set(candidate["properties"])
    assert candidate["properties"]["scoreComponents"]["items"] == {
        "$ref": "#/components/schemas/ScoreContributionResponse"
    }
    assert contribution["properties"]["component"] == {
        "$ref": "#/components/schemas/ScoreComponent"
    }
    assert set(schemas["ScoreComponent"]["enum"]) == {
        "materiality",
        "urgency",
        "confidence",
        "evidence_quality",
        "freshness",
        "relevance",
        "downstream_fit",
        "legacy_fixed_policy",
    }
    assert set(contribution["required"]) == {
        "component",
        "inputScore",
        "weight",
        "contribution",
    }


def test_openapi_requires_source_safe_downstream_submission_posture() -> None:
    schemas = app.openapi()["components"]["schemas"]
    candidate_detail = schemas["CandidateDetailResponse"]
    submission = schemas["DownstreamSubmissionSummaryResponse"]

    assert "downstreamSubmissions" in candidate_detail["required"]
    assert candidate_detail["properties"]["downstreamSubmissions"]["items"] == {
        "$ref": "#/components/schemas/DownstreamSubmissionSummaryResponse"
    }
    assert set(submission["required"]) == {
        "resourceType",
        "resourceId",
        "target",
        "sourceAuthority",
        "submissionPosture",
        "submittedAtUtc",
        "updatedAtUtc",
        "attemptCount",
        "operatorReconciliationRequired",
        "recordsDownstreamOutcome",
        "grantsDownstreamAuthority",
    }
    assert submission["properties"]["resourceType"] == {
        "$ref": "#/components/schemas/DownstreamSubmissionResourceType",
        "description": "Idea-owned resource whose delivery posture is shown.",
    }
    assert submission["properties"]["submissionPosture"] == {
        "$ref": "#/components/schemas/DownstreamSubmissionPosture",
        "description": "Idea-owned local delivery posture; not a business outcome.",
    }
    assert set(schemas["DownstreamSubmissionPosture"]["enum"]) == {
        "in_flight",
        "accepted_by_downstream",
        "rejected_by_downstream",
        "not_configured",
        "reconciliation_required",
        "quarantined",
    }
    assert {
        "idempotencyKey",
        "supportReference",
        "downstreamFailureReason",
        "correlationId",
        "traceId",
        "auditHistory",
    }.isdisjoint(submission["properties"])
