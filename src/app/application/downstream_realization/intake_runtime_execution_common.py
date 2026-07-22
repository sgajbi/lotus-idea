from __future__ import annotations

from collections.abc import Callable, Mapping
import hashlib
import json
from typing import Any

from app.application.source_runtime_evidence import is_sha256


def source_safe_intake_receipt_digest(
    receipt: Mapping[str, Any],
    *,
    digest_fields: tuple[str, ...],
) -> str:
    canonical = {field: receipt.get(field) for field in digest_fields}
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def intake_receipt_evidence_is_valid(
    receipt_evidence: Mapping[str, Any],
    *,
    expected_fields: frozenset[str],
    accepted_receipt_is_valid: Callable[[object], bool],
    replay_receipt_is_valid: Callable[[object], bool],
    rejected_receipt_is_valid: Callable[[object], bool],
    conflict_receipt_is_valid: Callable[[object], bool],
    authorization_denied_receipt_is_valid: Callable[[object], bool],
    tenant_isolation_receipt_is_valid: Callable[[object], bool],
) -> bool:
    return (
        set(receipt_evidence) == expected_fields
        and accepted_receipt_is_valid(receipt_evidence.get("accepted"))
        and replay_receipt_is_valid(receipt_evidence.get("acceptedReplay"))
        and rejected_receipt_is_valid(receipt_evidence.get("rejected"))
        and conflict_receipt_is_valid(receipt_evidence.get("idempotencyConflict"))
        and authorization_denied_receipt_is_valid(receipt_evidence.get("authorizationDenied"))
        and tenant_isolation_receipt_is_valid(receipt_evidence.get("tenantScopedIdempotency"))
    )


def intake_receipt_matches(
    value: object,
    *,
    receipt_fields: frozenset[str],
    status_code: int,
    intake_status: str | None,
    accepted: bool | None,
    replay: bool | None,
    reason_codes: tuple[str, ...],
    digest: Callable[[Mapping[str, Any]], str],
    retained_false_fields: tuple[str, ...],
) -> bool:
    if not isinstance(value, Mapping) or set(value) != receipt_fields:
        return False
    return (
        value.get("statusCode") == status_code
        and value.get("intakeStatus") == intake_status
        and value.get("intakeReceiptAccepted") is accepted
        and value.get("idempotencyReplay") is replay
        and tuple(value.get("reasonCodes") or ()) == reason_codes
        and is_sha256(value.get("receiptDigest"))
        and value.get("receiptDigest") == digest(value)
        and all(value.get(field) is False for field in retained_false_fields)
    )


def non_proof_claims_are_retained(value: object, *, expected_fields: frozenset[str]) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == expected_fields
        and all(value.get(key) is False for key in expected_fields)
    )
