import json
from pathlib import Path

from scripts.generate_lotus_ai_attestation_contract_proof import main
from tests.support.lotus_ai_attestation_source_fixture import (
    materialize_lotus_ai_attestation_source,
)


def test_generator_writes_source_safe_local_proof(tmp_path: Path) -> None:
    output = tmp_path / "lotus-ai-attestation-contract-proof.json"
    lotus_ai_root = materialize_lotus_ai_attestation_source(tmp_path / "lotus-ai")

    result = main(
        [
            "--generated-at-utc",
            "2026-07-11T12:00:00Z",
            "--output",
            str(output),
            "--lotus-ai-root",
            str(lotus_ai_root),
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
