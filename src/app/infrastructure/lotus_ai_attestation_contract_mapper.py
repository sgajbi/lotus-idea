from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field

from app.domain.lotus_ai_run_attestation import (
    LotusAIAttestationKeyDiscovery,
    LotusAIAttestationPublicKey,
    LotusAIRunAttestationClaims,
    LotusAIRunAttestationEnvelope,
    LotusAIRunAttestationSignature,
)


class _ProducerClaims(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    issuer: str
    audience: str
    run_id: str
    consumer_request_id: str
    replay_nonce: str
    workflow_pack_id: str
    workflow_pack_version: str
    registration_ref: str
    evaluator_id: str
    evaluator_policy_version: str
    provider_id: str
    provider_mode: str
    model_id: str
    model_version: str
    model_risk_status: str
    model_risk_approval_ref: str
    input_evidence_sha256: str
    output_content_sha256: str
    issued_at_utc: datetime
    execution_started_at_utc: datetime
    execution_completed_at_utc: datetime
    expires_at_utc: datetime
    stubbed: bool
    supportability_status: str


class _ProducerSignature(BaseModel):
    model_config = ConfigDict(extra="forbid")

    algorithm: str
    key_id: str
    rotation_epoch: int
    signature_base64url: str


class _ProducerEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claims: _ProducerClaims
    signature: _ProducerSignature
    key_discovery_path: str


class _ProducerPublicKey(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key_id: str
    algorithm: str
    curve: str
    public_key_base64url: str
    rotation_epoch: int
    status: str
    not_before_utc: datetime
    not_after_utc: datetime | None = None


class _ProducerKeyDiscovery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    issuer: str
    keys: tuple[_ProducerPublicKey, ...] = Field(min_length=1)


def map_lotus_ai_run_attestation(
    payload: Mapping[str, Any],
) -> LotusAIRunAttestationEnvelope:
    parsed = _ProducerEnvelope.model_validate(payload)
    raw_claims = payload.get("claims")
    if not isinstance(raw_claims, Mapping):
        raise ValueError("lotus-ai run attestation claims must be an object")
    claims = parsed.claims
    signature = parsed.signature
    return LotusAIRunAttestationEnvelope(
        claims=LotusAIRunAttestationClaims(**claims.model_dump()),
        signature=LotusAIRunAttestationSignature(**signature.model_dump()),
        key_discovery_path=parsed.key_discovery_path,
        canonical_claims=dict(raw_claims),
    )


def map_lotus_ai_attestation_key_discovery(
    payload: Mapping[str, Any],
) -> LotusAIAttestationKeyDiscovery:
    parsed = _ProducerKeyDiscovery.model_validate(payload)
    return LotusAIAttestationKeyDiscovery(
        schema_version=parsed.schema_version,
        issuer=parsed.issuer,
        keys=tuple(LotusAIAttestationPublicKey(**key.model_dump()) for key in parsed.keys),
    )
