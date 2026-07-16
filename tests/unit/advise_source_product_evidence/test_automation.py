from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.application.advise_source_product_evidence import (
    PROFILES,
    advise_source_product_source_contract_is_valid,
)
from scripts.advise_source_product_evidence import generate_source_contract
from scripts.advise_source_product_evidence.source_contract_gate import (
    validate_advise_source_product_source_contract,
)


ROOT = Path(__file__).resolve().parents[3]
ADVISE_FIXTURE_ROOT = ROOT / "tests/fixtures/advise_source_product_evidence/lotus-advise"


@pytest.mark.parametrize("capability", tuple(PROFILES))
def test_source_contract_gate_passes(capability: str) -> None:
    assert validate_advise_source_product_source_contract(capability) == []


@pytest.mark.parametrize("capability", tuple(PROFILES))
def test_generator_writes_valid_closed_source_contract(
    capability: str,
    tmp_path: Path,
) -> None:
    output = tmp_path / f"{capability}.json"

    exit_code = generate_source_contract.main(
        [
            "--capability",
            capability,
            "--generated-at-utc",
            "2026-07-16T10:10:00Z",
            "--advise-root",
            str(ADVISE_FIXTURE_ROOT),
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert advise_source_product_source_contract_is_valid(
        payload,
        profile=PROFILES[capability],
    )
    assert payload["aggregateProofProvenance"]["repository"] == "lotus-idea"
    assert payload["aggregateProofProvenance"]["proofRef"].endswith(f"{capability}.json")


@pytest.mark.parametrize("capability", tuple(PROFILES))
def test_generator_writes_invalid_non_proof_when_sibling_sources_are_absent(
    capability: str,
    tmp_path: Path,
) -> None:
    output = tmp_path / f"{capability}.json"

    exit_code = generate_source_contract.main(
        [
            "--capability",
            capability,
            "--generated-at-utc",
            "2026-07-16T10:10:00Z",
            "--advise-root",
            str(tmp_path / "missing"),
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["sourceContractValid"] is False
    assert not advise_source_product_source_contract_is_valid(
        payload,
        profile=PROFILES[capability],
    )
