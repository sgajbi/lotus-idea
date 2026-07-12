from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.application.data_lifecycle.authority_verification import (
    canonical_lifecycle_authority_claims,
    verify_lifecycle_authority_decision,
)
from app.domain.data_lifecycle import DataLifecycleAction
from app.domain.data_lifecycle.authority import (
    LIFECYCLE_AUTHORITY_AUDIENCE,
    LIFECYCLE_AUTHORITY_ISSUER,
    LIFECYCLE_AUTHORITY_KEY_DISCOVERY_PATH,
    LIFECYCLE_AUTHORITY_KEY_SCHEMA_VERSION,
    LIFECYCLE_AUTHORITY_SCHEMA_VERSION,
    ExpectedLifecycleAuthorityDecision,
    LifecycleAuthorityDecisionClaims,
    LifecycleAuthorityDecisionEnvelope,
    LifecycleAuthorityDomain,
    LifecycleAuthorityKeyDiscovery,
    LifecycleAuthorityPublicKey,
    LifecycleAuthoritySignature,
    VerifiedLifecycleAuthorityReceipt,
    expected_authority_domain,
)


NOW = datetime(2026, 7, 12, 6, 0, tzinfo=UTC)


class RecordingSignatureVerifier:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[dict[str, object]] = []

    def verify(self, **values: object) -> None:
        self.calls.append(values)
        if self.fail:
            raise ValueError("signature rejected")


def claims() -> LifecycleAuthorityDecisionClaims:
    return LifecycleAuthorityDecisionClaims(
        schema_version=LIFECYCLE_AUTHORITY_SCHEMA_VERSION,
        issuer=LIFECYCLE_AUTHORITY_ISSUER,
        audience=LIFECYCLE_AUTHORITY_AUDIENCE,
        decision_id="privacy-decision-001",
        replay_nonce="a" * 64,
        tenant_id="tenant-private-bank-sg",
        candidate_id="candidate-expired-001",
        action=DataLifecycleAction.PURGE,
        authority_domain=LifecycleAuthorityDomain.PRIVACY,
        authority_ref="bank-privacy-governance:decision-001",
        change_reference="privacy-case-001",
        decision_status="approved",
        issued_at_utc=NOW - timedelta(minutes=2),
        effective_at_utc=NOW - timedelta(minutes=1),
        expires_at_utc=NOW + timedelta(minutes=5),
    )


def envelope(
    *, claims_value: LifecycleAuthorityDecisionClaims | None = None
) -> LifecycleAuthorityDecisionEnvelope:
    value = LifecycleAuthorityDecisionEnvelope(
        claims=claims_value or claims(),
        signature=LifecycleAuthoritySignature(
            algorithm="EdDSA",
            key_id="lifecycle-key-001",
            rotation_epoch=3,
            signature_base64url="c2lnbmF0dXJl",
        ),
        key_discovery_path=LIFECYCLE_AUTHORITY_KEY_DISCOVERY_PATH,
        canonical_claims={},
    )
    return replace(value, canonical_claims=canonical_lifecycle_authority_claims(value))


def key_discovery() -> LifecycleAuthorityKeyDiscovery:
    return LifecycleAuthorityKeyDiscovery(
        schema_version=LIFECYCLE_AUTHORITY_KEY_SCHEMA_VERSION,
        issuer=LIFECYCLE_AUTHORITY_ISSUER,
        keys=(
            LifecycleAuthorityPublicKey(
                key_id="lifecycle-key-001",
                algorithm="EdDSA",
                curve="Ed25519",
                public_key_base64url="cHVibGljLWtleQ",
                rotation_epoch=3,
                status="active",
                not_before_utc=NOW - timedelta(days=1),
                not_after_utc=NOW + timedelta(days=1),
            ),
        ),
    )


def expected() -> ExpectedLifecycleAuthorityDecision:
    value = claims()
    return ExpectedLifecycleAuthorityDecision(
        tenant_id=value.tenant_id,
        candidate_id=value.candidate_id,
        action=value.action,
        authority_ref=value.authority_ref,
        change_reference=value.change_reference,
        verified_at_utc=NOW,
    )


def test_lifecycle_authority_verification_binds_decision_and_signing_key() -> None:
    verifier = RecordingSignatureVerifier()

    receipt = verify_lifecycle_authority_decision(
        envelope=envelope(),
        key_discovery=key_discovery(),
        expected=expected(),
        signature_verifier=verifier,
    )

    assert receipt.decision_id == "privacy-decision-001"
    assert receipt.action is DataLifecycleAction.PURGE
    assert receipt.authority_domain is LifecycleAuthorityDomain.PRIVACY
    assert receipt.key_id == "lifecycle-key-001"
    assert receipt.rotation_epoch == 3
    assert len(verifier.calls) == 1
    assert verifier.calls[0]["public_key_base64url"] == "cHVibGljLWtleQ"
    canonical_payload = verifier.calls[0]["canonical_payload"]
    assert isinstance(canonical_payload, bytes)
    assert b'"candidate_id":"candidate-expired-001"' in canonical_payload


@pytest.mark.parametrize(
    ("expected_changes", "message"),
    [
        ({"tenant_id": "tenant-other"}, "tenant identity"),
        ({"candidate_id": "candidate-other"}, "candidate identity"),
        ({"action": DataLifecycleAction.ERASE}, "action"),
        ({"authority_ref": "bank-privacy-governance:other"}, "authority reference"),
        ({"change_reference": "privacy-case-other"}, "change reference"),
        ({"verified_at_utc": NOW + timedelta(minutes=6)}, "validity window"),
    ],
)
def test_lifecycle_authority_verification_rejects_request_substitution(
    expected_changes: dict[str, Any], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        verify_lifecycle_authority_decision(
            envelope=envelope(),
            key_discovery=key_discovery(),
            expected=replace(expected(), **expected_changes),
            signature_verifier=RecordingSignatureVerifier(),
        )


@pytest.mark.parametrize(
    ("claim_changes", "message"),
    [
        ({"schema_version": "lotus.lifecycle-authority-decision.v2"}, "schema version"),
        ({"issuer": "untrusted-issuer"}, "issuer"),
        ({"audience": "other-service"}, "audience"),
        ({"decision_status": "revoked"}, "decision status"),
        ({"authority_domain": LifecycleAuthorityDomain.LEGAL_AND_RECORDS}, "authority domain"),
    ],
)
def test_lifecycle_authority_verification_rejects_untrusted_claims(
    claim_changes: dict[str, Any], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        verify_lifecycle_authority_decision(
            envelope=envelope(claims_value=replace(claims(), **claim_changes)),
            key_discovery=key_discovery(),
            expected=expected(),
            signature_verifier=RecordingSignatureVerifier(),
        )


@pytest.mark.parametrize(
    ("key_changes", "message"),
    [
        ({"algorithm": "RS256"}, "signing key algorithm"),
        ({"status": "revoked"}, "signing key status"),
        ({"rotation_epoch": 4}, "rotation epoch"),
        ({"not_before_utc": NOW}, "key validity start"),
        ({"not_after_utc": NOW - timedelta(minutes=3)}, "key validity end"),
    ],
)
def test_lifecycle_authority_verification_rejects_untrusted_key_posture(
    key_changes: dict[str, Any], message: str
) -> None:
    discovery = key_discovery()
    changed_key = replace(discovery.keys[0], **key_changes)

    with pytest.raises(ValueError, match=message):
        verify_lifecycle_authority_decision(
            envelope=envelope(),
            key_discovery=replace(discovery, keys=(changed_key,)),
            expected=expected(),
            signature_verifier=RecordingSignatureVerifier(),
        )


def test_lifecycle_authority_verification_rejects_canonical_claim_tampering() -> None:
    value = envelope()
    tampered = dict(value.canonical_claims)
    tampered["candidate_id"] = "candidate-other"

    with pytest.raises(ValueError, match="canonical claim mapping"):
        verify_lifecycle_authority_decision(
            envelope=replace(value, canonical_claims=tampered),
            key_discovery=key_discovery(),
            expected=expected(),
            signature_verifier=RecordingSignatureVerifier(),
        )


def test_lifecycle_authority_verification_propagates_signature_failure() -> None:
    with pytest.raises(ValueError, match="signature rejected"):
        verify_lifecycle_authority_decision(
            envelope=envelope(),
            key_discovery=key_discovery(),
            expected=expected(),
            signature_verifier=RecordingSignatureVerifier(fail=True),
        )


@pytest.mark.parametrize(
    ("claim_changes", "message"),
    [
        ({"decision_id": ""}, "decision_id must be a source-safe reference"),
        ({"replay_nonce": "short"}, "replay_nonce must be a lowercase SHA-256 digest"),
        (
            {"issued_at_utc": datetime(2026, 7, 12, 5, 58)},
            "issued_at_utc must be timezone-aware UTC",
        ),
        (
            {"effective_at_utc": NOW + timedelta(minutes=6)},
            "validity window is invalid",
        ),
    ],
)
def test_lifecycle_authority_claims_reject_malformed_decisions(
    claim_changes: dict[str, Any], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        replace(claims(), **claim_changes)


@pytest.mark.parametrize(
    ("receipt_changes", "message"),
    [
        ({"decision_id": ""}, "decision_id must be a source-safe reference"),
        ({"replay_nonce": "short"}, "replay_nonce must be a lowercase SHA-256 digest"),
        ({"rotation_epoch": 0}, "rotation_epoch must be positive"),
        (
            {"effective_at_utc": NOW + timedelta(minutes=1)},
            "receipt is not yet effective",
        ),
        ({"expires_at_utc": NOW}, "receipt is expired"),
    ],
)
def test_verified_receipt_rejects_invalid_persistence_state(
    receipt_changes: dict[str, Any], message: str
) -> None:
    receipt = VerifiedLifecycleAuthorityReceipt(
        decision_id="privacy-decision-001",
        replay_nonce="a" * 64,
        tenant_id="tenant-private-bank-sg",
        candidate_id="candidate-expired-001",
        action=DataLifecycleAction.PURGE,
        authority_domain=LifecycleAuthorityDomain.PRIVACY,
        authority_ref="bank-privacy-governance:decision-001",
        change_reference="privacy-case-001",
        key_id="lifecycle-key-001",
        rotation_epoch=3,
        issued_at_utc=NOW - timedelta(minutes=2),
        effective_at_utc=NOW - timedelta(minutes=1),
        expires_at_utc=NOW + timedelta(minutes=5),
        verified_at_utc=NOW,
    )

    with pytest.raises(ValueError, match=message):
        replace(receipt, **receipt_changes)


@pytest.mark.parametrize(
    "action",
    [DataLifecycleAction.APPLY_HOLD, DataLifecycleAction.RELEASE_HOLD],
)
def test_legal_hold_actions_require_legal_and_records_authority(
    action: DataLifecycleAction,
) -> None:
    assert expected_authority_domain(action) is LifecycleAuthorityDomain.LEGAL_AND_RECORDS
