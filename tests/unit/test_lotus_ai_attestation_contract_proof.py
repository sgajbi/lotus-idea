from datetime import UTC, datetime
from pathlib import Path

from app.application.lotus_ai_attestation_contract_proof import (
    REMAINING_LOTUS_AI_ATTESTATION_BLOCKERS,
    build_lotus_ai_attestation_contract_proof,
    lotus_ai_attestation_contract_proof_is_valid,
)

ROOT = Path(__file__).resolve().parents[2]


def test_local_cross_repository_attestation_contract_is_source_proven() -> None:
    proof = build_lotus_ai_attestation_contract_proof(
        generated_at_utc=datetime(2026, 7, 11, 12, 0, tzinfo=UTC),
        repository_root=ROOT,
        lotus_ai_root=ROOT.parent / "lotus-ai",
    )

    assert lotus_ai_attestation_contract_proof_is_valid(proof)
    assert proof["aggregateBlockersCleared"] == ()
    assert proof["remainingCertificationBlockers"] == REMAINING_LOTUS_AI_ATTESTATION_BLOCKERS
    assert proof["mainlineValidated"] is False
    assert proof["liveProviderExecuted"] is False
    assert proof["supportedFeaturePromoted"] is False


def test_missing_producer_repository_fails_closed(tmp_path: Path) -> None:
    proof = build_lotus_ai_attestation_contract_proof(
        generated_at_utc=datetime(2026, 7, 11, 12, 0, tzinfo=UTC),
        repository_root=ROOT,
        lotus_ai_root=tmp_path / "missing-lotus-ai",
    )

    assert proof["localContractProofValid"] is False
    assert proof["eligibleForMainlineCertification"] is False
    assert not lotus_ai_attestation_contract_proof_is_valid(proof)
