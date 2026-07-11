from __future__ import annotations

import base64
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.application.lotus_ai_run_attestation_verification import (
    verify_lotus_ai_run_attestation,
)
from app.domain.lotus_ai_run_attestation import (
    ExpectedLotusAIRunAttestation,
    LotusAIAttestationKeyDiscovery,
    LotusAIAttestationPublicKey,
    LotusAIRunAttestationClaims,
    LotusAIRunAttestationEnvelope,
    LotusAIRunAttestationSignature,
)
from app.infrastructure.ed25519_lotus_ai_attestation_verifier import (
    Ed25519LotusAIAttestationSignatureVerifier,
)


NOW = datetime(2026, 7, 11, 10, 5, tzinfo=UTC)
SIGNATURE_VERIFIER = Ed25519LotusAIAttestationSignatureVerifier()


def _claims(**overrides: object) -> LotusAIRunAttestationClaims:
    values: dict[str, object] = {
        "schema_version": "lotus-ai.workflow-run-attestation.v1",
        "issuer": "lotus-ai",
        "audience": "lotus-idea",
        "run_id": "packrun_idea_explanation_request-001",
        "consumer_request_id": "request-001",
        "replay_nonce": "a" * 64,
        "workflow_pack_id": "idea_explanation.pack",
        "workflow_pack_version": "v1",
        "registration_ref": "idea_explanation.pack@v1",
        "evaluator_id": "idea-explanation-guardrails",
        "evaluator_policy_version": "idea-explanation-policy.v1",
        "provider_id": "text.openai",
        "provider_mode": "openai",
        "model_id": "gpt-5.4",
        "model_version": "2026-06-01",
        "model_risk_status": "approved",
        "model_risk_approval_ref": "model-risk://lotus-ai/gpt-5.4/2026-06-01",
        "input_evidence_sha256": "b" * 64,
        "output_content_sha256": "c" * 64,
        "issued_at_utc": NOW - timedelta(seconds=5),
        "execution_started_at_utc": NOW - timedelta(seconds=10),
        "execution_completed_at_utc": NOW - timedelta(seconds=6),
        "expires_at_utc": NOW + timedelta(minutes=5),
        "stubbed": False,
        "supportability_status": "READY",
    }
    values.update(overrides)
    return LotusAIRunAttestationClaims(**values)  # type: ignore[arg-type]


def _mapping(claims: LotusAIRunAttestationClaims) -> dict[str, object]:
    return {
        "schema_version": claims.schema_version,
        "issuer": claims.issuer,
        "audience": claims.audience,
        "run_id": claims.run_id,
        "consumer_request_id": claims.consumer_request_id,
        "replay_nonce": claims.replay_nonce,
        "workflow_pack_id": claims.workflow_pack_id,
        "workflow_pack_version": claims.workflow_pack_version,
        "registration_ref": claims.registration_ref,
        "evaluator_id": claims.evaluator_id,
        "evaluator_policy_version": claims.evaluator_policy_version,
        "provider_id": claims.provider_id,
        "provider_mode": claims.provider_mode,
        "model_id": claims.model_id,
        "model_version": claims.model_version,
        "model_risk_status": claims.model_risk_status,
        "model_risk_approval_ref": claims.model_risk_approval_ref,
        "input_evidence_sha256": claims.input_evidence_sha256,
        "output_content_sha256": claims.output_content_sha256,
        "issued_at_utc": claims.issued_at_utc.isoformat().replace("+00:00", "Z"),
        "execution_started_at_utc": claims.execution_started_at_utc.isoformat().replace(
            "+00:00", "Z"
        ),
        "execution_completed_at_utc": claims.execution_completed_at_utc.isoformat().replace(
            "+00:00", "Z"
        ),
        "expires_at_utc": claims.expires_at_utc.isoformat().replace("+00:00", "Z"),
        "stubbed": claims.stubbed,
        "supportability_status": claims.supportability_status,
    }


def _fixture(
    *, claims: LotusAIRunAttestationClaims | None = None, key_status: str = "active"
) -> tuple[LotusAIRunAttestationEnvelope, LotusAIAttestationKeyDiscovery]:
    claims = claims or _claims()
    private_key = Ed25519PrivateKey.generate()
    mapping = _mapping(claims)
    canonical = json.dumps(
        mapping, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("ascii")
    signature = _encode(private_key.sign(canonical))
    envelope = LotusAIRunAttestationEnvelope(
        claims=claims,
        signature=LotusAIRunAttestationSignature(
            algorithm="EdDSA",
            key_id="attestation-key-1",
            rotation_epoch=1,
            signature_base64url=signature,
        ),
        key_discovery_path="/.well-known/lotus-ai-workflow-attestation-keys",
        canonical_claims=mapping,
    )
    discovery = LotusAIAttestationKeyDiscovery(
        schema_version="lotus-ai.workflow-run-attestation-keys.v1",
        issuer="lotus-ai",
        keys=(
            LotusAIAttestationPublicKey(
                key_id="attestation-key-1",
                algorithm="EdDSA",
                curve="Ed25519",
                public_key_base64url=_encode(private_key.public_key().public_bytes_raw()),
                rotation_epoch=1,
                status=key_status,
                not_before_utc=NOW - timedelta(days=1),
                not_after_utc=NOW + timedelta(days=1),
            ),
        ),
    )
    return envelope, discovery


def _expected(**overrides: object) -> ExpectedLotusAIRunAttestation:
    values: dict[str, object] = {
        "run_id": "packrun_idea_explanation_request-001",
        "consumer_request_id": "request-001",
        "input_evidence_sha256": "b" * 64,
        "output_content_sha256": "c" * 64,
        "verified_at_utc": NOW,
    }
    values.update(overrides)
    return ExpectedLotusAIRunAttestation(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("key_status", ["active", "rotated"])
def test_verifies_exact_active_and_rotated_lotus_ai_attestation(key_status: str) -> None:
    envelope, discovery = _fixture(key_status=key_status)

    receipt = verify_lotus_ai_run_attestation(
        envelope=envelope,
        key_discovery=discovery,
        expected=_expected(),
        signature_verifier=SIGNATURE_VERIFIER,
    )

    assert receipt.run_id == "packrun_idea_explanation_request-001"
    assert receipt.consumer_request_id == "request-001"
    assert receipt.model_risk_approval_ref.endswith("/2026-06-01")
    assert receipt.key_id == "attestation-key-1"


@pytest.mark.parametrize(
    ("expected", "message"),
    [
        (_expected(run_id="other-run"), "run identity"),
        (_expected(consumer_request_id="other-request"), "request identity"),
        (_expected(input_evidence_sha256="d" * 64), "input digest"),
        (_expected(output_content_sha256="d" * 64), "output digest"),
    ],
)
def test_rejects_expected_binding_mismatch(
    expected: ExpectedLotusAIRunAttestation, message: str
) -> None:
    envelope, discovery = _fixture()

    with pytest.raises(ValueError, match=message):
        verify_lotus_ai_run_attestation(
            envelope=envelope,
            key_discovery=discovery,
            expected=expected,
            signature_verifier=SIGNATURE_VERIFIER,
        )


@pytest.mark.parametrize(
    ("claims", "message"),
    [
        (_claims(issuer="other-service"), "issuer"),
        (_claims(audience="other-consumer"), "audience"),
        (_claims(workflow_pack_id="other.pack"), "workflow pack"),
        (_claims(model_risk_status="approval_unverified"), "model-risk"),
        (_claims(stubbed=True), "non-stub"),
        (_claims(expires_at_utc=NOW), "validity window"),
    ],
)
def test_rejects_non_certifying_claims(claims: LotusAIRunAttestationClaims, message: str) -> None:
    envelope, discovery = _fixture(claims=claims)

    with pytest.raises(ValueError, match=message):
        verify_lotus_ai_run_attestation(
            envelope=envelope,
            key_discovery=discovery,
            expected=_expected(),
            signature_verifier=SIGNATURE_VERIFIER,
        )


@pytest.mark.parametrize("key_status", ["revoked", "unknown"])
def test_rejects_untrusted_key_status_or_identity(key_status: str) -> None:
    envelope, discovery = _fixture(key_status="revoked" if key_status == "revoked" else "active")
    if key_status == "unknown":
        discovery = replace(
            discovery,
            keys=(replace(discovery.keys[0], key_id="other-key"),),
        )

    with pytest.raises(ValueError):
        verify_lotus_ai_run_attestation(
            envelope=envelope,
            key_discovery=discovery,
            expected=_expected(),
            signature_verifier=SIGNATURE_VERIFIER,
        )


def test_rejects_signature_tampering_and_claim_mapping_divergence() -> None:
    envelope, discovery = _fixture()
    tampered_signature = replace(
        envelope,
        signature=replace(envelope.signature, signature_base64url=_encode(b"tampered")),
    )
    with pytest.raises(ValueError, match="signature"):
        verify_lotus_ai_run_attestation(
            envelope=tampered_signature,
            key_discovery=discovery,
            expected=_expected(),
            signature_verifier=SIGNATURE_VERIFIER,
        )

    divergent_mapping = replace(
        envelope,
        canonical_claims={**envelope.canonical_claims, "model_id": "other-model"},
    )
    with pytest.raises(ValueError, match="canonical claim mapping"):
        verify_lotus_ai_run_attestation(
            envelope=divergent_mapping,
            key_discovery=discovery,
            expected=_expected(),
            signature_verifier=SIGNATURE_VERIFIER,
        )


def test_claims_reject_incomplete_identity_digest_and_time() -> None:
    with pytest.raises(ValueError, match="provider_id is required"):
        _claims(provider_id=" ")
    with pytest.raises(ValueError, match="replay_nonce must be"):
        _claims(replay_nonce="not-a-digest")
    with pytest.raises(ValueError, match="issued_at_utc must be timezone-aware"):
        _claims(issued_at_utc=NOW.replace(tzinfo=None))


def test_verified_receipt_rejects_invalid_persisted_identity_and_validity() -> None:
    envelope, discovery = _fixture()
    receipt = verify_lotus_ai_run_attestation(
        envelope=envelope,
        key_discovery=discovery,
        expected=_expected(),
        signature_verifier=SIGNATURE_VERIFIER,
    )

    with pytest.raises(ValueError, match="run_id is required"):
        replace(receipt, run_id=" ")
    with pytest.raises(ValueError, match="rotation_epoch must be positive"):
        replace(receipt, rotation_epoch=0)
    with pytest.raises(ValueError, match="replay_nonce must be"):
        replace(receipt, replay_nonce="not-a-digest")
    with pytest.raises(ValueError, match="verified_at_utc must be timezone-aware"):
        replace(receipt, verified_at_utc=NOW.replace(tzinfo=None))
    with pytest.raises(ValueError, match="validity window"):
        replace(receipt, verified_at_utc=receipt.expires_at_utc)


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")
