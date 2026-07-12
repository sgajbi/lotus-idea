from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
import re
from typing import Mapping


AI_PROVIDER_RETENTION_SCHEMA_VERSION = "lotus-ai.provider-retention-confirmation.v1"
AI_PROVIDER_RETENTION_KEY_DISCOVERY_PATH = "/.well-known/lotus-ai-workflow-attestation-keys"

_REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{2,255}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class AIProviderRetentionOutcome(StrEnum):
    NO_PROVIDER_STORAGE = "NO_PROVIDER_STORAGE"
    RETENTION_CONFIRMED = "RETENTION_CONFIRMED"
    DELETION_CONFIRMED = "DELETION_CONFIRMED"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"


@dataclass(frozen=True)
class AIProviderRetentionClaims:
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
    provider_failure_code: str | None
    deletion_confirmed: bool
    raw_prompt_included: bool
    raw_output_included: bool
    client_identifier_included: bool
    supportability_status: str
    issued_at_utc: datetime
    expires_at_utc: datetime
    replay_nonce: str

    def __post_init__(self) -> None:
        for field_name in (
            "schema_version",
            "issuer",
            "audience",
            "recorded_by",
            "confirmation_id",
            "workflow_run_id",
            "workflow_pack_id",
            "tenant_id",
            "provider_id",
            "provider_mode",
            "model_id",
            "model_version",
            "provider_confirmation_ref",
            "retention_policy_id",
            "supportability_status",
        ):
            if not _REFERENCE.fullmatch(str(getattr(self, field_name))):
                raise ValueError(f"{field_name} must be a source-safe reference")
        if self.provider_failure_code is not None and not _REFERENCE.fullmatch(
            self.provider_failure_code
        ):
            raise ValueError("provider_failure_code must be a source-safe reference")
        for field_name in ("evidence_sha256", "replay_nonce"):
            if not _SHA256.fullmatch(str(getattr(self, field_name))):
                raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
        for field_name in (
            "provider_decision_at_utc",
            "issued_at_utc",
            "expires_at_utc",
        ):
            _require_utc(getattr(self, field_name), field_name)
        if not self.provider_decision_at_utc <= self.issued_at_utc < self.expires_at_utc:
            raise ValueError("provider retention confirmation validity window is invalid")


@dataclass(frozen=True)
class AIProviderRetentionSignature:
    algorithm: str
    key_id: str
    rotation_epoch: int
    signature_base64url: str


@dataclass(frozen=True)
class AIProviderRetentionEnvelope:
    claims: AIProviderRetentionClaims
    signature: AIProviderRetentionSignature
    key_discovery_path: str
    canonical_claims: Mapping[str, object]


@dataclass(frozen=True)
class ExpectedAIProviderRetention:
    workflow_run_id: str
    tenant_id: str
    provider_id: str
    provider_mode: str
    model_id: str
    model_version: str
    verified_at_utc: datetime


@dataclass(frozen=True)
class VerifiedAIProviderRetentionReceipt:
    confirmation_id: str
    workflow_run_id: str
    tenant_id: str
    provider_confirmation_ref: str
    retention_policy_id: str
    outcome: AIProviderRetentionOutcome
    evidence_sha256: str
    provider_failure_code: str | None
    deletion_confirmed: bool
    supportability_status: str
    replay_nonce: str
    key_id: str
    rotation_epoch: int
    provider_decision_at_utc: datetime
    issued_at_utc: datetime
    expires_at_utc: datetime
    verified_at_utc: datetime

    def __post_init__(self) -> None:
        for field_name in (
            "confirmation_id",
            "workflow_run_id",
            "tenant_id",
            "provider_confirmation_ref",
            "retention_policy_id",
            "supportability_status",
            "key_id",
        ):
            if not _REFERENCE.fullmatch(str(getattr(self, field_name))):
                raise ValueError(f"{field_name} must be a source-safe reference")
        for field_name in ("evidence_sha256", "replay_nonce"):
            if not _SHA256.fullmatch(str(getattr(self, field_name))):
                raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
        if self.rotation_epoch < 1:
            raise ValueError("rotation_epoch must be positive")
        for field_name in (
            "provider_decision_at_utc",
            "issued_at_utc",
            "expires_at_utc",
            "verified_at_utc",
        ):
            _require_utc(getattr(self, field_name), field_name)
        if not self.issued_at_utc <= self.verified_at_utc < self.expires_at_utc:
            raise ValueError("verified provider retention receipt is outside its validity window")


def _require_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be timezone-aware UTC")
