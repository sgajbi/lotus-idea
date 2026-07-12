from __future__ import annotations

import hashlib
import json
from datetime import datetime

from app.domain.data_lifecycle.archive_posture import (
    ARCHIVE_LIFECYCLE_SCHEMA_VERSION,
    ArchiveLegalHoldStatus,
    ArchiveLifecycleAction,
    ArchiveLifecycleDecisionEnvelope,
    ArchiveLifecycleTrustedKey,
    ArchivePurgeStatus,
    ExpectedArchiveLifecyclePosture,
    VerifiedArchiveLifecycleReceipt,
)
from app.infrastructure.ed25519_signature_verifier import Ed25519SignatureVerifier


_EXPECTED_POSTURES = {
    ArchiveLifecycleAction.RETAIN: (
        ArchiveLegalHoldStatus.CLEAR,
        ArchivePurgeStatus.NOT_ELIGIBLE,
        "retention_period_active",
    ),
    ArchiveLifecycleAction.LEGAL_HOLD: (
        ArchiveLegalHoldStatus.ACTIVE,
        ArchivePurgeStatus.NOT_ELIGIBLE,
        "legal_hold_active",
    ),
    ArchiveLifecycleAction.DISPOSAL_ELIGIBLE: (
        ArchiveLegalHoldStatus.CLEAR,
        ArchivePurgeStatus.ELIGIBLE,
        "retention_elapsed",
    ),
    ArchiveLifecycleAction.DISPOSAL_EXECUTED: (
        ArchiveLegalHoldStatus.CLEAR,
        ArchivePurgeStatus.PURGED,
        "purge_executed",
    ),
}


def verify_archive_lifecycle_decision(
    *,
    envelope: ArchiveLifecycleDecisionEnvelope,
    trusted_keys: tuple[ArchiveLifecycleTrustedKey, ...],
    expected: ExpectedArchiveLifecyclePosture,
    signature_verifier: Ed25519SignatureVerifier,
) -> VerifiedArchiveLifecycleReceipt:
    claims = envelope.claims
    _require(claims.contract_version == ARCHIVE_LIFECYCLE_SCHEMA_VERSION, "contract version")
    _require(claims.authority == "lotus-archive", "authority")
    _require(claims.signing_algorithm == "Ed25519", "signing algorithm")
    _require(not claims.disposal_authorized, "disposal authority boundary")
    _require(claims.tenant_id == expected.tenant_id, "tenant")
    _require(claims.idea_candidate_id == expected.candidate_id, "candidate")
    _require(
        claims.idea_evidence_pack_id in expected.linked_evidence_pack_ids,
        "evidence pack",
    )
    _require(
        claims.issued_at_utc <= expected.verified_at_utc < claims.expires_at_utc,
        "validity window",
    )
    _require(
        (claims.expires_at_utc - claims.issued_at_utc).total_seconds() <= 300,
        "maximum validity",
    )
    hold_status, purge_status, reason = _EXPECTED_POSTURES[claims.lifecycle_action]
    _require(claims.legal_hold_status is hold_status, "legal hold posture")
    _require(claims.purge_status is purge_status, "purge posture")
    _require(claims.decision_reason_code == reason, "reason code")
    _require(
        (claims.legal_hold_count > 0)
        is (claims.legal_hold_status is ArchiveLegalHoldStatus.ACTIVE),
        "legal hold count",
    )

    key = _select_key(claims.signing_key_id, trusted_keys, claims.issued_at_utc)
    canonical = json.dumps(
        dict(envelope.canonical_claims),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = "sha256:" + hashlib.sha256(canonical).hexdigest()
    _require(envelope.payload_digest == digest, "payload digest")
    signature_verifier.verify(
        public_key_base64url=key.public_key_base64url,
        signature_base64url=envelope.signature.removeprefix("ed25519:"),
        canonical_payload=canonical,
    )
    return VerifiedArchiveLifecycleReceipt(
        decision_id=claims.decision_id,
        document_id=claims.document_id,
        evidence_pack_id=claims.idea_evidence_pack_id,
        candidate_id=claims.idea_candidate_id,
        tenant_id=claims.tenant_id,
        retention_policy_id=claims.retention_policy_id,
        legal_hold_status=claims.legal_hold_status,
        purge_status=claims.purge_status,
        lifecycle_action=claims.lifecycle_action,
        payload_digest=envelope.payload_digest,
        key_id=key.key_id,
        issued_at_utc=claims.issued_at_utc,
        expires_at_utc=claims.expires_at_utc,
        verified_at_utc=expected.verified_at_utc,
    )


def _select_key(
    key_id: str,
    trusted_keys: tuple[ArchiveLifecycleTrustedKey, ...],
    issued_at_utc: datetime,
) -> ArchiveLifecycleTrustedKey:
    matches = tuple(key for key in trusted_keys if key.key_id == key_id)
    _require(len(matches) == 1, "known unique signing key")
    key = matches[0]
    _require(key.status in {"active", "rotated"}, "signing key status")
    _require(key.not_before_utc <= issued_at_utc, "key validity start")
    _require(key.not_after_utc is None or issued_at_utc < key.not_after_utc, "key validity end")
    return key


def _require(condition: bool, label: str) -> None:
    if not condition:
        raise ValueError(f"lotus-archive lifecycle posture failed {label} verification")
