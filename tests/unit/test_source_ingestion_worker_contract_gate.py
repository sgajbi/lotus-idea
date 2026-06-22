from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def _load_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "source_ingestion_worker_contract_gate.py"
    spec = importlib.util.spec_from_file_location(
        "source_ingestion_worker_contract_gate",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_source_ingestion_worker_contract_gate_passes_current_manifest() -> None:
    module = _load_gate()

    assert module.validate_source_ingestion_worker_contract() == []


def test_source_ingestion_worker_contract_gate_blocks_source_sensitive_fields() -> None:
    module = _load_gate()
    summary: dict[str, Any] = {
        "schemaVersion": module.MANIFEST_SCHEMA_VERSION,
        "mode": "check_only",
        "sourceAuthority": "lotus-core",
        "evaluatedAtUtc": "2026-06-21T10:00:00+00:00",
        "actorSubject": "signal-ingestion-worker",
        "maxItems": 100,
        "workItemCount": 1,
        "workItems": [
            {
                "itemIndex": 0,
                "asOfDate": "2026-06-21",
                "hasExplicitIdempotencyKey": False,
                "hasDuplicateOfCandidateId": False,
                "portfolioId": "PB_SG_GLOBAL_BAL_001",
                "idempotencyKey": "signal-ingestion:high-cash:lotus-core:raw",
            }
        ],
    }
    errors: list[str] = []

    module._validate_forbidden_content(summary, errors)

    assert "$.workItems[0].portfolioId: forbidden source-sensitive key is present" in errors
    assert "$.workItems[0].idempotencyKey: forbidden source-sensitive key is present" in errors
    assert (
        "$.workItems[0].portfolioId: forbidden source-sensitive text `PB_SG_GLOBAL_BAL_001` "
        "is present"
    ) in errors
    assert (
        "$.workItems[0].idempotencyKey: forbidden source-sensitive text "
        "`signal-ingestion:high-cash:lotus-core` is present"
    ) in errors


def test_source_ingestion_worker_contract_gate_blocks_candidate_ids_in_check_only() -> None:
    module = _load_gate()
    errors: list[str] = []

    module._validate_forbidden_content(
        {
            "workItems": [
                {
                    "itemIndex": 0,
                    "candidateId": "idea_high_cash_candidate",
                }
            ]
        },
        errors,
    )

    assert "$.workItems[0].candidateId: forbidden source-sensitive key is present" in errors


def test_source_ingestion_worker_contract_gate_reports_key_shape_drift(
    monkeypatch: Any,
) -> None:
    module = _load_gate()

    class DriftedPlan:
        def check_summary(self) -> dict[str, Any]:
            return {
                "schemaVersion": module.MANIFEST_SCHEMA_VERSION,
                "mode": "check_only",
                "sourceAuthority": "lotus-core",
                "evaluatedAtUtc": "2026-06-21T10:00:00+00:00",
                "actorSubject": "signal-ingestion-worker",
                "maxItems": 100,
                "workItemCount": 1,
                "workItems": [
                    {
                        "itemIndex": 0,
                        "asOfDate": "2026-06-21",
                        "hasExplicitIdempotencyKey": False,
                    }
                ],
            }

    monkeypatch.setattr(
        module,
        "source_ingestion_worker_plan_from_manifest",
        lambda _manifest: DriftedPlan(),
    )

    errors = module.validate_source_ingestion_worker_contract()

    assert (
        "workItems[0] keys must be ['asOfDate', 'hasDuplicateOfCandidateId', "
        "'hasExplicitIdempotencyKey', 'itemIndex']; got "
        "['asOfDate', 'hasExplicitIdempotencyKey', 'itemIndex']"
    ) in errors
