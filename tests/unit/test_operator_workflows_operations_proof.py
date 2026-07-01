from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

from app.application.operator_workflows_operations_proof import (
    EXPECTED_ALERT_IDS,
    EXPECTED_DASHBOARD_OPERATIONS,
    EXPECTED_DASHBOARD_UID,
    EXPECTED_METRIC_NAME,
    OPERATOR_WORKFLOWS_OPERATIONS_BLOCKERS_CLEARED,
    OPERATOR_WORKFLOWS_OPERATIONS_PROOF_SCHEMA_VERSION,
    REMAINING_OPERATOR_WORKFLOWS_OPERATIONS_BLOCKERS,
    REQUIRED_OPERATOR_WORKFLOWS_OPERATIONS_EVIDENCE_REFS,
    _alert_rules_artifact_certified,
    _dashboard_artifact_certified,
    _operations_contract_certified,
    _runbook_artifact_certified,
    build_operator_workflows_operations_proof_payload,
    operator_workflows_operations_proof_is_valid,
)

ROOT = Path(__file__).resolve().parents[2]


def test_builds_source_safe_operator_workflows_operations_proof() -> None:
    proof = build_operator_workflows_operations_proof_payload(
        generated_at_utc=datetime(2026, 7, 1, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
    )

    assert proof["schemaVersion"] == OPERATOR_WORKFLOWS_OPERATIONS_PROOF_SCHEMA_VERSION
    assert proof["repository"] == "lotus-idea"
    assert proof["operatorWorkflowsOperationsProofValid"] is True
    assert tuple(proof["aggregateBlockersCleared"]) == (
        OPERATOR_WORKFLOWS_OPERATIONS_BLOCKERS_CLEARED
    )
    assert tuple(proof["evidenceRefs"]) == REQUIRED_OPERATOR_WORKFLOWS_OPERATIONS_EVIDENCE_REFS
    assert tuple(proof["remainingCertificationBlockers"]) == (
        REMAINING_OPERATOR_WORKFLOWS_OPERATIONS_BLOCKERS
    )
    assert proof["metricFamily"] == EXPECTED_METRIC_NAME
    assert proof["dashboardUid"] == EXPECTED_DASHBOARD_UID
    assert tuple(proof["alertIds"]) == EXPECTED_ALERT_IDS
    assert proof["operatorDashboardCertified"] is True
    assert proof["operatorAlertsCertified"] is True
    assert proof["liveSourceIngestionCertified"] is False
    assert proof["externalBrokerRuntimeCertified"] is False
    assert proof["downstreamExecutionOutcomeAuthorityCertified"] is False
    assert proof["dataMeshCertified"] is False
    assert proof["gatewayWorkbenchProofCertified"] is False
    assert proof["clientReadyPublicationAuthorized"] is False
    assert proof["supportedFeaturePromoted"] is False
    assert proof["proofClosed"] is False
    assert operator_workflows_operations_proof_is_valid(proof) is True
    serialized = json.dumps(proof)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "portfolioId" not in serialized
    assert "clientId" not in serialized
    assert "requestBody" not in serialized
    assert "responseBody" not in serialized


def test_rejects_operator_workflows_operations_proof_with_naive_timestamp() -> None:
    proof = build_operator_workflows_operations_proof_payload(
        generated_at_utc=datetime(2026, 7, 1, 0, 0),
        repository_root=ROOT,
    )

    assert proof["operatorWorkflowsOperationsProofValid"] is False
    assert operator_workflows_operations_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("schemaVersion", "wrong"),
        ("repository", "lotus-ai"),
        ("operatorWorkflowsOperationsProofValid", False),
        ("metricFamily", "local_metric_total"),
        ("dashboardUid", "local-dashboard"),
        ("alertIds", []),
        ("operatorDashboardCertified", False),
        ("operatorAlertsCertified", False),
        ("liveSourceIngestionCertified", True),
        ("externalBrokerRuntimeCertified", True),
        ("downstreamExecutionOutcomeAuthorityCertified", True),
        ("dataMeshCertified", True),
        ("gatewayWorkbenchProofCertified", True),
        ("clientReadyPublicationAuthorized", True),
        ("supportedFeaturePromoted", True),
        ("proofClosed", True),
        ("generatedAtUtc", "not-a-datetime"),
    ],
)
def test_rejects_operator_workflows_operations_proof_with_invalid_top_level_fields(
    field_name: str,
    bad_value: object,
) -> None:
    proof = _valid_operator_workflows_operations_proof()
    proof[field_name] = bad_value

    assert operator_workflows_operations_proof_is_valid(proof) is False


def test_rejects_operator_workflows_operations_proof_with_invalid_proof_checks() -> None:
    proof = _valid_operator_workflows_operations_proof()
    proof_checks = dict(cast(Mapping[str, object], proof["proofChecks"]))
    proof_checks["dashboardArtifactCertified"] = False
    proof["proofChecks"] = proof_checks

    assert operator_workflows_operations_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    "field_name",
    [
        "aggregateBlockersCleared",
        "evidenceRefs",
        "remainingCertificationBlockers",
    ],
)
def test_rejects_operator_workflows_operations_proof_with_invalid_blocker_lists(
    field_name: str,
) -> None:
    proof = _valid_operator_workflows_operations_proof()
    proof[field_name] = ()

    assert operator_workflows_operations_proof_is_valid(proof) is False


def test_rejects_operator_workflows_operations_proof_with_non_mapping_checks() -> None:
    proof = _valid_operator_workflows_operations_proof()
    proof["proofChecks"] = []

    assert operator_workflows_operations_proof_is_valid(proof) is False


def test_operator_workflows_operations_proof_cli_writes_valid_artifact(tmp_path: Path) -> None:
    module = _load_generator_script()
    output_path = tmp_path / "proof" / "operator-workflows-operations-proof.json"

    result = module.main(
        [
            "--generated-at-utc",
            "2026-07-01T00:00:00Z",
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    proof = json.loads(output_path.read_text(encoding="utf-8"))
    assert operator_workflows_operations_proof_is_valid(proof) is True


def test_operator_workflows_operations_proof_contract_gate_scans_tuple_content() -> None:
    module = _load_contract_gate_script()
    errors: list[str] = []

    module._validate_forbidden_content(("portfolio_id",), errors)

    assert errors == ["$[0]: forbidden source-sensitive text `portfolio_id` is present"]


def test_operator_workflows_operations_proof_contract_gate_passes_current_artifacts() -> None:
    module = _load_contract_gate_script()

    assert module.validate_operator_workflows_operations_proof_contract() == []


def test_artifact_certification_fails_closed(tmp_path: Path) -> None:
    assert _dashboard_artifact_certified(tmp_path) is False
    assert _alert_rules_artifact_certified(tmp_path) is False
    assert _runbook_artifact_certified(tmp_path) is False
    assert _operations_contract_certified(tmp_path) is False

    dashboard_path = (
        tmp_path / "monitoring/grafana/dashboards/lotus-idea-operator-workflows-operations.json"
    )
    dashboard_path.parent.mkdir(parents=True)
    dashboard_path.write_text('{"uid": "wrong"}', encoding="utf-8")

    assert _dashboard_artifact_certified(tmp_path) is False


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ({"title": "Wrong"}, False),
        ({"annotations": {"source": "portfolio_id"}}, False),
        (
            {
                "uid": EXPECTED_DASHBOARD_UID,
                "title": "Lotus Idea Operator Workflow Operations",
                "panels": [],
            },
            False,
        ),
    ],
)
def test_dashboard_artifact_certification_rejects_invalid_metadata(
    tmp_path: Path,
    mutation: dict[str, object],
    expected: bool,
) -> None:
    payload = _valid_dashboard_payload()
    payload.update(mutation)
    _write_dashboard_payload(tmp_path, payload)

    assert _dashboard_artifact_certified(tmp_path) is expected


def test_dashboard_artifact_certification_rejects_unexpected_metric(tmp_path: Path) -> None:
    payload = _valid_dashboard_payload()
    payload["panels"] = [
        {
            "targets": [
                {"expr": "sum(rate(lotus_local_operation_events_total[5m]))"},
            ],
        },
    ]
    _write_dashboard_payload(tmp_path, payload)

    assert _dashboard_artifact_certified(tmp_path) is False


def test_dashboard_artifact_certification_rejects_missing_operation(tmp_path: Path) -> None:
    payload = _valid_dashboard_payload()
    payload.pop("annotations")
    payload["panels"] = [
        {
            "targets": [
                {
                    "expr": f'{EXPECTED_METRIC_NAME}{{operation="{EXPECTED_DASHBOARD_OPERATIONS[0]}"}}',
                },
            ],
        }
        for _ in range(4)
    ]
    _write_dashboard_payload(tmp_path, payload)

    assert _dashboard_artifact_certified(tmp_path) is False


def test_alert_rules_artifact_certification_rejects_missing_runbook_refs(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path / "monitoring/prometheus/rules/lotus-idea-operator-workflows-operations.rules.yml"
    )
    path.parent.mkdir(parents=True)
    path.write_text("\n".join(f"alert_id: {alert_id}" for alert_id in EXPECTED_ALERT_IDS))

    assert _alert_rules_artifact_certified(tmp_path) is False


def test_alert_rules_artifact_certification_rejects_missing_alert_id(tmp_path: Path) -> None:
    path = (
        tmp_path / "monitoring/prometheus/rules/lotus-idea-operator-workflows-operations.rules.yml"
    )
    path.parent.mkdir(parents=True)
    path.write_text(
        "\n".join(
            f"docs/runbooks/operator-workflows-operations.md#{alert_id}"
            for alert_id in EXPECTED_ALERT_IDS
        )
        + "\n"
        + "\n".join(EXPECTED_DASHBOARD_OPERATIONS),
        encoding="utf-8",
    )

    assert _alert_rules_artifact_certified(tmp_path) is False


def test_runbook_artifact_certification_rejects_forbidden_and_missing_text(
    tmp_path: Path,
) -> None:
    path = tmp_path / "docs/runbooks/operator-workflows-operations.md"
    path.parent.mkdir(parents=True)
    path.write_text("portfolio_id", encoding="utf-8")
    assert _runbook_artifact_certified(tmp_path) is False

    path.write_text(
        "\n".join(f"## {alert_id}" for alert_id in EXPECTED_ALERT_IDS), encoding="utf-8"
    )
    assert _runbook_artifact_certified(tmp_path) is False


@pytest.mark.parametrize(
    "mutation",
    [
        {"dashboard_certified": False},
        {"alert_certified": False},
        {"source_of_truth": []},
        {
            "source_of_truth": {
                "dashboard": "wrong",
                "alert_rules": "monitoring/prometheus/rules/"
                "lotus-idea-operator-workflows-operations.rules.yml",
                "operator_runbook": "docs/runbooks/operator-workflows-operations.md",
                "proof_contract_gate": "scripts/operator_workflows_operations_proof_contract_gate.py",
            },
        },
        {"operator_dashboard_controls": [{"certification_status": "pending"}]},
        {"operator_alert_candidates": [{"certification_status": "pending"}]},
    ],
)
def test_operations_contract_certification_rejects_invalid_contract_fields(
    tmp_path: Path,
    mutation: dict[str, object],
) -> None:
    payload = _valid_operations_contract_payload()
    payload.update(mutation)
    path = tmp_path / "contracts/observability/lotus-idea-operator-workflows-operations.v1.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert _operations_contract_certified(tmp_path) is False


def _valid_operator_workflows_operations_proof() -> dict[str, object]:
    return build_operator_workflows_operations_proof_payload(
        generated_at_utc=datetime(2026, 7, 1, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
    )


def _valid_dashboard_payload() -> dict[str, object]:
    return {
        "uid": EXPECTED_DASHBOARD_UID,
        "title": "Lotus Idea Operator Workflow Operations",
        "panels": [
            {
                "targets": [
                    {
                        "expr": f'{EXPECTED_METRIC_NAME}{{operation="{operation}"}}',
                    },
                ],
            }
            for operation in EXPECTED_DASHBOARD_OPERATIONS[:4]
        ],
        "annotations": {"operations": list(EXPECTED_DASHBOARD_OPERATIONS)},
    }


def _write_dashboard_payload(tmp_path: Path, payload: Mapping[str, object]) -> None:
    path = tmp_path / "monitoring/grafana/dashboards/lotus-idea-operator-workflows-operations.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _valid_operations_contract_payload() -> dict[str, object]:
    return {
        "dashboard_certified": True,
        "alert_certified": True,
        "source_of_truth": {
            "dashboard": "monitoring/grafana/dashboards/lotus-idea-operator-workflows-operations.json",
            "alert_rules": "monitoring/prometheus/rules/"
            "lotus-idea-operator-workflows-operations.rules.yml",
            "operator_runbook": "docs/runbooks/operator-workflows-operations.md",
            "proof_contract_gate": "scripts/operator_workflows_operations_proof_contract_gate.py",
        },
        "operator_dashboard_controls": [{"certification_status": "certified"}],
        "operator_alert_candidates": [{"certification_status": "certified"}],
    }


def _load_generator_script() -> ModuleType:
    script_path = ROOT / "scripts" / "generate_operator_workflows_operations_proof.py"
    spec = importlib.util.spec_from_file_location(
        "generate_operator_workflows_operations_proof",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_contract_gate_script() -> ModuleType:
    script_path = ROOT / "scripts" / "operator_workflows_operations_proof_contract_gate.py"
    spec = importlib.util.spec_from_file_location(
        "operator_workflows_operations_proof_contract_gate",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
