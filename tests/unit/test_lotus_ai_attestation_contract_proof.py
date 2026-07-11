from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.application.lotus_ai_attestation_contract_proof import (
    REMAINING_LOTUS_AI_ATTESTATION_BLOCKERS,
    build_lotus_ai_attestation_contract_proof,
    lotus_ai_attestation_consumer_contract_is_valid,
    lotus_ai_attestation_contract_proof_is_valid,
)
from tests.support.lotus_ai_attestation_source_fixture import (
    materialize_lotus_ai_attestation_source,
)

ROOT = Path(__file__).resolve().parents[2]


def test_local_cross_repository_attestation_contract_is_source_proven(tmp_path: Path) -> None:
    lotus_ai_root = materialize_lotus_ai_attestation_source(tmp_path / "lotus-ai")
    proof = build_lotus_ai_attestation_contract_proof(
        generated_at_utc=datetime(2026, 7, 11, 12, 0, tzinfo=UTC),
        repository_root=ROOT,
        lotus_ai_root=lotus_ai_root,
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
    assert lotus_ai_attestation_consumer_contract_is_valid(proof)


def test_consumer_contract_rejects_missing_repository_owned_control(tmp_path: Path) -> None:
    proof = build_lotus_ai_attestation_contract_proof(
        generated_at_utc=datetime(2026, 7, 11, 12, 0, tzinfo=UTC),
        repository_root=ROOT,
        lotus_ai_root=tmp_path / "missing-lotus-ai",
    )
    proof["proofChecks"]["consumerReplayPersistenceImplemented"] = False

    assert not lotus_ai_attestation_consumer_contract_is_valid(proof)


@pytest.mark.parametrize(
    ("path", "invalid_value"),
    [
        (("schemaVersion",), "other-schema"),
        (("repository",), "other-repository"),
        (("proofType",), "other-proof"),
        (("proofScope",), "other-scope"),
        (("localContractProofValid",), False),
        (("eligibleForMainlineCertification",), False),
        (("mainlineValidated",), True),
        (("aggregateBlockersCleared",), ("unsupported-clearance",)),
        (("remainingCertificationBlockers",), ()),
        (("evidenceRefs",), ()),
        (("generatedAtUtc",), "not-a-timestamp"),
        (("liveProviderExecuted",), True),
        (("workbenchProductProofCertified",), True),
        (("supportedFeaturePromoted",), True),
    ],
)
def test_cross_repository_proof_rejects_inflated_or_tampered_claims(
    tmp_path: Path,
    path: tuple[str, ...],
    invalid_value: object,
) -> None:
    lotus_ai_root = materialize_lotus_ai_attestation_source(tmp_path / "lotus-ai")
    proof = build_lotus_ai_attestation_contract_proof(
        generated_at_utc=datetime(2026, 7, 11, 12, 0, tzinfo=UTC),
        repository_root=ROOT,
        lotus_ai_root=lotus_ai_root,
    )
    tampered = deepcopy(proof)
    tampered[path[0]] = invalid_value

    assert not lotus_ai_attestation_contract_proof_is_valid(tampered)
