from __future__ import annotations

from scripts.source_ingestion_scheduler.contract_gate import (
    validate_source_ingestion_scheduler_contracts,
)


def test_scheduler_contract_gate_passes_repository_truth() -> None:
    assert validate_source_ingestion_scheduler_contracts() == []
