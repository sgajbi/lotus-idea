from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any, cast


ROOT = Path(__file__).resolve().parents[2]


def _load_gate() -> ModuleType:
    path = ROOT / "scripts" / "service_slo_capacity_contract_gate.py"
    spec = importlib.util.spec_from_file_location("service_slo_capacity_contract_gate", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _payload(module: ModuleType) -> dict[str, Any]:
    return cast(dict[str, Any], module.load_contract())


def test_service_slo_capacity_contract_passes_current_foundation() -> None:
    module = _load_gate()

    assert module.validate_service_slo_capacity_contract() == []


def test_service_slo_capacity_contract_blocks_false_certification() -> None:
    module = _load_gate()
    payload = _payload(module)
    payload["certification_status"] = "certified"
    payload["supported_feature_promoted"] = True
    payload["service_objectives"][0]["certification_status"] = "certified"
    payload["certification_blockers"] = []

    errors = module.validate_payload(payload)

    assert "service SLO capacity contract certification_status must be 'not_certified'" in errors
    assert "service SLO capacity contract supported_feature_promoted must be False" in errors
    assert "api objective must remain baseline_required" in errors
    assert "service SLO certification blockers must match required evidence set" in errors


def test_service_slo_capacity_contract_rejects_invalid_objectives_and_capacity() -> None:
    module = _load_gate()
    payload = _payload(module)
    payload["service_objectives"][0]["availability_target"] = 1.0
    payload["service_objectives"][1]["latency_p95_seconds"] = 700.0
    payload["capacity_budgets"]["source_ingestion_batch_max_items"] = True
    payload["capacity_budgets"]["postgres_pool_utilization_warn_fraction"] = 0.95

    errors = module.validate_payload(payload)

    assert "api availability and error budget must be fractions" in errors
    assert "source_ingestion latency objectives must be positive and ordered" in errors
    assert any("batch_max_items must be a positive integer" in error for error in errors)
    assert "PostgreSQL utilization thresholds must be ordered fractions" in errors
    assert "source-ingestion capacity budget must match code-owned ceiling" in errors


def test_service_slo_capacity_contract_rejects_sensitive_labels_and_mesh_alias() -> None:
    module = _load_gate()
    payload = _payload(module)
    payload["metric_label_policy"]["allowed"].append("portfolio_id")
    payload["metric_label_policy"]["forbidden"] = []
    payload["source_of_truth"]["mesh_slo_contract"] = module.CONTRACT_PATH.as_posix()

    errors = module.validate_payload(payload)

    assert "service SLO metric labels contain sensitive keys: portfolio_id" in errors
    assert "service SLO forbidden metric labels must match governed deny set" in errors
    assert "service SLO contract must remain distinct from mesh data-product SLO" in errors


def test_service_slo_capacity_contract_rejects_recording_and_alert_rule_drift() -> None:
    module = _load_gate()
    malformed = """
      - record: lotus_idea:http_error_ratio:rate5m
        expr: lotus_idea_http_requests_total{portfolio_id='unsafe'}
      - alert: UnknownAlert
        expr: vector(1)
    """

    errors = module.validate_rule_text(malformed)

    assert "service SLO recording rules must match governed set" in errors
    assert "service SLO alert rules must match governed set" in errors
    assert "service SLO rules must consume lotus_idea_workflow_runs_total" in errors
    assert "service SLO rule expressions contain sensitive labels: portfolio_id" in errors


def test_service_slo_capacity_contract_rejects_incomplete_or_sensitive_dashboard() -> None:
    module = _load_gate()
    dashboard = {
        "uid": "wrong",
        "panels": [{"targets": [{"expr": "lotus_idea_http_requests_total{tenant_id='unsafe'}"}]}],
    }

    errors = module.validate_dashboard_payload(dashboard)

    assert "service SLO dashboard uid must be lotus-idea-service-slo" in errors
    assert "service SLO dashboard must contain all governed panels" in errors


def test_service_slo_capacity_contract_loader_rejects_non_object(tmp_path: Path) -> None:
    module = _load_gate()
    path = tmp_path / "contract.json"
    path.write_text(json.dumps([]), encoding="utf-8")

    try:
        module.load_contract(tmp_path, Path("contract.json"))
    except ValueError as error:
        assert str(error) == "service SLO capacity contract must be a JSON object"
    else:
        raise AssertionError("expected non-object contract to fail")
