import json
from pathlib import Path

from scripts.generate_lotus_ai_attestation_contract_proof import main


def test_generator_writes_source_safe_local_proof(tmp_path: Path) -> None:
    output = tmp_path / "lotus-ai-attestation-contract-proof.json"

    result = main(
        [
            "--generated-at-utc",
            "2026-07-11T12:00:00Z",
            "--output",
            str(output),
        ]
    )

    assert result == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["localContractProofValid"] is True
    assert payload["mainlineValidated"] is False
    assert payload["aggregateBlockersCleared"] == []


def test_generator_rejects_naive_timestamp(tmp_path: Path) -> None:
    assert (
        main(
            [
                "--generated-at-utc",
                "2026-07-11T12:00:00",
                "--output",
                str(tmp_path / "invalid.json"),
            ]
        )
        == 2
    )
