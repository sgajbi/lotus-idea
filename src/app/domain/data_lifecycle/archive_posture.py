from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
import re
from typing import Mapping


ARCHIVE_LIFECYCLE_SCHEMA_VERSION = "lotus-archive:IdeaEvidenceLifecycleDecision:v1"

_REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{2,255}$")
_REGION = re.compile(r"^[A-Z]{2,16}$")
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")


class ArchiveLifecycleAction(StrEnum):
    RETAIN = "RETAIN"
    LEGAL_HOLD = "LEGAL_HOLD"
    DISPOSAL_ELIGIBLE = "DISPOSAL_ELIGIBLE"
    DISPOSAL_EXECUTED = "DISPOSAL_EXECUTED"


class ArchiveLegalHoldStatus(StrEnum):
    CLEAR = "clear"
    ACTIVE = "active"


class ArchivePurgeStatus(StrEnum):
    NOT_ELIGIBLE = "not_eligible"
    ELIGIBLE = "eligible"
    PURGED = "purged"


@dataclass(frozen=True)
class ArchiveLifecycleDecisionClaims:
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

    def __post_init__(self) -> None:
        for field_name in (
            "contract_version",
            "decision_id",
            "document_id",
            "idea_evidence_pack_id",
            "idea_candidate_id",
            "source_correlation_ref",
            "tenant_id",
            "retention_policy_id",
            "decision_reason_code",
            "authority",
            "correlation_id",
            "trace_id",
            "signing_algorithm",
            "signing_key_id",
        ):
            if not _REFERENCE.fullmatch(str(getattr(self, field_name))):
                raise ValueError(f"{field_name} must be a source-safe reference")
        if not _REGION.fullmatch(self.residency_region):
            raise ValueError("residency_region must be a source-safe region code")
        if (
            isinstance(self.legal_hold_count, bool)
            or not isinstance(self.legal_hold_count, int)
            or self.legal_hold_count < 0
        ):
            raise ValueError("legal_hold_count must be a non-negative integer")
        _require_utc(self.issued_at_utc, "issued_at_utc")
        _require_utc(self.expires_at_utc, "expires_at_utc")
        if self.issued_at_utc >= self.expires_at_utc:
            raise ValueError("Archive lifecycle decision validity window is invalid")


@dataclass(frozen=True)
class ArchiveLifecycleDecisionEnvelope:
    claims: ArchiveLifecycleDecisionClaims
    payload_digest: str
    signature: str
    canonical_claims: Mapping[str, object]

    def __post_init__(self) -> None:
        if not _SHA256.fullmatch(self.payload_digest):
            raise ValueError("payload_digest must be a prefixed lowercase SHA-256 digest")
        if not self.signature.startswith("ed25519:"):
            raise ValueError("signature must use the Ed25519 envelope prefix")


@dataclass(frozen=True)
class ArchiveLifecycleTrustedKey:
    key_id: str
    public_key_base64url: str
    status: str
    not_before_utc: datetime
    not_after_utc: datetime | None = None

    def __post_init__(self) -> None:
        if not _REFERENCE.fullmatch(self.key_id):
            raise ValueError("key_id must be a source-safe reference")
        if not self.public_key_base64url:
            raise ValueError("public_key_base64url is required")
        _require_utc(self.not_before_utc, "not_before_utc")
        if self.not_after_utc is not None:
            _require_utc(self.not_after_utc, "not_after_utc")
            if self.not_after_utc <= self.not_before_utc:
                raise ValueError("Archive trusted key validity window is invalid")


@dataclass(frozen=True)
class ExpectedArchiveLifecyclePosture:
    tenant_id: str
    candidate_id: str
    linked_evidence_pack_ids: frozenset[str]
    verified_at_utc: datetime

    def __post_init__(self) -> None:
        _require_reference(self.tenant_id, "tenant_id")
        _require_reference(self.candidate_id, "candidate_id")
        if not self.linked_evidence_pack_ids:
            raise ValueError("linked_evidence_pack_ids is required")
        for evidence_pack_id in self.linked_evidence_pack_ids:
            _require_reference(evidence_pack_id, "linked_evidence_pack_id")
        _require_utc(self.verified_at_utc, "verified_at_utc")


@dataclass(frozen=True)
class VerifiedArchiveLifecycleReceipt:
    decision_id: str
    document_id: str
    evidence_pack_id: str
    candidate_id: str
    tenant_id: str
    retention_policy_id: str
    legal_hold_status: ArchiveLegalHoldStatus
    purge_status: ArchivePurgeStatus
    lifecycle_action: ArchiveLifecycleAction
    payload_digest: str
    key_id: str
    issued_at_utc: datetime
    expires_at_utc: datetime
    verified_at_utc: datetime

    def __post_init__(self) -> None:
        for field_name in (
            "decision_id",
            "document_id",
            "evidence_pack_id",
            "candidate_id",
            "tenant_id",
            "retention_policy_id",
            "key_id",
        ):
            _require_reference(str(getattr(self, field_name)), field_name)
        if not _SHA256.fullmatch(self.payload_digest):
            raise ValueError("payload_digest must be a prefixed lowercase SHA-256 digest")
        for field_name in ("issued_at_utc", "expires_at_utc", "verified_at_utc"):
            _require_utc(getattr(self, field_name), field_name)
        if not self.issued_at_utc <= self.verified_at_utc < self.expires_at_utc:
            raise ValueError("verified Archive lifecycle receipt is outside its validity window")


def _require_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be timezone-aware UTC")


def _require_reference(value: str, field_name: str) -> None:
    if not _REFERENCE.fullmatch(value):
        raise ValueError(f"{field_name} must be a source-safe reference")
