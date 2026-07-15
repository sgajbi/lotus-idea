from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

from app.application.ai_attestation.source_contract import (
    idea_consumer_source_contract_is_valid,
    signed_ai_attestation_source_contract_is_valid,
)
from tests.support.ai_attestation.source_fixture import write_lotus_ai_attestation_source


ROOT = Path(__file__).resolve().parents[3]


def test_generator_writes_valid_full_source_contract(tmp_path: Path) -> None:
    output = tmp_path / "output" / "signed-ai-attestation-source-contract.json"
    result = _generator().main(
        [
            "--generated-at-utc",
            "2026-07-15T00:00:00Z",
            "--lotus-ai-root",
            str(write_lotus_ai_attestation_source(tmp_path / "lotus-ai")),
            "--output",
            str(output),
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert result == 0
    assert signed_ai_attestation_source_contract_is_valid(payload) is True


def test_generator_requires_explicit_missing_producer_posture(tmp_path: Path) -> None:
    output = tmp_path / "output" / "consumer-only.json"
    args = [
        "--generated-at-utc",
        "2026-07-15T00:00:00Z",
        "--lotus-ai-root",
        str(tmp_path / "missing-lotus-ai"),
        "--output",
        str(output),
    ]

    assert _generator().main(args) == 1
    assert _generator().main([*args, "--allow-missing-producer"]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert idea_consumer_source_contract_is_valid(payload) is True


def test_generator_rejects_naive_timestamp(tmp_path: Path) -> None:
    result = _generator().main(
        [
            "--generated-at-utc",
            "2026-07-15T00:00:00",
            "--lotus-ai-root",
            str(write_lotus_ai_attestation_source(tmp_path / "lotus-ai")),
        ]
    )

    assert result == 2


def test_contract_gate_validates_full_and_consumer_only_scopes(tmp_path: Path) -> None:
    gate = _gate()

    assert (
        gate.validate_ai_attestation_source_contract(
            lotus_ai_root=write_lotus_ai_attestation_source(tmp_path / "lotus-ai")
        )
        == []
    )
    assert (
        gate.validate_ai_attestation_source_contract(lotus_ai_root=tmp_path / "missing-lotus-ai")
        == []
    )


def test_contract_gate_source_safety_scans_nested_values() -> None:
    gate = _gate()
    errors: list[str] = []

    gate._validate_source_safety(("portfolio_id",), errors)

    assert errors == ["$[0]: forbidden source-sensitive text `portfolio_id` is present"]


def _generator() -> ModuleType:
    return _load("scripts/ai_attestation/generate_source_contract.py", "ai_attestation_generator")


def _gate() -> ModuleType:
    return _load("scripts/ai_attestation/source_contract_gate.py", "ai_attestation_gate")


def _load(relative_path: str, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
