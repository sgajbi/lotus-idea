from __future__ import annotations

import base64
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import hashlib
import json
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.application.data_lifecycle.archive_posture_verification import (
    verify_archive_lifecycle_decision,
)
from app.domain.data_lifecycle.archive_posture import (
    ArchiveLifecycleAction,
    ArchiveLifecycleTrustedKey,
    ExpectedArchiveLifecyclePosture,
    VerifiedArchiveLifecycleReceipt,
)
from app.infrastructure.ed25519_signature_verifier import Ed25519SignatureVerifier
from app.integration.data_lifecycle.archive_posture_contract import (
    map_archive_lifecycle_decision,
)


NOW = datetime(2026, 7, 12, 5, 0, tzinfo=UTC)
PRIVATE_KEY = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))


def test_verifies_archive_posture_without_granting_disposal_authority() -> None:
    receipt = _verify(_signed_payload())

    assert receipt.candidate_id == "candidate-001"
    assert receipt.evidence_pack_id == "report-pack-001"
    assert receipt.lifecycle_action is ArchiveLifecycleAction.RETAIN
    assert receipt.document_id == "document-001"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("tenant_id", "tenant-other", "tenant"),
        ("idea_candidate_id", "candidate-other", "candidate"),
        ("idea_evidence_pack_id", "report-pack-other", "evidence pack"),
        ("authority", "lotus-idea", "authority"),
        ("disposal_authorized", True, "disposal authority boundary"),
        ("signing_algorithm", "RS256", "signing algorithm"),
    ],
)
def test_rejects_substituted_identity_or_authority(
    field: str,
    value: Any,
    message: str,
) -> None:
    payload = _payload()
    payload[field] = value

    with pytest.raises(ValueError, match=message):
        _verify(_signed_payload(payload))


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"legal_hold_status": "active"}, "legal hold posture"),
        ({"purge_status": "eligible"}, "purge posture"),
        ({"decision_reason_code": "retention_elapsed"}, "reason code"),
        ({"legal_hold_count": 1}, "legal hold count"),
        ({"expires_at_utc": "2026-07-12T05:06:00Z"}, "maximum validity"),
    ],
)
def test_rejects_internally_inconsistent_or_overlong_posture(
    changes: dict[str, Any],
    message: str,
) -> None:
    payload = _payload()
    payload.update(changes)

    with pytest.raises(ValueError, match=message):
        _verify(_signed_payload(payload))


def test_accepts_active_hold_only_with_matching_archive_posture() -> None:
    payload = _payload()
    payload.update(
        {
            "legal_hold_status": "active",
            "legal_hold_count": 1,
            "lifecycle_action": "LEGAL_HOLD",
            "decision_reason_code": "legal_hold_active",
        }
    )

    receipt = _verify(_signed_payload(payload))

    assert receipt.lifecycle_action is ArchiveLifecycleAction.LEGAL_HOLD


def test_rejects_expiry_unknown_key_revocation_digest_and_signature_tampering() -> None:
    with pytest.raises(ValueError, match="validity window"):
        _verify(_signed_payload(), verified_at=NOW + timedelta(minutes=5))
    with pytest.raises(ValueError, match="known unique signing key"):
        _verify(_signed_payload(), key_id="archive-other")
    with pytest.raises(ValueError, match="signing key status"):
        _verify(_signed_payload(), key_status="revoked")

    digest_tampered = _signed_payload()
    digest_tampered["payload_digest"] = "sha256:" + "f" * 64
    with pytest.raises(ValueError, match="payload digest"):
        _verify(digest_tampered)

    signature_tampered = _signed_payload()
    signature_tampered["signature"] = "ed25519:" + "A" * 86
    with pytest.raises(ValueError, match="signature is invalid"):
        _verify(signature_tampered)


def test_strict_mapper_rejects_unknown_or_source_unsafe_fields() -> None:
    payload = _signed_payload()
    payload["raw_document_content"] = "forbidden"
    with pytest.raises(ValueError, match="Extra inputs are not permitted"):
        map_archive_lifecycle_decision(payload)

    payload = _payload()
    payload["document_id"] = "unsafe document id"
    with pytest.raises(ValueError, match="source-safe reference"):
        map_archive_lifecycle_decision(_signed_payload(payload))


def test_expected_and_verified_receipts_reject_malformed_persisted_identity() -> None:
    with pytest.raises(ValueError, match="linked_evidence_pack_ids is required"):
        ExpectedArchiveLifecyclePosture(
            tenant_id="tenant-001",
            candidate_id="candidate-001",
            linked_evidence_pack_ids=frozenset(),
            verified_at_utc=NOW,
        )

    receipt = _verify(_signed_payload())
    with pytest.raises(ValueError, match="source-safe reference"):
        replace(receipt, document_id="unsafe document id")
    with pytest.raises(ValueError, match="prefixed lowercase SHA-256"):
        replace(receipt, payload_digest="not-a-digest")
    with pytest.raises(ValueError, match="timezone-aware UTC"):
        replace(receipt, verified_at_utc=NOW.replace(tzinfo=None))
    with pytest.raises(ValueError, match="outside its validity window"):
        replace(receipt, verified_at_utc=receipt.expires_at_utc)


def _verify(
    payload: dict[str, Any],
    *,
    verified_at: datetime = NOW,
    key_id: str = "archive-lifecycle-2026-07",
    key_status: str = "active",
) -> VerifiedArchiveLifecycleReceipt:
    return verify_archive_lifecycle_decision(
        envelope=map_archive_lifecycle_decision(payload),
        trusted_keys=(
            ArchiveLifecycleTrustedKey(
                key_id=key_id,
                public_key_base64url=base64.urlsafe_b64encode(
                    PRIVATE_KEY.public_key().public_bytes_raw()
                ).decode("ascii"),
                status=key_status,
                not_before_utc=NOW - timedelta(days=1),
                not_after_utc=NOW + timedelta(days=30),
            ),
        ),
        expected=ExpectedArchiveLifecyclePosture(
            tenant_id="tenant-001",
            candidate_id="candidate-001",
            linked_evidence_pack_ids=frozenset({"report-pack-001"}),
            verified_at_utc=verified_at,
        ),
        signature_verifier=Ed25519SignatureVerifier(),
    )


def _signed_payload(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    result = deepcopy(payload or _payload())
    canonical = json.dumps(
        result,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    result["payload_digest"] = "sha256:" + hashlib.sha256(canonical).hexdigest()
    result["signature"] = "ed25519:" + base64.urlsafe_b64encode(PRIVATE_KEY.sign(canonical)).decode(
        "ascii"
    )
    return result


def _payload() -> dict[str, Any]:
    return {
        "contract_version": "lotus-archive:IdeaEvidenceLifecycleDecision:v1",
        "decision_id": "archive-lifecycle-decision-001",
        "document_id": "document-001",
        "idea_evidence_pack_id": "report-pack-001",
        "idea_candidate_id": "candidate-001",
        "source_correlation_ref": "source-correlation-001",
        "tenant_id": "tenant-001",
        "residency_region": "SG",
        "retention_policy_id": "generated-report-standard",
        "legal_hold_status": "clear",
        "legal_hold_count": 0,
        "purge_status": "not_eligible",
        "lifecycle_action": "RETAIN",
        "disposal_authorized": False,
        "decision_reason_code": "retention_period_active",
        "authority": "lotus-archive",
        "issued_at_utc": "2026-07-12T05:00:00Z",
        "expires_at_utc": "2026-07-12T05:05:00Z",
        "correlation_id": "correlation-001",
        "trace_id": "trace-001",
        "signing_algorithm": "Ed25519",
        "signing_key_id": "archive-lifecycle-2026-07",
    }
