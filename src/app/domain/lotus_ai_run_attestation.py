from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Mapping


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class LotusAIRunAttestationClaims:
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

    def __post_init__(self) -> None:
        for field_name in (
            "run_id",
            "consumer_request_id",
            "workflow_pack_id",
            "workflow_pack_version",
            "registration_ref",
            "evaluator_id",
            "evaluator_policy_version",
            "provider_id",
            "provider_mode",
            "model_id",
            "model_version",
            "model_risk_approval_ref",
        ):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} is required")
        for field_name in (
            "replay_nonce",
            "input_evidence_sha256",
            "output_content_sha256",
        ):
            if not _SHA256.fullmatch(str(getattr(self, field_name))):
                raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
        for field_name in (
            "issued_at_utc",
            "execution_started_at_utc",
            "execution_completed_at_utc",
            "expires_at_utc",
        ):
            value = getattr(self, field_name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True)
class LotusAIRunAttestationSignature:
    algorithm: str
    key_id: str
    rotation_epoch: int
    signature_base64url: str


@dataclass(frozen=True)
class LotusAIRunAttestationEnvelope:
    claims: LotusAIRunAttestationClaims
    signature: LotusAIRunAttestationSignature
    key_discovery_path: str
    canonical_claims: Mapping[str, object]


@dataclass(frozen=True)
class LotusAIAttestationPublicKey:
    key_id: str
    algorithm: str
    curve: str
    public_key_base64url: str
    rotation_epoch: int
    status: str
    not_before_utc: datetime
    not_after_utc: datetime | None


@dataclass(frozen=True)
class LotusAIAttestationKeyDiscovery:
    schema_version: str
    issuer: str
    keys: tuple[LotusAIAttestationPublicKey, ...]


@dataclass(frozen=True)
class ExpectedLotusAIRunAttestation:
    run_id: str
    consumer_request_id: str
    input_evidence_sha256: str
    output_content_sha256: str
    verified_at_utc: datetime


@dataclass(frozen=True)
class VerifiedLotusAIRunAttestationReceipt:
    run_id: str
    consumer_request_id: str
    replay_nonce: str
    key_id: str
    rotation_epoch: int
    provider_id: str
    provider_mode: str
    model_id: str
    model_version: str
    model_risk_approval_ref: str
    evaluator_id: str
    evaluator_policy_version: str
    input_evidence_sha256: str
    output_content_sha256: str
    issued_at_utc: datetime
    expires_at_utc: datetime
    verified_at_utc: datetime
