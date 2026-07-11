from __future__ import annotations

from datetime import datetime
import json
from typing import Protocol

from app.application.ed25519_key_trust import select_trusted_ed25519_key
from app.domain.lotus_ai_run_attestation import (
    ExpectedLotusAIRunAttestation,
    LotusAIAttestationKeyDiscovery,
    LotusAIAttestationPublicKey,
    LotusAIRunAttestationEnvelope,
    VerifiedLotusAIRunAttestationReceipt,
)


class LotusAIAttestationSignatureVerifier(Protocol):
    def verify(
        self,
        *,
        public_key_base64url: str,
        signature_base64url: str,
        canonical_payload: bytes,
    ) -> None: ...


def verify_lotus_ai_run_attestation(
    *,
    envelope: LotusAIRunAttestationEnvelope,
    key_discovery: LotusAIAttestationKeyDiscovery,
    expected: ExpectedLotusAIRunAttestation,
    signature_verifier: LotusAIAttestationSignatureVerifier,
) -> VerifiedLotusAIRunAttestationReceipt:
    claims = envelope.claims
    if expected.verified_at_utc.tzinfo is None or expected.verified_at_utc.utcoffset() is None:
        raise ValueError("attestation verification time must be timezone-aware")
    _require(claims.schema_version == "lotus-ai.workflow-run-attestation.v1", "schema version")
    _require(claims.issuer == "lotus-ai" == key_discovery.issuer, "issuer")
    _require(claims.audience == "lotus-idea", "audience")
    _require(claims.run_id == expected.run_id, "run identity")
    _require(claims.consumer_request_id == expected.consumer_request_id, "request identity")
    _require(claims.workflow_pack_id == "idea_explanation.pack", "workflow pack")
    _require(claims.workflow_pack_version == "v1", "workflow pack version")
    _require(claims.registration_ref == "idea_explanation.pack@v1", "registration")
    _require(claims.evaluator_id == "idea-explanation-guardrails", "evaluator")
    _require(claims.evaluator_policy_version == "idea-explanation-policy.v1", "evaluator policy")
    _require(claims.model_risk_status == "approved", "model-risk approval")
    _require(not claims.stubbed, "non-stub execution")
    _require(claims.supportability_status == "READY", "supportability")
    _require(claims.input_evidence_sha256 == expected.input_evidence_sha256, "input digest")
    _require(claims.output_content_sha256 == expected.output_content_sha256, "output digest")
    _require(
        claims.execution_started_at_utc
        <= claims.execution_completed_at_utc
        <= claims.issued_at_utc,
        "execution timestamps",
    )
    _require(
        claims.issued_at_utc <= expected.verified_at_utc < claims.expires_at_utc,
        "attestation validity window",
    )
    key = select_trusted_ed25519_key(
        signature=envelope.signature,
        keys=key_discovery.keys,
        issued_at_utc=claims.issued_at_utc,
        require=_require,
    )
    _verify_signature(envelope=envelope, key=key, signature_verifier=signature_verifier)
    return VerifiedLotusAIRunAttestationReceipt(
        run_id=claims.run_id,
        consumer_request_id=claims.consumer_request_id,
        replay_nonce=claims.replay_nonce,
        key_id=key.key_id,
        rotation_epoch=key.rotation_epoch,
        provider_id=claims.provider_id,
        provider_mode=claims.provider_mode,
        model_id=claims.model_id,
        model_version=claims.model_version,
        model_risk_approval_ref=claims.model_risk_approval_ref,
        evaluator_id=claims.evaluator_id,
        evaluator_policy_version=claims.evaluator_policy_version,
        input_evidence_sha256=claims.input_evidence_sha256,
        output_content_sha256=claims.output_content_sha256,
        issued_at_utc=claims.issued_at_utc,
        expires_at_utc=claims.expires_at_utc,
        verified_at_utc=expected.verified_at_utc,
    )


def _verify_signature(
    *,
    envelope: LotusAIRunAttestationEnvelope,
    key: LotusAIAttestationPublicKey,
    signature_verifier: LotusAIAttestationSignatureVerifier,
) -> None:
    claim_values = _canonical_claim_values(envelope)
    _require(dict(envelope.canonical_claims) == claim_values, "canonical claim mapping")
    canonical = json.dumps(
        claim_values,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    signature_verifier.verify(
        public_key_base64url=key.public_key_base64url,
        signature_base64url=envelope.signature.signature_base64url,
        canonical_payload=canonical,
    )


def _require(condition: bool, label: str) -> None:
    if not condition:
        raise ValueError(f"lotus-ai run attestation failed {label} verification")


def _canonical_claim_values(envelope: LotusAIRunAttestationEnvelope) -> dict[str, object]:
    claims = envelope.claims
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
        "issued_at_utc": _timestamp(claims.issued_at_utc),
        "execution_started_at_utc": _timestamp(claims.execution_started_at_utc),
        "execution_completed_at_utc": _timestamp(claims.execution_completed_at_utc),
        "expires_at_utc": _timestamp(claims.expires_at_utc),
        "stubbed": claims.stubbed,
        "supportability_status": claims.supportability_status,
    }


def _timestamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")
