from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from app.application.proof_provenance import AGGREGATE_PROOF_PROVENANCE_KEY
from app.application.source_authority import (
    SourceAuthoritySource,
    build_source_authority_records,
    source_authority_records_are_valid,
    source_authority_records_digest,
)
from app.application.source_safe_cross_repo_proof import (
    is_timezone_aware_datetime_text,
    text_file_contains_all,
)
from app.domain.proof_evidence import EvidenceClass, evidence_class_can_clear


AI_ATTESTATION_SOURCE_CONTRACT_SCHEMA_VERSION = (
    "lotus-idea.signed-ai-attestation-source-contract.v2"
)
AI_ATTESTATION_SOURCE_CONTRACT_BLOCKERS_SATISFIED: tuple[str, ...] = ()
AI_ATTESTATION_REQUIRED_BLOCKER_EVIDENCE_CLASSES: tuple[tuple[str, str], ...] = ()

REMAINING_AI_ATTESTATION_CERTIFICATION_BLOCKERS = (
    "lotus_ai_runtime_execution_missing",
    "certified_runtime_trust_telemetry_missing",
    "workbench_product_proof_missing",
    "supported_feature_promotion_missing",
)

PRODUCER_SOURCE_REFS = (
    "src/app/contracts/workflow_run_attestation.py",
    "src/app/services/workflow_run_attestation_signing.py",
    "src/app/services/workflow_run_attestation_issuance.py",
    "src/app/routers/workflow_run_attestations.py",
    "tests/unit/test_workflow_run_attestation_signing.py",
    "tests/unit/test_workflow_run_attestation_issuance.py",
    "tests/integration/test_workflow_run_attestation_api_contract.py",
)

CONSUMER_SOURCE_REFS = (
    "src/app/domain/lotus_ai_run_attestation.py",
    "src/app/application/lotus_ai_run_attestation_verification.py",
    "src/app/infrastructure/http_lotus_ai_attestation_keys.py",
    "src/app/domain/persistence_ai_lineage.py",
    "src/app/domain/lotus_ai_attestation_replay.py",
    "migrations/012_ai_run_attestation_receipt.sql",
)

REQUIRED_AI_ATTESTATION_EVIDENCE_REFS = (
    *(f"../lotus-ai/{ref}" for ref in PRODUCER_SOURCE_REFS),
    *CONSUMER_SOURCE_REFS,
    "scripts/ai_attestation/generate_source_contract.py",
    "scripts/ai_attestation/source_contract_gate.py",
    "tests/unit/ai_attestation/test_source_contract.py",
    "tests/unit/ai_attestation/test_source_contract_automation.py",
    "make ai-attestation-source-contract-gate",
)

_PAYLOAD_FIELDS = frozenset(
    {
        "schemaVersion",
        "repository",
        "generatedAtUtc",
        "proofType",
        "proofScope",
        "validationScope",
        "evidenceClass",
        "sourceContractValid",
        "consumerSourceContractValid",
        "producerSourceContractValid",
        "sourceContractBlockersSatisfied",
        "requiredBlockerEvidenceClasses",
        "evidenceRefs",
        "consumerSourceAuthority",
        "consumerSourceAuthorityDigest",
        "producerSourceAuthority",
        "producerSourceAuthorityDigest",
        "contractChecks",
        "remainingCertificationBlockers",
        "runtimeExecutionObserved",
        "liveProviderExecuted",
        "modelRiskApprovalObserved",
        "deploymentObserved",
        "productionCertificationGranted",
        "workbenchProductProofCertified",
        "clientReadyPublicationAuthorized",
        "supportedFeaturePromoted",
        "certificationClosed",
    }
)

_CONTRACT_CHECK_FIELDS = frozenset(
    {
        "timezoneAwareGeneratedAtUtc",
        "consumerSourceAuthorityDigestBound",
        "producerSourceAuthorityDigestBound",
        "producerClaimsDeclared",
        "producerSigningDeclared",
        "producerIssuanceFailClosed",
        "consumerVerificationDeclared",
        "consumerReplayPersistenceDeclared",
        "evidenceClassMatchesBlockers",
    }
)

_FALSE_AUTHORITY_CLAIMS = (
    "runtimeExecutionObserved",
    "liveProviderExecuted",
    "modelRiskApprovalObserved",
    "deploymentObserved",
    "productionCertificationGranted",
    "workbenchProductProofCertified",
    "clientReadyPublicationAuthorized",
    "supportedFeaturePromoted",
    "certificationClosed",
)


@dataclass(frozen=True, slots=True)
class _SourceContractAuthority:
    consumer_sources: tuple[SourceAuthoritySource, ...]
    producer_sources: tuple[SourceAuthoritySource, ...]
    consumer_authority: tuple[Mapping[str, Any], ...]
    producer_authority: tuple[Mapping[str, Any], ...]
    consumer_valid: bool
    producer_valid: bool


@dataclass(frozen=True, slots=True)
class _SourceContractChecks:
    timezone_aware_generated_at_utc: bool
    consumer_source_authority_digest_bound: bool
    producer_source_authority_digest_bound: bool
    producer_claims_declared: bool
    producer_signing_declared: bool
    producer_issuance_fail_closed: bool
    consumer_verification_declared: bool
    consumer_replay_persistence_declared: bool
    evidence_class_matches_blockers: bool

    def as_contract_payload(self) -> dict[str, bool]:
        return {
            "timezoneAwareGeneratedAtUtc": self.timezone_aware_generated_at_utc,
            "consumerSourceAuthorityDigestBound": self.consumer_source_authority_digest_bound,
            "producerSourceAuthorityDigestBound": self.producer_source_authority_digest_bound,
            "producerClaimsDeclared": self.producer_claims_declared,
            "producerSigningDeclared": self.producer_signing_declared,
            "producerIssuanceFailClosed": self.producer_issuance_fail_closed,
            "consumerVerificationDeclared": self.consumer_verification_declared,
            "consumerReplayPersistenceDeclared": self.consumer_replay_persistence_declared,
            "evidenceClassMatchesBlockers": self.evidence_class_matches_blockers,
        }


@dataclass(frozen=True, slots=True)
class _SourceContractValidity:
    consumer_valid: bool
    producer_valid: bool

    @property
    def source_contract_valid(self) -> bool:
        return self.consumer_valid and self.producer_valid

    @property
    def validation_scope(self) -> str:
        return "full_cross_repository" if self.producer_valid else "idea_consumer_only"


def build_ai_attestation_source_contract(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
    lotus_ai_root: Path | None = None,
) -> dict[str, Any]:
    resolved_lotus_ai_root = lotus_ai_root or repository_root.parent / "lotus-ai"
    authority = _build_source_contract_authority(repository_root, resolved_lotus_ai_root)
    checks = _build_source_contract_checks(
        generated_at_utc=generated_at_utc,
        repository_root=repository_root,
        lotus_ai_root=resolved_lotus_ai_root,
        authority=authority,
    )
    validity = _build_source_contract_validity(checks)
    return _build_source_contract_payload(
        generated_at_utc=generated_at_utc,
        authority=authority,
        checks=checks,
        validity=validity,
    )


def _build_source_contract_payload(
    *,
    generated_at_utc: datetime,
    authority: _SourceContractAuthority,
    checks: _SourceContractChecks,
    validity: _SourceContractValidity,
) -> dict[str, Any]:
    return {
        "schemaVersion": AI_ATTESTATION_SOURCE_CONTRACT_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "signed_ai_attestation_source_contract",
        "proofScope": "lotus_ai_producer_and_idea_consumer_source_declarations",
        "validationScope": validity.validation_scope,
        "evidenceClass": EvidenceClass.SOURCE_CONTRACT.value,
        "sourceContractValid": validity.source_contract_valid,
        "consumerSourceContractValid": validity.consumer_valid,
        "producerSourceContractValid": validity.producer_valid,
        "sourceContractBlockersSatisfied": AI_ATTESTATION_SOURCE_CONTRACT_BLOCKERS_SATISFIED,
        "requiredBlockerEvidenceClasses": dict(AI_ATTESTATION_REQUIRED_BLOCKER_EVIDENCE_CLASSES),
        "evidenceRefs": REQUIRED_AI_ATTESTATION_EVIDENCE_REFS,
        "consumerSourceAuthority": authority.consumer_authority,
        "consumerSourceAuthorityDigest": source_authority_records_digest(
            authority.consumer_authority
        ),
        "producerSourceAuthority": authority.producer_authority,
        "producerSourceAuthorityDigest": source_authority_records_digest(
            authority.producer_authority
        ),
        "contractChecks": checks.as_contract_payload(),
        "remainingCertificationBlockers": REMAINING_AI_ATTESTATION_CERTIFICATION_BLOCKERS,
        "runtimeExecutionObserved": False,
        "liveProviderExecuted": False,
        "modelRiskApprovalObserved": False,
        "deploymentObserved": False,
        "productionCertificationGranted": False,
        "workbenchProductProofCertified": False,
        "clientReadyPublicationAuthorized": False,
        "supportedFeaturePromoted": False,
        "certificationClosed": False,
    }


def _build_source_contract_authority(
    repository_root: Path,
    lotus_ai_root: Path,
) -> _SourceContractAuthority:
    consumer_sources = _consumer_sources(repository_root)
    producer_sources = _producer_sources(lotus_ai_root)
    consumer_authority = build_source_authority_records(consumer_sources)
    producer_authority = build_source_authority_records(producer_sources)
    return _SourceContractAuthority(
        consumer_sources=consumer_sources,
        producer_sources=producer_sources,
        consumer_authority=consumer_authority,
        producer_authority=producer_authority,
        consumer_valid=source_authority_records_are_valid(
            consumer_authority,
            expected_sources=consumer_sources,
        ),
        producer_valid=source_authority_records_are_valid(
            producer_authority,
            expected_sources=producer_sources,
        ),
    )


def _build_source_contract_checks(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
    lotus_ai_root: Path,
    authority: _SourceContractAuthority,
) -> _SourceContractChecks:
    return _SourceContractChecks(
        timezone_aware_generated_at_utc=_is_timezone_aware_datetime(generated_at_utc),
        consumer_source_authority_digest_bound=authority.consumer_valid,
        producer_source_authority_digest_bound=authority.producer_valid,
        producer_claims_declared=_producer_claims_declared(lotus_ai_root),
        producer_signing_declared=_producer_signing_declared(lotus_ai_root),
        producer_issuance_fail_closed=_producer_issuance_fail_closed(lotus_ai_root),
        consumer_verification_declared=_consumer_verification_declared(repository_root),
        consumer_replay_persistence_declared=_consumer_replay_persistence_declared(repository_root),
        evidence_class_matches_blockers=_evidence_class_matches_blockers(),
    )


def _build_source_contract_validity(
    checks: _SourceContractChecks,
) -> _SourceContractValidity:
    consumer_valid = (
        checks.timezone_aware_generated_at_utc
        and checks.consumer_source_authority_digest_bound
        and checks.consumer_verification_declared
        and checks.consumer_replay_persistence_declared
        and checks.evidence_class_matches_blockers
    )
    producer_valid = (
        checks.producer_source_authority_digest_bound
        and checks.producer_claims_declared
        and checks.producer_signing_declared
        and checks.producer_issuance_fail_closed
    )
    return _SourceContractValidity(
        consumer_valid=consumer_valid,
        producer_valid=producer_valid,
    )


def _is_timezone_aware_datetime(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def _producer_claims_declared(lotus_ai_root: Path) -> bool:
    return text_file_contains_all(
        lotus_ai_root / PRODUCER_SOURCE_REFS[0],
        ("WorkflowRunAttestationClaims", "model_risk_approval_ref", "replay_nonce"),
    )


def _producer_signing_declared(lotus_ai_root: Path) -> bool:
    return text_file_contains_all(
        lotus_ai_root / PRODUCER_SOURCE_REFS[1],
        ("EdDSA", "signature_base64url", "canonical_attestation_payload"),
    )


def _producer_issuance_fail_closed(lotus_ai_root: Path) -> bool:
    return text_file_contains_all(
        lotus_ai_root / PRODUCER_SOURCE_REFS[2],
        ("model_risk_status", "approval_ref", "stubbed"),
    )


def _consumer_verification_declared(repository_root: Path) -> bool:
    return text_file_contains_all(
        repository_root / CONSUMER_SOURCE_REFS[1],
        (
            "verify_lotus_ai_run_attestation",
            "select_trusted_ed25519_key",
            "signature_verifier.verify",
            "input digest",
            "output digest",
        ),
    )


def _evidence_class_matches_blockers() -> bool:
    return all(
        evidence_class_can_clear(
            actual=EvidenceClass.SOURCE_CONTRACT,
            required=EvidenceClass(required_class),
        )
        for _blocker, required_class in AI_ATTESTATION_REQUIRED_BLOCKER_EVIDENCE_CLASSES
    )


def signed_ai_attestation_source_contract_is_valid(payload: Mapping[str, Any]) -> bool:
    if not _common_contract_is_valid(payload):
        return False
    if payload.get("validationScope") != "full_cross_repository":
        return False
    if payload.get("sourceContractValid") is not True:
        return False
    if payload.get("consumerSourceContractValid") is not True:
        return False
    if payload.get("producerSourceContractValid") is not True:
        return False
    consumer_sources = _consumer_sources(Path())
    producer_sources = _producer_sources(Path())
    if not source_authority_records_are_valid(
        payload.get("consumerSourceAuthority"),
        expected_sources=consumer_sources,
    ):
        return False
    if not source_authority_records_are_valid(
        payload.get("producerSourceAuthority"),
        expected_sources=producer_sources,
    ):
        return False
    if payload.get("consumerSourceAuthorityDigest") != source_authority_records_digest(
        payload.get("consumerSourceAuthority")
    ):
        return False
    if payload.get("producerSourceAuthorityDigest") != source_authority_records_digest(
        payload.get("producerSourceAuthority")
    ):
        return False
    checks = payload.get("contractChecks")
    return isinstance(checks, Mapping) and all(
        checks.get(name) is True for name in _CONTRACT_CHECK_FIELDS
    )


def idea_consumer_source_contract_is_valid(payload: Mapping[str, Any]) -> bool:
    if not _common_contract_is_valid(payload):
        return False
    if payload.get("validationScope") != "idea_consumer_only":
        return False
    if payload.get("sourceContractValid") is not False:
        return False
    if payload.get("consumerSourceContractValid") is not True:
        return False
    if payload.get("producerSourceContractValid") is not False:
        return False
    if not source_authority_records_are_valid(
        payload.get("consumerSourceAuthority"),
        expected_sources=_consumer_sources(Path()),
    ):
        return False
    if payload.get("consumerSourceAuthorityDigest") != source_authority_records_digest(
        payload.get("consumerSourceAuthority")
    ):
        return False
    if payload.get("producerSourceAuthorityDigest") is not None:
        return False
    if not _missing_producer_authority_is_explicit(payload.get("producerSourceAuthority")):
        return False
    checks = cast(Mapping[str, Any], payload["contractChecks"])
    expected_true = _CONTRACT_CHECK_FIELDS - {
        "producerSourceAuthorityDigestBound",
        "producerClaimsDeclared",
        "producerSigningDeclared",
        "producerIssuanceFailClosed",
    }
    return all(checks.get(name) is True for name in expected_true) and all(
        checks.get(name) is False for name in _CONTRACT_CHECK_FIELDS - expected_true
    )


def _common_contract_is_valid(payload: Mapping[str, Any]) -> bool:
    if set(payload) not in (_PAYLOAD_FIELDS, _PAYLOAD_FIELDS | {AGGREGATE_PROOF_PROVENANCE_KEY}):
        return False
    if payload.get("schemaVersion") != AI_ATTESTATION_SOURCE_CONTRACT_SCHEMA_VERSION:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("proofType") != "signed_ai_attestation_source_contract":
        return False
    if payload.get("proofScope") != ("lotus_ai_producer_and_idea_consumer_source_declarations"):
        return False
    if payload.get("evidenceClass") != EvidenceClass.SOURCE_CONTRACT.value:
        return False
    if payload.get("requiredBlockerEvidenceClasses") != dict(
        AI_ATTESTATION_REQUIRED_BLOCKER_EVIDENCE_CLASSES
    ):
        return False
    if tuple(payload.get("sourceContractBlockersSatisfied") or ()) != (
        AI_ATTESTATION_SOURCE_CONTRACT_BLOCKERS_SATISFIED
    ):
        return False
    if tuple(payload.get("evidenceRefs") or ()) != REQUIRED_AI_ATTESTATION_EVIDENCE_REFS:
        return False
    if tuple(payload.get("remainingCertificationBlockers") or ()) != (
        REMAINING_AI_ATTESTATION_CERTIFICATION_BLOCKERS
    ):
        return False
    if not is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if any(payload.get(claim) is not False for claim in _FALSE_AUTHORITY_CLAIMS):
        return False
    checks = payload.get("contractChecks")
    return isinstance(checks, Mapping) and set(checks) == _CONTRACT_CHECK_FIELDS


def _consumer_sources(repository_root: Path) -> tuple[SourceAuthoritySource, ...]:
    return tuple(
        SourceAuthoritySource("lotus-idea", ref, repository_root / ref)
        for ref in CONSUMER_SOURCE_REFS
    )


def _producer_sources(lotus_ai_root: Path) -> tuple[SourceAuthoritySource, ...]:
    return tuple(
        SourceAuthoritySource("lotus-ai", f"../lotus-ai/{ref}", lotus_ai_root / ref)
        for ref in PRODUCER_SOURCE_REFS
    )


def _missing_producer_authority_is_explicit(value: object) -> bool:
    if not isinstance(value, (list, tuple)) or len(value) != len(PRODUCER_SOURCE_REFS):
        return False
    for item, source in zip(value, _producer_sources(Path()), strict=True):
        if not isinstance(item, Mapping) or set(item) != {"repository", "ref", "sha256"}:
            return False
        if item.get("repository") != source.repository or item.get("ref") != source.ref:
            return False
        if item.get("sha256") is not None:
            return False
    return True


def _consumer_replay_persistence_declared(repository_root: Path) -> bool:
    return (
        text_file_contains_all(
            repository_root / CONSUMER_SOURCE_REFS[3],
            ("LotusAIAttestationReplayIndex", "attestation_receipt"),
        )
        and text_file_contains_all(
            repository_root / CONSUMER_SOURCE_REFS[4],
            ("_request_by_run_id", "_request_by_nonce", "conflicts"),
        )
        and text_file_contains_all(
            repository_root / CONSUMER_SOURCE_REFS[5],
            ("lotus_ai_run_id", "lotus_ai_replay_nonce", "CREATE UNIQUE INDEX"),
        )
    )
