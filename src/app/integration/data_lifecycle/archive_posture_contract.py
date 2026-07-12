from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field

from app.domain.data_lifecycle.archive_posture import (
    ArchiveLegalHoldStatus,
    ArchiveLifecycleAction,
    ArchiveLifecycleDecisionClaims,
    ArchiveLifecycleDecisionEnvelope,
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
    public_key_base64url: str
    status: str
    not_before_utc: datetime
    not_after_utc: datetime | None = None

    def to_domain(self) -> ArchiveLifecycleTrustedKey:
        return ArchiveLifecycleTrustedKey(**self.model_dump())


class ArchiveLifecycleTrustBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["lotus-idea.archive-lifecycle-trust-bundle.v1"]
    keys: tuple[ArchiveLifecycleTrustedKeyConfig, ...] = Field(min_length=1)

    def to_domain(self) -> tuple[ArchiveLifecycleTrustedKey, ...]:
        return tuple(key.to_domain() for key in self.keys)


def map_archive_lifecycle_trust_bundle(payload: object) -> tuple[ArchiveLifecycleTrustedKey, ...]:
    return ArchiveLifecycleTrustBundle.model_validate(payload).to_domain()
