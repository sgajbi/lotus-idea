from __future__ import annotations

import base64
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import json
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.application.ai_provider_retention_verification import (
    verify_ai_provider_retention_confirmation,
)
from app.domain.ai_provider_retention import (
    ExpectedAIProviderRetention,
    VerifiedAIProviderRetentionReceipt,
)
from app.domain.ai_provider_retention_replay import AIProviderRetentionReplayIndex
from app.domain.lotus_ai_run_attestation import (
    LotusAIAttestationKeyDiscovery,
    LotusAIAttestationPublicKey,
)
from app.infrastructure.ed25519_lotus_ai_attestation_verifier import (
    Ed25519LotusAIAttestationSignatureVerifier,
)
from app.integration.lotus_ai_provider_retention_contract import (
    map_lotus_ai_provider_retention_confirmation,
)


NOW = datetime(2026, 7, 12, 4, 0, tzinfo=UTC)
PRIVATE_KEY = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))


def test_verifies_source_safe_deletion_confirmation_against_run_and_tenant() -> None:
    receipt = _verify(_signed_payload())

    assert receipt.workflow_run_id == "packrun_idea_explanation_request-001"
    assert receipt.tenant_id == "tenant-sg-001"
    assert receipt.outcome == "DELETION_CONFIRMED"
    assert receipt.deletion_confirmed is True
    assert receipt.supportability_status == "READY"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("tenant_id", "tenant-other", "tenant"),
        ("workflow_run_id", "packrun-other", "workflow run"),
        ("provider_id", "text.other", "provider"),
        ("model_id", "other-model", "model"),
        ("raw_prompt_included", True, "source safety"),
        ("client_identifier_included", True, "source safety"),
    ],
)
def test_rejects_substituted_identity_or_sensitive_content(
    field: str,
    value: Any,
    message: str,
) -> None:
    payload = _payload()
    payload["claims"][field] = value

    with pytest.raises(ValueError, match=message):
        _verify(_signed_payload(payload))


def test_provider_failure_cannot_be_presented_as_deletion_proof() -> None:
    payload = _payload()
    payload["claims"].update(
        {
            "outcome": "PROVIDER_FAILURE",
            "provider_failure_code": "PROVIDER_TIMEOUT",
            "deletion_confirmed": True,
            "supportability_status": "BLOCKED",
        }
    )

    with pytest.raises(ValueError, match="provider failure deletion posture"):
        _verify(_signed_payload(payload))


def test_rejects_expired_revoked_and_canonically_tampered_confirmation() -> None:
    with pytest.raises(ValueError, match="validity window"):
        _verify(_signed_payload(), verified_at=NOW + timedelta(minutes=6))
    with pytest.raises(ValueError, match="signing key status"):
        _verify(_signed_payload(), key_status="revoked")

    envelope = map_lotus_ai_provider_retention_confirmation(_signed_payload())
    tampered = envelope.__class__(
        claims=envelope.claims,
        signature=envelope.signature,
        key_discovery_path=envelope.key_discovery_path,
        canonical_claims={**envelope.canonical_claims, "retention_policy_id": "tampered-policy"},
    )
    with pytest.raises(ValueError, match="canonical claim mapping"):
        verify_ai_provider_retention_confirmation(
            envelope=tampered,
            key_discovery=_key_discovery(),
            expected=_expected(NOW),
            signature_verifier=Ed25519LotusAIAttestationSignatureVerifier(),
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("confirmation_id", "unsafe reference", "source-safe reference"),
        ("provider_failure_code", "unsafe code", "source-safe reference"),
        ("evidence_sha256", "not-a-digest", "lowercase SHA-256"),
        ("replay_nonce", "A" * 64, "lowercase SHA-256"),
        ("issued_at_utc", datetime(2026, 7, 12, 4, 0), "timezone-aware UTC"),
        ("expires_at_utc", NOW, "validity window"),
    ],
)
def test_claims_reject_unsafe_or_temporally_invalid_provider_evidence(
    field: str,
    value: Any,
    message: str,
) -> None:
    claims = map_lotus_ai_provider_retention_confirmation(_signed_payload()).claims

    with pytest.raises(ValueError, match=message):
        replace(claims, **{field: value})


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("confirmation_id", "unsafe reference", "source-safe reference"),
        ("evidence_sha256", "not-a-digest", "lowercase SHA-256"),
        ("rotation_epoch", 0, "rotation_epoch must be positive"),
        ("verified_at_utc", datetime(2026, 7, 12, 4, 0), "timezone-aware UTC"),
        ("verified_at_utc", NOW + timedelta(minutes=6), "outside its validity window"),
    ],
)
def test_verified_receipt_rejects_invalid_persisted_identity_or_time(
    field: str,
    value: Any,
    message: str,
) -> None:
    receipt = _verify(_signed_payload())

    with pytest.raises(ValueError, match=message):
        replace(receipt, **{field: value})


def test_replay_snapshot_restore_rejects_identity_reuse_across_requests() -> None:
    receipt = _verify(_signed_payload())
    index = AIProviderRetentionReplayIndex()

    with pytest.raises(ValueError, match="duplicate AI provider retention identity"):
        index.restore((("request-001", receipt), ("request-002", receipt)))


def test_provider_failure_requires_blocked_supportability() -> None:
    payload = _payload()
    payload["claims"].update(
        {
            "outcome": "PROVIDER_FAILURE",
            "provider_failure_code": "PROVIDER_TIMEOUT",
            "deletion_confirmed": False,
            "supportability_status": "READY",
        }
    )

    with pytest.raises(ValueError, match="provider failure supportability"):
        _verify(_signed_payload(payload))


def _verify(
    payload: dict[str, Any],
    *,
    verified_at: datetime = NOW,
    key_status: str = "active",
) -> VerifiedAIProviderRetentionReceipt:
    return verify_ai_provider_retention_confirmation(
        envelope=map_lotus_ai_provider_retention_confirmation(payload),
        key_discovery=_key_discovery(status=key_status),
        expected=_expected(verified_at),
        signature_verifier=Ed25519LotusAIAttestationSignatureVerifier(),
    )


def _expected(verified_at: datetime) -> ExpectedAIProviderRetention:
    return ExpectedAIProviderRetention(
        workflow_run_id="packrun_idea_explanation_request-001",
        tenant_id="tenant-sg-001",
        provider_id="text.openai",
        provider_mode="openai",
        model_id="gpt-5.4",
        model_version="2026-06-01",
        verified_at_utc=verified_at,
    )


def _signed_payload(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    result = deepcopy(payload or _payload())
    canonical = json.dumps(
        result["claims"],
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    result["signature"]["signature_base64url"] = (
        base64.urlsafe_b64encode(PRIVATE_KEY.sign(canonical)).rstrip(b"=").decode("ascii")
    )
    return result


def _payload() -> dict[str, Any]:
    return {
        "claims": {
            "schema_version": "lotus-ai.provider-retention-confirmation.v1",
            "issuer": "lotus-ai",
            "audience": "lotus-idea",
            "recorded_by": "lotus-ai-provider-operations",
            "confirmation_id": "provider_retention_001",
            "workflow_run_id": "packrun_idea_explanation_request-001",
            "workflow_pack_id": "idea_explanation.pack",
            "tenant_id": "tenant-sg-001",
            "provider_id": "text.openai",
            "provider_mode": "openai",
            "model_id": "gpt-5.4",
            "model_version": "2026-06-01",
            "provider_confirmation_ref": "provider-confirmation-001",
            "retention_policy_id": "idea-provider-zero-retention-v1",
            "outcome": "DELETION_CONFIRMED",
            "provider_decision_at_utc": "2026-07-12T03:59:00Z",
            "evidence_sha256": "e" * 64,
            "provider_failure_code": None,
            "deletion_confirmed": True,
            "raw_prompt_included": False,
            "raw_output_included": False,
            "client_identifier_included": False,
            "supportability_status": "READY",
            "issued_at_utc": "2026-07-12T04:00:00Z",
            "expires_at_utc": "2026-07-12T04:05:00Z",
            "replay_nonce": "a" * 64,
        },
        "signature": {
            "algorithm": "EdDSA",
            "key_id": "workflow-attestation-2026-07",
            "rotation_epoch": 2,
            "signature_base64url": "pending",
        },
        "key_discovery_path": "/.well-known/lotus-ai-workflow-attestation-keys",
    }


def _key_discovery(status: str = "active") -> LotusAIAttestationKeyDiscovery:
    return LotusAIAttestationKeyDiscovery(
        schema_version="lotus-ai.workflow-run-attestation-keys.v1",
        issuer="lotus-ai",
        keys=(
            LotusAIAttestationPublicKey(
                key_id="workflow-attestation-2026-07",
                algorithm="EdDSA",
                curve="Ed25519",
                public_key_base64url=base64.urlsafe_b64encode(
                    PRIVATE_KEY.public_key().public_bytes_raw()
                )
                .rstrip(b"=")
                .decode("ascii"),
                rotation_epoch=2,
                status=status,
                not_before_utc=NOW - timedelta(days=1),
                not_after_utc=NOW + timedelta(days=30),
            ),
        ),
    )
