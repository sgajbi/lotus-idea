from __future__ import annotations

from datetime import datetime
import json

from app.application.ed25519_key_trust import select_trusted_ed25519_key
from app.application.lotus_ai_run_attestation_verification import (
    LotusAIAttestationSignatureVerifier,
)
from app.domain.ai_provider_retention import (
    AI_PROVIDER_RETENTION_KEY_DISCOVERY_PATH,
    AI_PROVIDER_RETENTION_SCHEMA_VERSION,
    AIProviderRetentionEnvelope,
    AIProviderRetentionOutcome,
    ExpectedAIProviderRetention,
    VerifiedAIProviderRetentionReceipt,
)
from app.domain.lotus_ai_run_attestation import LotusAIAttestationKeyDiscovery


def verify_ai_provider_retention_confirmation(
    *,
    envelope: AIProviderRetentionEnvelope,
    key_discovery: LotusAIAttestationKeyDiscovery,
    expected: ExpectedAIProviderRetention,
    signature_verifier: LotusAIAttestationSignatureVerifier,
) -> VerifiedAIProviderRetentionReceipt:
    claims = envelope.claims
    _require(claims.schema_version == AI_PROVIDER_RETENTION_SCHEMA_VERSION, "schema version")
    _require(claims.issuer == key_discovery.issuer == "lotus-ai", "issuer")
    _require(claims.audience == "lotus-idea", "audience")
    _require(claims.recorded_by == "lotus-ai-provider-operations", "recorder")
    _require(envelope.key_discovery_path == AI_PROVIDER_RETENTION_KEY_DISCOVERY_PATH, "key path")
    _require(claims.workflow_pack_id == "idea_explanation.pack", "workflow pack")
    _require(claims.workflow_run_id == expected.workflow_run_id, "workflow run")
    _require(claims.tenant_id == expected.tenant_id, "tenant")
    _require(claims.provider_id == expected.provider_id, "provider")
    _require(claims.provider_mode == expected.provider_mode, "provider mode")
    _require(claims.model_id == expected.model_id, "model")
    _require(claims.model_version == expected.model_version, "model version")
    _require(
        not claims.raw_prompt_included
        and not claims.raw_output_included
        and not claims.client_identifier_included,
        "source safety",
    )
    if claims.outcome is AIProviderRetentionOutcome.PROVIDER_FAILURE:
        _require(claims.provider_failure_code is not None, "provider failure code")
        _require(not claims.deletion_confirmed, "provider failure deletion posture")
        _require(claims.supportability_status == "BLOCKED", "provider failure supportability")
    else:
        _require(claims.provider_failure_code is None, "provider failure code absence")
        _require(
            claims.deletion_confirmed
            is (claims.outcome is AIProviderRetentionOutcome.DELETION_CONFIRMED),
            "deletion posture",
        )
        _require(claims.supportability_status == "READY", "supportability")
    _require(
        claims.issued_at_utc <= expected.verified_at_utc < claims.expires_at_utc,
        "validity window",
    )
    key = select_trusted_ed25519_key(
        signature=envelope.signature,
        keys=key_discovery.keys,
        issued_at_utc=claims.issued_at_utc,
        require=_require,
    )
    canonical = _canonical_claim_values(envelope)
    _require(dict(envelope.canonical_claims) == canonical, "canonical claim mapping")
    signature_verifier.verify(
        public_key_base64url=key.public_key_base64url,
        signature_base64url=envelope.signature.signature_base64url,
        canonical_payload=json.dumps(
            canonical,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii"),
    )
    return VerifiedAIProviderRetentionReceipt(
        confirmation_id=claims.confirmation_id,
        workflow_run_id=claims.workflow_run_id,
        tenant_id=claims.tenant_id,
        provider_confirmation_ref=claims.provider_confirmation_ref,
        retention_policy_id=claims.retention_policy_id,
        outcome=claims.outcome,
        evidence_sha256=claims.evidence_sha256,
        provider_failure_code=claims.provider_failure_code,
        deletion_confirmed=claims.deletion_confirmed,
        supportability_status=claims.supportability_status,
        replay_nonce=claims.replay_nonce,
        key_id=key.key_id,
        rotation_epoch=key.rotation_epoch,
        provider_decision_at_utc=claims.provider_decision_at_utc,
        issued_at_utc=claims.issued_at_utc,
        expires_at_utc=claims.expires_at_utc,
        verified_at_utc=expected.verified_at_utc,
    )


def _canonical_claim_values(envelope: AIProviderRetentionEnvelope) -> dict[str, object]:
    claims = envelope.claims
    return {
        "schema_version": claims.schema_version,
        "issuer": claims.issuer,
        "audience": claims.audience,
        "recorded_by": claims.recorded_by,
        "confirmation_id": claims.confirmation_id,
        "workflow_run_id": claims.workflow_run_id,
        "workflow_pack_id": claims.workflow_pack_id,
        "tenant_id": claims.tenant_id,
        "provider_id": claims.provider_id,
        "provider_mode": claims.provider_mode,
        "model_id": claims.model_id,
        "model_version": claims.model_version,
        "provider_confirmation_ref": claims.provider_confirmation_ref,
        "retention_policy_id": claims.retention_policy_id,
        "outcome": claims.outcome.value,
        "provider_decision_at_utc": _timestamp(claims.provider_decision_at_utc),
        "evidence_sha256": claims.evidence_sha256,
        "provider_failure_code": claims.provider_failure_code,
        "deletion_confirmed": claims.deletion_confirmed,
        "raw_prompt_included": claims.raw_prompt_included,
        "raw_output_included": claims.raw_output_included,
        "client_identifier_included": claims.client_identifier_included,
        "supportability_status": claims.supportability_status,
        "issued_at_utc": _timestamp(claims.issued_at_utc),
        "expires_at_utc": _timestamp(claims.expires_at_utc),
        "replay_nonce": claims.replay_nonce,
    }


def _timestamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _require(condition: bool, label: str) -> None:
    if not condition:
        raise ValueError(f"lotus-ai provider retention failed {label} verification")
