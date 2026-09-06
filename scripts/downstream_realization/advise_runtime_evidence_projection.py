# ruff: noqa: E402
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.downstream_realization.advise_intake_runtime_execution import (
    source_safe_receipt_digest,
)
from app.application.downstream_realization.intake_runtime_execution_common import (
    source_safe_binding_digest,
)
from scripts.downstream_realization.intake_runtime_generator_common import body_get, reason_codes


def source_safe_execution_evidence(
    raw: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    for name, response in raw.items():
        if name == "submittedIntent":
            evidence[name] = _submitted_intent(response)
            continue
        body = response.get("body") if isinstance(response, Mapping) else {}
        if name == "ownerRealization":
            evidence[name] = _owner_realization(response, body)
            continue
        if name == "ownerAdvancement":
            evidence[name] = _owner_advancement(response)
            continue
        if name == "preCommitTimeout":
            evidence[name] = _pre_commit_timeout(response)
            continue
        evidence[name] = _receipt(response, body)
    return evidence


def _pre_commit_timeout(value: object) -> dict[str, Any]:
    raw = value if isinstance(value, Mapping) else {}
    owner_lookup = raw.get("ownerLookup")
    repeated_owner_lookup = raw.get("repeatedOwnerLookup")
    owner_lookup_body = owner_lookup.get("body") if isinstance(owner_lookup, Mapping) else None
    repeated_owner_lookup_body = (
        repeated_owner_lookup.get("body") if isinstance(repeated_owner_lookup, Mapping) else None
    )
    return {
        "failureStage": raw.get("failureStage"),
        "sourceIntentDigest": source_safe_binding_digest(
            raw.get("ideaCandidateId"), raw.get("conversionIntentId")
        ),
        "scopeDigest": source_safe_binding_digest(
            raw.get("tenantId"), raw.get("legalEntityCode"), raw.get("portfolioId")
        ),
        "ownerLookupStatusCode": (
            owner_lookup.get("statusCode") if isinstance(owner_lookup, Mapping) else None
        ),
        "ownerLookupReasonCodes": reason_codes(owner_lookup_body),
        "repeatedOwnerLookupStatusCode": (
            repeated_owner_lookup.get("statusCode")
            if isinstance(repeated_owner_lookup, Mapping)
            else None
        ),
        "repeatedOwnerLookupReasonCodes": reason_codes(repeated_owner_lookup_body),
        "downstreamPostAttemptCount": raw.get("downstreamPostAttemptCount"),
        "automaticResubmissionAttemptCount": raw.get("automaticResubmissionAttemptCount"),
        "ownerStateObserved": raw.get("ownerStateObserved"),
    }


def _receipt(response: object, body: object) -> dict[str, Any]:
    receipt = {
        "statusCode": response.get("statusCode") if isinstance(response, Mapping) else None,
        "intakeStatus": body_get(body, "intake_status"),
        "intakeReceiptAccepted": body_get(body, "intake_receipt_accepted"),
        "idempotencyReplay": body_get(body, "idempotency_replay"),
        "receiptDigest": None,
        "reasonCodes": reason_codes(body),
        "ownerIdentityDigest": source_safe_binding_digest(
            body_get(body, "intake_id"),
            body_get(body, "realization_id"),
            body_get(body, "review_work_id"),
        ),
        "scopeDigest": source_safe_binding_digest(
            body_get(body_get(body, "trusted_scope"), "tenant_id"),
            body_get(body_get(body, "trusted_scope"), "legal_entity_code"),
            body_get(body, "portfolio_id"),
        ),
        "reviewWorkStatus": body_get(body, "review_work_status"),
        "sourceEvidenceFingerprint": body_get(body, "source_evidence_fingerprint"),
        "realizationStatus": body_get(body, "realization_status"),
        "sourceEventVersion": body_get(body, "source_event_version"),
        "proposalRecordCreated": bool(body_get(body, "proposal_record_created") or False),
        "suitabilityAuthorityGranted": bool(
            body_get(body, "suitability_authority_granted") or False
        ),
        "orderCreated": bool(body_get(body, "order_created") or False),
        "clientPublicationAuthorized": bool(
            body_get(body, "client_publication_authorized") or False
        ),
    }
    receipt["receiptDigest"] = source_safe_receipt_digest(receipt)
    return receipt


def _submitted_intent(value: object) -> dict[str, str]:
    submitted = value if isinstance(value, Mapping) else {}
    return {
        "scopeDigest": source_safe_binding_digest(
            submitted.get("tenantId"),
            submitted.get("legalEntityCode"),
            submitted.get("portfolioId"),
        ),
        "sourceIntentDigest": source_safe_binding_digest(
            submitted.get("ideaCandidateId"), submitted.get("conversionIntentId")
        ),
    }


def _owner_realization(response: object, body: object) -> dict[str, Any]:
    raw_outcomes = body_get(body, "outcomes")
    outcomes = raw_outcomes if isinstance(raw_outcomes, list) else []
    return {
        "statusCode": response.get("statusCode") if isinstance(response, Mapping) else None,
        "ownerIdentityDigest": source_safe_binding_digest(
            body_get(body, "intake_id"),
            body_get(body, "realization_id"),
            body_get(body, "review_work_id"),
        ),
        "scopeDigest": source_safe_binding_digest(
            body_get(body, "tenant_id"),
            body_get(body, "legal_entity_code"),
            body_get(body, "portfolio_id"),
        ),
        "reviewWorkStatus": body_get(body, "review_work_status"),
        "sourceIntentDigest": source_safe_binding_digest(
            body_get(body, "idea_candidate_id"), body_get(body, "conversion_intent_id")
        ),
        "sourceEvidenceFingerprint": body_get(body, "source_evidence_fingerprint"),
        "currentStatus": body_get(body, "current_status"),
        "currentSourceEventVersion": body_get(body, "current_source_event_version"),
        "proposalIdentityPresent": body_get(body, "proposal_id") is not None,
        "proposalRecordCreated": bool(body_get(body, "proposal_record_created") or False),
        "suitabilityAuthorityGranted": bool(
            body_get(body, "suitability_authority_granted") or False
        ),
        "orderCreated": bool(body_get(body, "order_created") or False),
        "clientPublicationAuthorized": bool(
            body_get(body, "client_publication_authorized") or False
        ),
        "outcomes": [
            {
                "sourceEventVersion": body_get(outcome, "source_event_version"),
                "status": body_get(outcome, "status"),
                "reasonCode": body_get(outcome, "reason_code"),
                "ownerWorkBound": body_get(outcome, "review_work_id")
                == body_get(body, "review_work_id"),
                "proposalIdentityPresent": body_get(outcome, "proposal_id") is not None,
                "terminal": body_get(outcome, "terminal"),
            }
            for outcome in outcomes
        ],
    }


def _owner_advancement(value: object) -> dict[str, Any]:
    raw = value if isinstance(value, Mapping) else {}
    linked = raw.get("linked")
    stale = raw.get("staleCorrection")
    after_refusal = raw.get("afterStaleCorrection")
    concurrent = raw.get("concurrentAdvancement")
    final = raw.get("finalReadback")
    linked_body = linked.get("body") if isinstance(linked, Mapping) else None
    after_refusal_body = after_refusal.get("body") if isinstance(after_refusal, Mapping) else None
    final_body = final.get("body") if isinstance(final, Mapping) else None
    concurrent_responses = concurrent if isinstance(concurrent, list) else []
    final_outcomes = body_get(final_body, "outcomes")
    outcomes = final_outcomes if isinstance(final_outcomes, list) else []
    return {
        "ownerIdentityDigest": source_safe_binding_digest(
            body_get(final_body, "intake_id"),
            body_get(final_body, "realization_id"),
            body_get(final_body, "review_work_id"),
        ),
        "scopeDigest": source_safe_binding_digest(
            body_get(final_body, "tenant_id"),
            body_get(final_body, "legal_entity_code"),
            body_get(final_body, "portfolio_id"),
        ),
        "sourceIntentDigest": source_safe_binding_digest(
            body_get(final_body, "idea_candidate_id"),
            body_get(final_body, "conversion_intent_id"),
        ),
        "sourceEvidenceFingerprint": body_get(final_body, "source_evidence_fingerprint"),
        "linkedStatusCode": linked.get("statusCode") if isinstance(linked, Mapping) else None,
        "linkedSourceEventVersion": body_get(linked_body, "current_source_event_version"),
        "staleCorrectionStatusCode": (
            stale.get("statusCode") if isinstance(stale, Mapping) else None
        ),
        "staleCorrectionReasonCodes": reason_codes(
            stale.get("body") if isinstance(stale, Mapping) else None
        ),
        "sourceEventVersionAfterRefusal": body_get(
            after_refusal_body, "current_source_event_version"
        ),
        "concurrentStatusCodes": [
            response.get("statusCode") if isinstance(response, Mapping) else None
            for response in concurrent_responses
        ],
        "concurrentSourceEventVersions": [
            body_get(response.get("body"), "current_source_event_version")
            if isinstance(response, Mapping)
            else None
            for response in concurrent_responses
        ],
        "finalStatusCode": final.get("statusCode") if isinstance(final, Mapping) else None,
        "finalStatus": body_get(final_body, "current_status"),
        "finalSourceEventVersion": body_get(final_body, "current_source_event_version"),
        "finalOutcomeVersions": [body_get(outcome, "source_event_version") for outcome in outcomes],
        "finalOutcomeStatuses": [body_get(outcome, "status") for outcome in outcomes],
        "proposalIdentityPresent": body_get(final_body, "proposal_id") is not None,
        "proposalRecordCreated": bool(body_get(final_body, "proposal_record_created") or False),
        "suitabilityAuthorityGranted": bool(
            body_get(final_body, "suitability_authority_granted") or False
        ),
        "orderCreated": bool(body_get(final_body, "order_created") or False),
        "clientPublicationAuthorized": bool(
            body_get(final_body, "client_publication_authorized") or False
        ),
    }
