from __future__ import annotations

from collections.abc import Mapping
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


def build_ai_attestation_source_contract(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
    lotus_ai_root: Path | None = None,
) -> dict[str, Any]:
    lotus_ai_root = lotus_ai_root or repository_root.parent / "lotus-ai"
    consumer_sources = _consumer_sources(repository_root)
    producer_sources = _producer_sources(lotus_ai_root)
    consumer_authority = build_source_authority_records(consumer_sources)
    producer_authority = build_source_authority_records(producer_sources)
    consumer_authority_valid = source_authority_records_are_valid(
        consumer_authority,
        expected_sources=consumer_sources,
    )
    producer_authority_valid = source_authority_records_are_valid(
        producer_authority,
        expected_sources=producer_sources,
    )
    producer_claims_declared = text_file_contains_all(
        lotus_ai_root / PRODUCER_SOURCE_REFS[0],
        ("WorkflowRunAttestationClaims", "model_risk_approval_ref", "replay_nonce"),
    )
    producer_signing_declared = text_file_contains_all(
        lotus_ai_root / PRODUCER_SOURCE_REFS[1],
        ("EdDSA", "signature_base64url", "canonical_attestation_payload"),
    )
    producer_issuance_fail_closed = text_file_contains_all(
        lotus_ai_root / PRODUCER_SOURCE_REFS[2],
        ("model_risk_status", "approval_ref", "stubbed"),
    )
    consumer_verification_declared = text_file_contains_all(
        repository_root / CONSUMER_SOURCE_REFS[1],
        (
            "verify_lotus_ai_run_attestation",
            "select_trusted_ed25519_key",
            "signature_verifier.verify",
            "input digest",
            "output digest",
        ),
    )
    consumer_replay_persistence_declared = _consumer_replay_persistence_declared(repository_root)
    timezone_aware = (
        generated_at_utc.tzinfo is not None and generated_at_utc.utcoffset() is not None
    )
    evidence_class_matches_blockers = all(
        evidence_class_can_clear(
            actual=EvidenceClass.SOURCE_CONTRACT,
            required=EvidenceClass(required_class),
        )
        for _blocker, required_class in AI_ATTESTATION_REQUIRED_BLOCKER_EVIDENCE_CLASSES
    )
    consumer_valid = (
        timezone_aware
        and consumer_authority_valid
        and consumer_verification_declared
        and consumer_replay_persistence_declared
        and evidence_class_matches_blockers
    )
    producer_valid = (
        producer_authority_valid
        and producer_claims_declared
        and producer_signing_declared
        and producer_issuance_fail_closed
    )
    source_contract_valid = consumer_valid and producer_valid
    return {
        "schemaVersion": AI_ATTESTATION_SOURCE_CONTRACT_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "signed_ai_attestation_source_contract",
        "proofScope": "lotus_ai_producer_and_idea_consumer_source_declarations",
        "validationScope": ("full_cross_repository" if producer_valid else "idea_consumer_only"),
        "evidenceClass": EvidenceClass.SOURCE_CONTRACT.value,
        "sourceContractValid": source_contract_valid,
        "consumerSourceContractValid": consumer_valid,
        "producerSourceContractValid": producer_valid,
        "sourceContractBlockersSatisfied": AI_ATTESTATION_SOURCE_CONTRACT_BLOCKERS_SATISFIED,
        "requiredBlockerEvidenceClasses": dict(AI_ATTESTATION_REQUIRED_BLOCKER_EVIDENCE_CLASSES),
        "evidenceRefs": REQUIRED_AI_ATTESTATION_EVIDENCE_REFS,
        "consumerSourceAuthority": consumer_authority,
        "consumerSourceAuthorityDigest": source_authority_records_digest(consumer_authority),
        "producerSourceAuthority": producer_authority,
        "producerSourceAuthorityDigest": source_authority_records_digest(producer_authority),
        "contractChecks": {
            "timezoneAwareGeneratedAtUtc": timezone_aware,
            "consumerSourceAuthorityDigestBound": consumer_authority_valid,
            "producerSourceAuthorityDigestBound": producer_authority_valid,
            "producerClaimsDeclared": producer_claims_declared,
            "producerSigningDeclared": producer_signing_declared,
            "producerIssuanceFailClosed": producer_issuance_fail_closed,
            "consumerVerificationDeclared": consumer_verification_declared,
            "consumerReplayPersistenceDeclared": consumer_replay_persistence_declared,
            "evidenceClassMatchesBlockers": evidence_class_matches_blockers,
        },
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
