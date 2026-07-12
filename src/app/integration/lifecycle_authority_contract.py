from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field

from app.domain.data_lifecycle import DataLifecycleAction
from app.domain.data_lifecycle.authority import (
    LifecycleAuthorityDecisionClaims,
    LifecycleAuthorityDecisionEnvelope,
    LifecycleAuthorityDomain,
    LifecycleAuthorityKeyDiscovery,
    LifecycleAuthorityPublicKey,
    LifecycleAuthoritySignature,
)


class LifecycleAuthorityProducerClaims(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    issuer: str
    audience: str
    decision_id: str
    replay_nonce: str
    tenant_id: str
    candidate_id: str
    action: DataLifecycleAction
    authority_domain: LifecycleAuthorityDomain
    authority_ref: str
    change_reference: str
    decision_status: str
    issued_at_utc: datetime
    effective_at_utc: datetime
    expires_at_utc: datetime


class LifecycleAuthorityProducerSignature(BaseModel):
    model_config = ConfigDict(extra="forbid")

    algorithm: str
    key_id: str
    rotation_epoch: int
    signature_base64url: str


class LifecycleAuthorityProducerDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claims: LifecycleAuthorityProducerClaims
    signature: LifecycleAuthorityProducerSignature
    key_discovery_path: str

    def to_domain(self) -> LifecycleAuthorityDecisionEnvelope:
        raw = self.model_dump(mode="json")
        return LifecycleAuthorityDecisionEnvelope(
            claims=LifecycleAuthorityDecisionClaims(**self.claims.model_dump()),
            signature=LifecycleAuthoritySignature(**self.signature.model_dump()),
            key_discovery_path=self.key_discovery_path,
            canonical_claims=dict(raw["claims"]),
        )


class LifecycleAuthorityProducerPublicKey(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key_id: str
    algorithm: str
    curve: str
    public_key_base64url: str
    rotation_epoch: int
    status: str
    not_before_utc: datetime
    not_after_utc: datetime | None = None


class LifecycleAuthorityProducerKeyDiscovery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    issuer: str
    keys: tuple[LifecycleAuthorityProducerPublicKey, ...] = Field(min_length=1)

    def to_domain(self) -> LifecycleAuthorityKeyDiscovery:
        return LifecycleAuthorityKeyDiscovery(
            schema_version=self.schema_version,
            issuer=self.issuer,
            keys=tuple(LifecycleAuthorityPublicKey(**key.model_dump()) for key in self.keys),
        )


def map_lifecycle_authority_decision(
    payload: Mapping[str, Any],
) -> LifecycleAuthorityDecisionEnvelope:
    return LifecycleAuthorityProducerDecision.model_validate(payload).to_domain()


def map_lifecycle_authority_key_discovery(
    payload: Mapping[str, Any],
) -> LifecycleAuthorityKeyDiscovery:
    return LifecycleAuthorityProducerKeyDiscovery.model_validate(payload).to_domain()
