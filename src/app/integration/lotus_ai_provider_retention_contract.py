from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict

from app.domain.ai_provider_retention import (
    AIProviderRetentionClaims,
    AIProviderRetentionEnvelope,
    AIProviderRetentionOutcome,
    AIProviderRetentionSignature,
)


class LotusAIProviderRetentionClaims(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    issuer: str
    audience: str
    recorded_by: str
    confirmation_id: str
    workflow_run_id: str
    workflow_pack_id: str
    tenant_id: str
    provider_id: str
    provider_mode: str
    model_id: str
    model_version: str
    provider_confirmation_ref: str
    retention_policy_id: str
    outcome: AIProviderRetentionOutcome
    provider_decision_at_utc: datetime
    evidence_sha256: str
    provider_failure_code: str | None = None
    deletion_confirmed: bool
    raw_prompt_included: bool
    raw_output_included: bool
    client_identifier_included: bool
    supportability_status: str
    issued_at_utc: datetime
    expires_at_utc: datetime
    replay_nonce: str


class LotusAIProviderRetentionSignature(BaseModel):
    model_config = ConfigDict(extra="forbid")

    algorithm: str
    key_id: str
    rotation_epoch: int
    signature_base64url: str


class LotusAIProviderRetentionConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claims: LotusAIProviderRetentionClaims
    signature: LotusAIProviderRetentionSignature
    key_discovery_path: str

    def to_domain(self) -> AIProviderRetentionEnvelope:
        raw = self.model_dump(mode="json")
        return AIProviderRetentionEnvelope(
            claims=AIProviderRetentionClaims(**self.claims.model_dump()),
            signature=AIProviderRetentionSignature(**self.signature.model_dump()),
            key_discovery_path=self.key_discovery_path,
            canonical_claims=dict(raw["claims"]),
        )


def map_lotus_ai_provider_retention_confirmation(
    payload: Mapping[str, Any],
) -> AIProviderRetentionEnvelope:
    return LotusAIProviderRetentionConfirmation.model_validate(payload).to_domain()
