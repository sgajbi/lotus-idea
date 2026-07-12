from __future__ import annotations

from datetime import datetime
import json
from typing import Protocol

from app.application.ed25519_key_trust import select_trusted_ed25519_key
from app.domain.data_lifecycle.authority import (
    LIFECYCLE_AUTHORITY_AUDIENCE,
    LIFECYCLE_AUTHORITY_ISSUER,
    LIFECYCLE_AUTHORITY_KEY_DISCOVERY_PATH,
    LIFECYCLE_AUTHORITY_KEY_SCHEMA_VERSION,
    LIFECYCLE_AUTHORITY_SCHEMA_VERSION,
    ExpectedLifecycleAuthorityDecision,
    LifecycleAuthorityDecisionEnvelope,
    LifecycleAuthorityKeyDiscovery,
    LifecycleAuthorityPublicKey,
    VerifiedLifecycleAuthorityReceipt,
    expected_authority_domain,
)


class LifecycleAuthoritySignatureVerifier(Protocol):
    def verify(
        self,
        *,
        public_key_base64url: str,
        signature_base64url: str,
        canonical_payload: bytes,
    ) -> None: ...


def verify_lifecycle_authority_decision(
    *,
    envelope: LifecycleAuthorityDecisionEnvelope,
    key_discovery: LifecycleAuthorityKeyDiscovery,
    expected: ExpectedLifecycleAuthorityDecision,
    signature_verifier: LifecycleAuthoritySignatureVerifier,
) -> VerifiedLifecycleAuthorityReceipt:
    claims = envelope.claims
    _require(
        claims.schema_version == LIFECYCLE_AUTHORITY_SCHEMA_VERSION,
        "schema version",
    )
    _require(
        key_discovery.schema_version == LIFECYCLE_AUTHORITY_KEY_SCHEMA_VERSION,
        "key schema version",
    )
    _require(
        claims.issuer == key_discovery.issuer == LIFECYCLE_AUTHORITY_ISSUER,
        "issuer",
    )
    _require(claims.audience == LIFECYCLE_AUTHORITY_AUDIENCE, "audience")
    _require(envelope.key_discovery_path == LIFECYCLE_AUTHORITY_KEY_DISCOVERY_PATH, "key path")
    _require(claims.decision_status == "approved", "decision status")
    _require(claims.tenant_id == expected.tenant_id, "tenant identity")
    _require(claims.candidate_id == expected.candidate_id, "candidate identity")
    _require(claims.action is expected.action, "action")
    _require(
        claims.authority_domain is expected_authority_domain(expected.action), "authority domain"
    )
    _require(claims.authority_ref == expected.authority_ref, "authority reference")
    _require(claims.change_reference == expected.change_reference, "change reference")
    _require(
        claims.effective_at_utc <= expected.verified_at_utc < claims.expires_at_utc,
        "validity window",
    )
    key = select_trusted_ed25519_key(
        signature=envelope.signature,
        keys=key_discovery.keys,
        issued_at_utc=claims.issued_at_utc,
        require=_require,
    )
    _verify_signature(envelope=envelope, key=key, signature_verifier=signature_verifier)
    return VerifiedLifecycleAuthorityReceipt(
        decision_id=claims.decision_id,
        replay_nonce=claims.replay_nonce,
        tenant_id=claims.tenant_id,
        candidate_id=claims.candidate_id,
        action=claims.action,
        authority_domain=claims.authority_domain,
        authority_ref=claims.authority_ref,
        change_reference=claims.change_reference,
        key_id=key.key_id,
        rotation_epoch=key.rotation_epoch,
        issued_at_utc=claims.issued_at_utc,
        effective_at_utc=claims.effective_at_utc,
        expires_at_utc=claims.expires_at_utc,
        verified_at_utc=expected.verified_at_utc,
    )


def _verify_signature(
    *,
    envelope: LifecycleAuthorityDecisionEnvelope,
    key: LifecycleAuthorityPublicKey,
    signature_verifier: LifecycleAuthoritySignatureVerifier,
) -> None:
    canonical_claims = _canonical_claim_values(envelope)
    _require(dict(envelope.canonical_claims) == canonical_claims, "canonical claim mapping")
    signature_verifier.verify(
        public_key_base64url=key.public_key_base64url,
        signature_base64url=envelope.signature.signature_base64url,
        canonical_payload=json.dumps(
            canonical_claims,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii"),
    )


def canonical_lifecycle_authority_claims(
    envelope: LifecycleAuthorityDecisionEnvelope,
) -> dict[str, object]:
    return _canonical_claim_values(envelope)


def _canonical_claim_values(envelope: LifecycleAuthorityDecisionEnvelope) -> dict[str, object]:
    claims = envelope.claims
    return {
        "schema_version": claims.schema_version,
        "issuer": claims.issuer,
        "audience": claims.audience,
        "decision_id": claims.decision_id,
        "replay_nonce": claims.replay_nonce,
        "tenant_id": claims.tenant_id,
        "candidate_id": claims.candidate_id,
        "action": claims.action.value,
        "authority_domain": claims.authority_domain.value,
        "authority_ref": claims.authority_ref,
        "change_reference": claims.change_reference,
        "decision_status": claims.decision_status,
        "issued_at_utc": _timestamp(claims.issued_at_utc),
        "effective_at_utc": _timestamp(claims.effective_at_utc),
        "expires_at_utc": _timestamp(claims.expires_at_utc),
    }


def _timestamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _require(condition: bool, label: str) -> None:
    if not condition:
        raise ValueError(f"lifecycle authority decision failed {label} verification")
