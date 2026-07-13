from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from app.application.source_safe_cross_repo_proof import (
    is_timezone_aware_datetime_text,
    required_file_evidence_present,
    text_file_contains_all,
)

LOTUS_AI_ATTESTATION_CONTRACT_PROOF_SCHEMA_VERSION = (
    "lotus-idea.lotus-ai-attestation-contract-proof.v1"
)

REQUIRED_LOTUS_AI_ATTESTATION_EVIDENCE_REFS = (
    "../lotus-ai/src/app/contracts/workflow_run_attestation.py",
    "../lotus-ai/src/app/services/workflow_run_attestation_signing.py",
    "../lotus-ai/src/app/services/workflow_run_attestation_issuance.py",
    "../lotus-ai/src/app/routers/workflow_run_attestations.py",
    "../lotus-ai/tests/unit/test_workflow_run_attestation_signing.py",
    "../lotus-ai/tests/unit/test_workflow_run_attestation_issuance.py",
    "../lotus-ai/tests/integration/test_workflow_run_attestation_api_contract.py",
    "src/app/application/lotus_ai_run_attestation_verification.py",
    "src/app/infrastructure/http_lotus_ai_attestation_keys.py",
    "src/app/infrastructure/ed25519_lotus_ai_attestation_verifier.py",
    "src/app/domain/persistence_ai_lineage.py",
    "src/app/domain/lotus_ai_attestation_replay.py",
    "migrations/012_ai_run_attestation_receipt.sql",
    "tests/unit/test_lotus_ai_run_attestation_verification.py",
    "tests/unit/test_ai_attestation_replay.py",
    "tests/integration/test_attested_ai_governance_api.py",
)

REMAINING_LOTUS_AI_ATTESTATION_BLOCKERS = (
    "lotus_ai_runtime_execution_missing",
    "certified_runtime_trust_telemetry_missing",
    "workbench_product_proof_missing",
    "supported_feature_promotion_missing",
)

REPOSITORY_OWNED_ATTESTATION_CHECKS = (
    "timezoneAwareGeneratedAtUtc",
    "consumerVerificationImplemented",
    "consumerReplayPersistenceImplemented",
)


def build_lotus_ai_attestation_contract_proof(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
    lotus_ai_root: Path | None = None,
) -> dict[str, Any]:
    lotus_ai_root = lotus_ai_root or repository_root.parent / "lotus-ai"
    timezone_aware = (
        generated_at_utc.tzinfo is not None and generated_at_utc.utcoffset() is not None
    )
    files_present = required_file_evidence_present(
        repository_root=repository_root,
        sibling_roots={"../lotus-ai/": lotus_ai_root},
        evidence_refs=REQUIRED_LOTUS_AI_ATTESTATION_EVIDENCE_REFS,
        non_file_ref_prefixes=(),
    )
    producer_contract_implemented = text_file_contains_all(
        lotus_ai_root / "src/app/contracts/workflow_run_attestation.py",
        ("WorkflowRunAttestationClaims", "model_risk_approval_ref", "replay_nonce"),
    )
    producer_signing_implemented = text_file_contains_all(
        lotus_ai_root / "src/app/services/workflow_run_attestation_signing.py",
        ("EdDSA", "signature_base64url", "canonical_attestation_payload"),
    )
    producer_issuance_fail_closed = text_file_contains_all(
        lotus_ai_root / "src/app/services/workflow_run_attestation_issuance.py",
        ("model_risk_status", "approval_ref", "stubbed"),
    )
    consumer_verification_implemented = text_file_contains_all(
        repository_root / "src/app/application/lotus_ai_run_attestation_verification.py",
        (
            "verify_lotus_ai_run_attestation",
            "select_trusted_ed25519_key",
            "signature_verifier.verify",
            "input digest",
            "output digest",
        ),
    )
    consumer_replay_persistence_implemented = (
        text_file_contains_all(
            repository_root / "src/app/domain/persistence_ai_lineage.py",
            ("LotusAIAttestationReplayIndex", "attestation_receipt"),
        )
        and text_file_contains_all(
            repository_root / "src/app/domain/lotus_ai_attestation_replay.py",
            ("_request_by_run_id", "_request_by_nonce", "conflicts"),
        )
        and text_file_contains_all(
            repository_root / "migrations/012_ai_run_attestation_receipt.sql",
            ("lotus_ai_run_id", "lotus_ai_replay_nonce", "CREATE UNIQUE INDEX"),
        )
    )
    local_contract_proof_valid = all(
        (
            timezone_aware,
            files_present,
            producer_contract_implemented,
            producer_signing_implemented,
            producer_issuance_fail_closed,
            consumer_verification_implemented,
            consumer_replay_persistence_implemented,
        )
    )
    return {
        "schemaVersion": LOTUS_AI_ATTESTATION_CONTRACT_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "lotus_ai_signed_run_attestation_contract",
        "proofScope": "source_safe_local_cross_repository_contract",
        "localContractProofValid": local_contract_proof_valid,
        "eligibleForMainlineCertification": local_contract_proof_valid,
        "mainlineValidated": False,
        "aggregateBlockersCleared": (),
        "remainingCertificationBlockers": REMAINING_LOTUS_AI_ATTESTATION_BLOCKERS,
        "evidenceRefs": REQUIRED_LOTUS_AI_ATTESTATION_EVIDENCE_REFS,
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": timezone_aware,
            "fileEvidencePresent": files_present,
            "producerContractImplemented": producer_contract_implemented,
            "producerSigningImplemented": producer_signing_implemented,
            "producerIssuanceFailClosed": producer_issuance_fail_closed,
            "consumerVerificationImplemented": consumer_verification_implemented,
            "consumerReplayPersistenceImplemented": consumer_replay_persistence_implemented,
        },
        "liveProviderExecuted": False,
        "workbenchProductProofCertified": False,
        "supportedFeaturePromoted": False,
    }


def lotus_ai_attestation_contract_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    if payload.get("schemaVersion") != LOTUS_AI_ATTESTATION_CONTRACT_PROOF_SCHEMA_VERSION:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("proofType") != "lotus_ai_signed_run_attestation_contract":
        return False
    if payload.get("proofScope") != "source_safe_local_cross_repository_contract":
        return False
    if payload.get("localContractProofValid") is not True:
        return False
    if payload.get("eligibleForMainlineCertification") is not True:
        return False
    if payload.get("mainlineValidated") is not False:
        return False
    if tuple(payload.get("aggregateBlockersCleared") or ()):
        return False
    if tuple(payload.get("remainingCertificationBlockers") or ()) != (
        REMAINING_LOTUS_AI_ATTESTATION_BLOCKERS
    ):
        return False
    if tuple(payload.get("evidenceRefs") or ()) != REQUIRED_LOTUS_AI_ATTESTATION_EVIDENCE_REFS:
        return False
    if not is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if payload.get("liveProviderExecuted") is not False:
        return False
    if payload.get("workbenchProductProofCertified") is not False:
        return False
    if payload.get("supportedFeaturePromoted") is not False:
        return False
    checks = payload.get("proofChecks")
    return isinstance(checks, Mapping) and all(value is True for value in checks.values())


def lotus_ai_attestation_consumer_contract_is_valid(payload: Mapping[str, Any]) -> bool:
    """Validate only controls owned by lotus-idea when producer source is unavailable."""
    checks = payload.get("proofChecks")
    return (
        payload.get("schemaVersion") == LOTUS_AI_ATTESTATION_CONTRACT_PROOF_SCHEMA_VERSION
        and payload.get("repository") == "lotus-idea"
        and payload.get("localContractProofValid") is False
        and payload.get("eligibleForMainlineCertification") is False
        and isinstance(checks, Mapping)
        and all(checks.get(check) is True for check in REPOSITORY_OWNED_ATTESTATION_CHECKS)
        and checks.get("fileEvidencePresent") is False
        and checks.get("producerContractImplemented") is False
        and checks.get("producerSigningImplemented") is False
        and checks.get("producerIssuanceFailClosed") is False
    )
