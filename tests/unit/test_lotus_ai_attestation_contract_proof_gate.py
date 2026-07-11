from pathlib import Path

from scripts.lotus_ai_attestation_contract_proof_gate import (
    validate_lotus_ai_attestation_contract_proof,
)


def test_gate_validates_consumer_contract_when_producer_checkout_is_unavailable(
    tmp_path: Path,
) -> None:
    missing_producer = tmp_path / "missing-lotus-ai"

    assert validate_lotus_ai_attestation_contract_proof(lotus_ai_root=missing_producer) == []
