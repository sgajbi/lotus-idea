from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.data_lifecycle.archive_posture import (
    ArchiveLegalHoldStatus,
    ArchiveLifecycleAction,
    ArchiveLifecycleDecisionClaims,
    ArchiveLifecycleDecisionEnvelope,
    ArchiveLifecycleKeyAlgorithm,
    ArchiveLifecycleKeyProvenance,
    ArchiveLifecycleKeyStatus,
    ArchiveLifecycleTrustedKey,
    ArchivePurgeStatus,
)


class ArchiveLifecycleProducerDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str
    decision_id: str
    document_id: str
    idea_evidence_pack_id: str
    idea_candidate_id: str
    source_correlation_ref: str
    tenant_id: str
    residency_region: str
    retention_policy_id: str
    legal_hold_status: ArchiveLegalHoldStatus
    legal_hold_count: int
    purge_status: ArchivePurgeStatus
    lifecycle_action: ArchiveLifecycleAction
    disposal_authorized: bool
    decision_reason_code: str
    authority: str
    issued_at_utc: datetime
    expires_at_utc: datetime
    correlation_id: str
    trace_id: str
    signing_algorithm: str
    signing_key_id: str
    payload_digest: str
    signature: str

    def to_domain(self) -> ArchiveLifecycleDecisionEnvelope:
        raw = self.model_dump(mode="json")
        canonical = {
            key: value for key, value in raw.items() if key not in {"payload_digest", "signature"}
        }
        return ArchiveLifecycleDecisionEnvelope(
            claims=ArchiveLifecycleDecisionClaims(
                **self.model_dump(exclude={"payload_digest", "signature"})
            ),
            payload_digest=self.payload_digest,
            signature=self.signature,
            canonical_claims=canonical,
        )


def map_archive_lifecycle_decision(
    payload: Mapping[str, Any],
) -> ArchiveLifecycleDecisionEnvelope:
    return ArchiveLifecycleProducerDecision.model_validate(payload).to_domain()


class ArchiveLifecycleTrustedKeyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key_id: str
    algorithm: ArchiveLifecycleKeyAlgorithm
    public_key_base64: str
    provenance: ArchiveLifecycleKeyProvenance
    status: ArchiveLifecycleKeyStatus
    not_before_utc: datetime
    not_after_utc: datetime | None = None

    def to_domain(self) -> ArchiveLifecycleTrustedKey:
        values = self.model_dump(exclude={"public_key_base64"})
        return ArchiveLifecycleTrustedKey(
            **values,
            public_key_base64url=self.public_key_base64,
        )


class ArchiveLifecycleTrustBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    keys: tuple[ArchiveLifecycleTrustedKeyConfig, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_key_ids(self) -> Self:
        key_ids = tuple(key.key_id for key in self.keys)
        if len(key_ids) != len(set(key_ids)):
            raise ValueError("Archive lifecycle trust bundle key IDs must be unique")
        active_key_count = sum(key.status is ArchiveLifecycleKeyStatus.ACTIVE for key in self.keys)
        if active_key_count != 1:
            raise ValueError("Archive lifecycle trust bundle must contain exactly one active key")
        return self

    def to_domain(self) -> tuple[ArchiveLifecycleTrustedKey, ...]:
        return tuple(key.to_domain() for key in self.keys)


def map_archive_lifecycle_trust_bundle(payload: object) -> tuple[ArchiveLifecycleTrustedKey, ...]:
    return ArchiveLifecycleTrustBundle.model_validate(payload).to_domain()
