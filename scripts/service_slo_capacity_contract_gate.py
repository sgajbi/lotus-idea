# ruff: noqa: E402
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any, TypeGuard


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.outbox.delivery import (  # noqa: E402
    OUTBOX_DELIVERY_RUN_ONCE_BATCH_CEILING,
)
from app.application.source_ingestion import (  # noqa: E402
    SOURCE_INGESTION_RUN_ONCE_BATCH_CEILING,
)
from app.application.service_capacity_baseline import SCENARIOS  # noqa: E402
from app.application.capacity_evidence_qualification import (  # noqa: E402
    LOAD_SOAK_SCENARIO_THRESHOLDS,
    MINIMUM_LOAD_SOAK_SAMPLES,
)
from app.contracts.operational_limits import (  # noqa: E402
    DEFAULT_DEPENDENCY_MAX_CONNECTIONS,
    DEFAULT_DEPENDENCY_MAX_KEEPALIVE_CONNECTIONS,
    DEFAULT_DEPENDENCY_TIMEOUT_SECONDS,
    DEFAULT_HTTP_REQUEST_BODY_MAX_BYTES,
    DEFAULT_OUTBOX_DELIVERY_MAX_RETRY_COUNT,
)
from app.domain.capacity_posture import (  # noqa: E402
    POSTGRES_CONNECTION_UTILIZATION_SHED_FRACTION,
    POSTGRES_CONNECTION_UTILIZATION_WARN_FRACTION,
)
from service_capacity_workflow_contract import (  # noqa: E402
    validate_capacity_attestation_workflows,
    validate_dependency_recovery_workflow,
    validate_load_soak_workflow,
)

CONTRACT_PATH = Path("contracts/observability/lotus-idea-service-slo-capacity.v1.json")
EXPECTED_WORKFLOWS = {
    "api",
    "source_ingestion",
    "outbox_delivery",
    "downstream_submission",
    "postgresql",
}
REQUIRED_BLOCKERS = {
    "load_soak_attestation_missing",
    "dependency_recovery_attestation_missing",
    "postgres_saturation_evidence_missing",
    "production_like_resource_attestation_missing",
    "cost_attribution_evidence_missing",
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
    "LotusIdeaPostgresCapacityCollectionUnavailable",
    "LotusIdeaPostgresCapacityWarning",
    "LotusIdeaPostgresCapacityShedActive",
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
    errors.extend(_validate_dashboard(payload, repository_root))
    errors.extend(_validate_capacity_attestation_workflow(repository_root))
    errors.extend(_validate_downstream_capacity_seed(repository_root))
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
        expected = LOAD_SOAK_SCENARIO_THRESHOLDS.get(workflow)
        if expected is not None and (error_budget, p95, p99) != expected:
            errors.append(f"{workflow} objective must match code-owned load soak thresholds")
    applicability = payload.get("applicability")
    if (
        not isinstance(applicability, dict)
        or applicability.get("minimum_request_volume") != MINIMUM_LOAD_SOAK_SAMPLES
    ):
        errors.append("service SLO minimum request volume must match load soak qualification")
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
    if capacity.get("source_ingestion_batch_max_items") != SOURCE_INGESTION_RUN_ONCE_BATCH_CEILING:
        errors.append("source-ingestion capacity budget must match code-owned ceiling")
    if capacity.get("outbox_delivery_batch_max_items") != OUTBOX_DELIVERY_RUN_ONCE_BATCH_CEILING:
        errors.append("outbox-delivery capacity budget must match code-owned ceiling")
    code_owned_limits = {
        "outbox_max_retry_count": DEFAULT_OUTBOX_DELIVERY_MAX_RETRY_COUNT,
        "source_dependency_timeout_seconds": DEFAULT_DEPENDENCY_TIMEOUT_SECONDS,
        "source_dependency_max_connections": DEFAULT_DEPENDENCY_MAX_CONNECTIONS,
        "source_dependency_max_keepalive_connections": (
            DEFAULT_DEPENDENCY_MAX_KEEPALIVE_CONNECTIONS
        ),
        "request_body_max_bytes": DEFAULT_HTTP_REQUEST_BODY_MAX_BYTES,
    }
    for key, expected in code_owned_limits.items():
        if capacity.get(key) != expected:
            errors.append(f"service SLO capacity {key} must match code-owned default")
    warn = capacity.get("postgres_pool_utilization_warn_fraction")
    shed = capacity.get("postgres_pool_utilization_shed_fraction")
    if not _fraction(warn) or not _fraction(shed) or warn >= shed:
        errors.append("PostgreSQL utilization thresholds must be ordered fractions")
    if warn != POSTGRES_CONNECTION_UTILIZATION_WARN_FRACTION:
        errors.append("PostgreSQL warning threshold must match code-owned default")
    if shed != POSTGRES_CONNECTION_UTILIZATION_SHED_FRACTION:
        errors.append("PostgreSQL shed threshold must match code-owned default")
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
        "capacity_metric_source",
        "recording_alert_rules",
        "rule_tests",
        "dashboard",
        "contract_gate",
        "baseline_evidence_model",
        "baseline_generator",
        "baseline_contract_gate",
        "baseline_workload_runner",
        "downstream_capacity_seed_model",
        "downstream_capacity_seed_port",
        "downstream_capacity_seed_adapter",
        "downstream_capacity_seed_runner",
        "resource_evidence_model",
        "resource_probe_port",
        "resource_probe_adapter",
        "resource_baseline_runner",
        "resource_baseline_contract_gate",
        "resource_proof_gate",
        "resource_attestation_workflow",
        "postgres_threshold_proof_model",
        "postgres_threshold_proof_adapter",
        "postgres_threshold_proof_runner",
        "postgres_threshold_attestation_workflow",
        "postgres_threshold_attestation_verifier",
        "postgres_threshold_qualification_model",
        "dependency_recovery_attestation_workflow",
        "load_soak_attestation_workflow",
        "load_soak_proof_gate",
        "operations_doc",
        "operations_wiki",
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


def _validate_capacity_attestation_workflow(repository_root: Path) -> list[str]:
    return validate_capacity_attestation_workflows(repository_root)


def _validate_dependency_recovery_workflow(repository_root: Path) -> list[str]:
    return validate_dependency_recovery_workflow(repository_root)


def _validate_load_soak_workflow(repository_root: Path) -> list[str]:
    return validate_load_soak_workflow(repository_root)


def _validate_certification(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if set(payload.get("certification_blockers", [])) != REQUIRED_BLOCKERS:
        errors.append("service SLO certification blockers must match required evidence set")
    if payload.get("capacity_evidence_scenarios") != list(SCENARIOS):
        errors.append("service SLO capacity evidence scenarios must match runtime vocabulary")
    boundaries = payload.get("non_proof_boundaries")
    if not isinstance(boundaries, list) or len(boundaries) < 4:
        errors.append("service SLO non_proof_boundaries must remain explicit")
    return errors


def _validate_downstream_capacity_seed(repository_root: Path) -> list[str]:
    required_tokens = {
        "src/app/application/downstream_capacity_seed.py": (
            "seed_only_not_capacity_evidence",
            'productionCapacityCertified": False',
            'supportedFeaturePromoted": False',
        ),
        "src/app/infrastructure/http_downstream_capacity_seed.py": (
            "CAPACITY_SYNTHETIC_PORTFOLIO_001",
            "MAX_RESPONSE_BYTES",
            "idea.conversion.intent.record",
        ),
        "scripts/seed_downstream_capacity_resource.py": (
            "SEED_SYNTHETIC_LOTUS_IDEA_CAPACITY_RESOURCE",
            "_write_json_atomic",
        ),
        "scripts/run_service_capacity_workload.py": (
            "--downstream-capacity-seed",
            "downstream capacity seed provenance is invalid",
        ),
        "Makefile": (
            "downstream-capacity-seed:",
            "SERVICE_CAPACITY_DOWNSTREAM_SEED_ARG",
        ),
    }
    errors: list[str] = []
    for relative_path, tokens in required_tokens.items():
        path = repository_root / relative_path
        if not path.is_file():
            errors.append(f"downstream capacity seed source missing {relative_path}")
            continue
        content = path.read_text(encoding="utf-8")
        errors.extend(
            f"downstream capacity seed source {relative_path} missing {token!r}"
            for token in tokens
            if token not in content
        )
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


def _validate_dashboard(payload: dict[str, Any], repository_root: Path) -> list[str]:
    source = payload.get("source_of_truth")
    if not isinstance(source, dict) or not isinstance(source.get("dashboard"), str):
        return []
    path = repository_root / source["dashboard"]
    if not path.is_file():
        return []
    dashboard = json.loads(path.read_text(encoding="utf-8"))
    return validate_dashboard_payload(dashboard)


def validate_dashboard_payload(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return ["service SLO dashboard must be a JSON object"]
    errors: list[str] = []
    if payload.get("uid") != "lotus-idea-service-slo":
        errors.append("service SLO dashboard uid must be lotus-idea-service-slo")
    panels = payload.get("panels")
    if not isinstance(panels, list) or len(panels) < 9:
        return [*errors, "service SLO dashboard must contain all governed panels"]
    expressions = " ".join(
        str(target.get("expr", ""))
        for panel in panels
        if isinstance(panel, dict)
        for target in panel.get("targets", [])
        if isinstance(target, dict)
    )
    for metric in (
        "lotus_idea:http_error_ratio:rate6h",
        "lotus_idea_http_request_duration_seconds_bucket",
        "lotus_idea_workflow_duration_seconds_bucket",
        "lotus_idea_dependency_requests_total",
        "lotus_idea_postgres_operations_total",
        "lotus_idea_postgres_connection_utilization_ratio",
        "lotus_idea_postgres_capacity_posture",
        "lotus_idea_postgres_capacity_collection_success",
        "lotus_idea_outbox_delivery_oldest_ready_age_seconds",
    ):
        if metric not in expressions:
            errors.append(f"service SLO dashboard must consume {metric}")
    leaked = sorted(label for label in FORBIDDEN_LABELS if label in expressions)
    if leaked:
        errors.append(
            f"service SLO dashboard expressions contain sensitive labels: {', '.join(leaked)}"
        )
    return errors


def _fraction(value: Any) -> TypeGuard[int | float]:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and 0 < value < 1


def _positive_number(value: Any) -> TypeGuard[int | float]:
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
