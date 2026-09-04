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
        evidence[name] = _receipt(response, body)
    return evidence


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
