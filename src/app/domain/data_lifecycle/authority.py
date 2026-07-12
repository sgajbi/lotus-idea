from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
import re
from typing import Mapping

from app.domain.data_lifecycle import DataLifecycleAction


LIFECYCLE_AUTHORITY_SCHEMA_VERSION = "lotus.lifecycle-authority-decision.v1"
LIFECYCLE_AUTHORITY_KEY_SCHEMA_VERSION = "lotus.lifecycle-authority-keys.v1"
LIFECYCLE_AUTHORITY_ISSUER = "bank-lifecycle-governance"
LIFECYCLE_AUTHORITY_AUDIENCE = "lotus-idea"
LIFECYCLE_AUTHORITY_KEY_DISCOVERY_PATH = "/.well-known/lotus-lifecycle-authority-keys"

_REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{2,255}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class LifecycleAuthorityDomain(StrEnum):
    LEGAL_AND_RECORDS = "legal_and_records"
    PRIVACY = "privacy"


@dataclass(frozen=True)
class LifecycleAuthorityDecisionClaims:
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

    def __post_init__(self) -> None:
        for field_name in (
            "schema_version",
            "issuer",
            "audience",
            "decision_id",
            "tenant_id",
            "candidate_id",
            "authority_ref",
            "change_reference",
            "decision_status",
        ):
            if not _REFERENCE.fullmatch(str(getattr(self, field_name))):
                raise ValueError(f"{field_name} must be a source-safe reference")
        if not _SHA256.fullmatch(self.replay_nonce):
            raise ValueError("replay_nonce must be a lowercase SHA-256 digest")
        for field_name in ("issued_at_utc", "effective_at_utc", "expires_at_utc"):
            _require_utc(getattr(self, field_name), field_name)
        if not self.issued_at_utc <= self.effective_at_utc < self.expires_at_utc:
            raise ValueError("lifecycle authority decision validity window is invalid")


@dataclass(frozen=True)
class LifecycleAuthoritySignature:
    algorithm: str
    key_id: str
    rotation_epoch: int
    signature_base64url: str


@dataclass(frozen=True)
class LifecycleAuthorityDecisionEnvelope:
    claims: LifecycleAuthorityDecisionClaims
    signature: LifecycleAuthoritySignature
    key_discovery_path: str
    canonical_claims: Mapping[str, object]


@dataclass(frozen=True)
class LifecycleAuthorityPublicKey:
    key_id: str
    algorithm: str
    curve: str
    public_key_base64url: str
    rotation_epoch: int
    status: str
    not_before_utc: datetime
    not_after_utc: datetime | None


@dataclass(frozen=True)
class LifecycleAuthorityKeyDiscovery:
    schema_version: str
    issuer: str
    keys: tuple[LifecycleAuthorityPublicKey, ...]


@dataclass(frozen=True)
class ExpectedLifecycleAuthorityDecision:
    tenant_id: str
    candidate_id: str
    action: DataLifecycleAction
    authority_ref: str
    change_reference: str
    verified_at_utc: datetime


@dataclass(frozen=True)
class VerifiedLifecycleAuthorityReceipt:
    decision_id: str
    replay_nonce: str
    tenant_id: str
    candidate_id: str
    action: DataLifecycleAction
    authority_domain: LifecycleAuthorityDomain
    authority_ref: str
    change_reference: str
    key_id: str
    rotation_epoch: int
    issued_at_utc: datetime
    effective_at_utc: datetime
    expires_at_utc: datetime
    verified_at_utc: datetime

    def __post_init__(self) -> None:
        for field_name in (
            "decision_id",
            "tenant_id",
            "candidate_id",
            "authority_ref",
            "change_reference",
            "key_id",
        ):
            if not _REFERENCE.fullmatch(str(getattr(self, field_name))):
                raise ValueError(f"{field_name} must be a source-safe reference")
        if not _SHA256.fullmatch(self.replay_nonce):
            raise ValueError("replay_nonce must be a lowercase SHA-256 digest")
        if self.rotation_epoch < 1:
            raise ValueError("rotation_epoch must be positive")
        for field_name in (
            "issued_at_utc",
            "effective_at_utc",
            "expires_at_utc",
            "verified_at_utc",
        ):
            _require_utc(getattr(self, field_name), field_name)
        if not self.issued_at_utc <= self.effective_at_utc <= self.verified_at_utc:
            raise ValueError("verified lifecycle authority receipt is not yet effective")
        if self.verified_at_utc >= self.expires_at_utc:
            raise ValueError("verified lifecycle authority receipt is expired")


def expected_authority_domain(action: DataLifecycleAction) -> LifecycleAuthorityDomain:
    if action in {DataLifecycleAction.APPLY_HOLD, DataLifecycleAction.RELEASE_HOLD}:
        return LifecycleAuthorityDomain.LEGAL_AND_RECORDS
    return LifecycleAuthorityDomain.PRIVACY


def _require_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be timezone-aware UTC")
