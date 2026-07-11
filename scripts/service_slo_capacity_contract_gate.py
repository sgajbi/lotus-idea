from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = Path("contracts/observability/lotus-idea-service-slo-capacity.v1.json")
EXPECTED_WORKFLOWS = {
    "api",
    "source_ingestion",
    "outbox_delivery",
    "downstream_submission",
    "postgresql",
}
REQUIRED_BLOCKERS = {
    "workflow_sli_metrics_incomplete",
    "slo_dashboard_missing",
    "load_and_soak_baseline_missing",
    "dependency_failure_baseline_missing",
    "postgres_saturation_evidence_missing",
    "cost_resource_baseline_missing",
}
FORBIDDEN_LABELS = {
    "candidate_id",
    "client_id",
    "correlation_id",
    "event_id",
    "idempotency_key",
    "portfolio_id",
    "request_id",
    "tenant_id",
    "trace_id",
}
REQUIRED_RECORDING_RULES = {
    "lotus_idea:http_error_ratio:rate5m",
    "lotus_idea:http_error_ratio:rate1h",
    "lotus_idea:http_error_ratio:rate30m",
    "lotus_idea:http_error_ratio:rate6h",
    "lotus_idea:workflow_error_ratio:rate5m",
    "lotus_idea:workflow_error_ratio:rate1h",
}
REQUIRED_ALERT_RULES = {
    "LotusIdeaApiErrorBudgetFastBurn",
    "LotusIdeaApiErrorBudgetSlowBurn",
    "LotusIdeaSourceIngestionErrorBudgetFastBurn",
    "LotusIdeaOutboxDeliveryErrorBudgetFastBurn",
}


def load_contract(
    repository_root: Path = ROOT,
    contract_path: Path = CONTRACT_PATH,
) -> dict[str, Any]:
    path = contract_path if contract_path.is_absolute() else repository_root / contract_path
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("service SLO capacity contract must be a JSON object")
    return payload


def validate_service_slo_capacity_contract(
    *,
    repository_root: Path = ROOT,
    contract_path: Path = CONTRACT_PATH,
) -> list[str]:
    return validate_payload(
        load_contract(repository_root, contract_path),
        repository_root=repository_root,
    )


def validate_payload(
    payload: dict[str, Any],
    *,
    repository_root: Path = ROOT,
) -> list[str]:
    errors = _validate_header(payload)
    errors.extend(_validate_objectives(payload))
    errors.extend(_validate_capacity(payload))
    errors.extend(_validate_labels(payload))
    errors.extend(_validate_source_truth(payload, repository_root))
    errors.extend(_validate_rule_file(payload, repository_root))
    errors.extend(_validate_certification(payload))
    return sorted(errors)


def _validate_header(payload: dict[str, Any]) -> list[str]:
    expected = {
        "contract_id": "lotus-idea-service-slo-capacity",
        "contract_version": "1.0.0",
        "repository": "lotus-idea",
        "lifecycle_status": "implemented_contract_foundation",
        "certification_status": "not_certified",
        "supported_feature_promoted": False,
    }
    return [
        f"service SLO capacity contract {key} must be {value!r}"
        for key, value in expected.items()
        if payload.get(key) != value
    ]


def _validate_objectives(payload: dict[str, Any]) -> list[str]:
    objectives = payload.get("service_objectives")
    if not isinstance(objectives, list):
        return ["service SLO capacity service_objectives must be a list"]
    errors: list[str] = []
    workflows = {item.get("workflow") for item in objectives if isinstance(item, dict)}
    if workflows != EXPECTED_WORKFLOWS:
        errors.append("service SLO capacity workflows must match governed workflow set")
    for objective in objectives:
        if not isinstance(objective, dict):
            errors.append("service SLO capacity objective must be an object")
            continue
        workflow = objective.get("workflow", "unknown")
        availability = objective.get("availability_target")
        error_budget = objective.get("error_budget_fraction")
        p95 = objective.get("latency_p95_seconds")
        p99 = objective.get("latency_p99_seconds")
        if not _fraction(availability) or not _fraction(error_budget):
            errors.append(f"{workflow} availability and error budget must be fractions")
        elif abs((1.0 - availability) - error_budget) > 1e-9:
            errors.append(f"{workflow} error budget must equal one minus availability")
        if not _positive_number(p95) or not _positive_number(p99) or p99 < p95:
            errors.append(f"{workflow} latency objectives must be positive and ordered")
        if objective.get("certification_status") != "baseline_required":
            errors.append(f"{workflow} objective must remain baseline_required")
    return errors


def _validate_capacity(payload: dict[str, Any]) -> list[str]:
    capacity = payload.get("capacity_budgets")
    if not isinstance(capacity, dict):
        return ["service SLO capacity capacity_budgets must be an object"]
    errors: list[str] = []
    for key in (
        "source_ingestion_batch_max_items",
        "outbox_delivery_batch_max_items",
        "outbox_max_retry_count",
        "request_body_max_bytes",
    ):
        value = capacity.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            errors.append(f"service SLO capacity {key} must be a positive integer")
    warn = capacity.get("postgres_pool_utilization_warn_fraction")
    shed = capacity.get("postgres_pool_utilization_shed_fraction")
    if not _fraction(warn) or not _fraction(shed) or warn >= shed:
        errors.append("PostgreSQL utilization thresholds must be ordered fractions")
    if capacity.get("capacity_posture") != "baseline_required":
        errors.append("service SLO capacity posture must remain baseline_required")
    return errors


def _validate_labels(payload: dict[str, Any]) -> list[str]:
    policy = payload.get("metric_label_policy")
    if not isinstance(policy, dict):
        return ["service SLO capacity metric_label_policy must be an object"]
    allowed = set(policy.get("allowed", []))
    forbidden = set(policy.get("forbidden", []))
    errors: list[str] = []
    leaked = allowed & FORBIDDEN_LABELS
    if leaked:
        errors.append(
            f"service SLO metric labels contain sensitive keys: {', '.join(sorted(leaked))}"
        )
    if forbidden != FORBIDDEN_LABELS:
        errors.append("service SLO forbidden metric labels must match governed deny set")
    return errors


def _validate_source_truth(payload: dict[str, Any], repository_root: Path) -> list[str]:
    source = payload.get("source_of_truth")
    if not isinstance(source, dict):
        return ["service SLO capacity source_of_truth must be an object"]
    required = {
        "mesh_slo_contract",
        "operation_metric_contract",
        "sli_metric_source",
        "recording_alert_rules",
        "rule_tests",
        "contract_gate",
        "operations_doc",
        "rfc_slice",
    }
    errors: list[str] = []
    if set(source) != required:
        errors.append("service SLO capacity source_of_truth must use governed keys")
    if source.get("mesh_slo_contract") == CONTRACT_PATH.as_posix():
        errors.append("service SLO contract must remain distinct from mesh data-product SLO")
    for key, raw_path in source.items():
        path = Path(raw_path) if isinstance(raw_path, str) else Path("missing")
        if path.is_absolute() or ".." in path.parts:
            errors.append(f"service SLO source_of_truth.{key} must stay repository-relative")
        elif not (repository_root / path).is_file():
            errors.append(f"service SLO source_of_truth.{key} path missing")
    return errors


def _validate_certification(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if set(payload.get("certification_blockers", [])) != REQUIRED_BLOCKERS:
        errors.append("service SLO certification blockers must match required evidence set")
    boundaries = payload.get("non_proof_boundaries")
    if not isinstance(boundaries, list) or len(boundaries) < 4:
        errors.append("service SLO non_proof_boundaries must remain explicit")
    return errors


def _validate_rule_file(payload: dict[str, Any], repository_root: Path) -> list[str]:
    source = payload.get("source_of_truth")
    if not isinstance(source, dict):
        return []
    raw_path = source.get("recording_alert_rules")
    if not isinstance(raw_path, str):
        return []
    path = repository_root / raw_path
    if not path.is_file():
        return []
    return validate_rule_text(path.read_text(encoding="utf-8"))


def validate_rule_text(rule_text: str) -> list[str]:
    records = set(re.findall(r"^\s*-\s+record:\s+(\S+)\s*$", rule_text, re.MULTILINE))
    alerts = set(re.findall(r"^\s*-\s+alert:\s+(\S+)\s*$", rule_text, re.MULTILINE))
    errors: list[str] = []
    if records != REQUIRED_RECORDING_RULES:
        errors.append("service SLO recording rules must match governed set")
    if alerts != REQUIRED_ALERT_RULES:
        errors.append("service SLO alert rules must match governed set")
    for metric in (
        "lotus_idea_http_requests_total",
        "lotus_idea_workflow_runs_total",
    ):
        if metric not in rule_text:
            errors.append(f"service SLO rules must consume {metric}")
    leaked = sorted(label for label in FORBIDDEN_LABELS if label in rule_text)
    if leaked:
        errors.append(f"service SLO rule expressions contain sensitive labels: {', '.join(leaked)}")
    return errors


def _fraction(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and 0 < value < 1


def _positive_number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and value > 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate service SLO and capacity contract")
    parser.add_argument("--contract-path", type=Path, default=CONTRACT_PATH)
    args = parser.parse_args()
    errors = validate_service_slo_capacity_contract(contract_path=args.contract_path)
    if errors:
        print("Service SLO capacity contract gate failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Service SLO capacity contract gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
