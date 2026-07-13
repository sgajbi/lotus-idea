from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any

from app.application.source_safe_cross_repo_proof import (
    is_timezone_aware_datetime_text,
    read_text,
    required_file_evidence_present,
    required_make_target_evidence_present,
)
from app.observability import OPERATION_EVENT_SOURCE_AUTHORITIES

OPERATOR_WORKFLOWS_OPERATIONS_PROOF_SCHEMA_VERSION = (
    "lotus-idea.operator-workflows-operations-proof.v1"
)
OPERATOR_WORKFLOWS_OPERATIONS_PROOF_ENV = "LOTUS_IDEA_OPERATOR_WORKFLOWS_OPERATIONS_PROOF"
OPERATOR_WORKFLOWS_OPERATIONS_BLOCKERS_CLEARED = (
    "operator_workflow_dashboard_not_certified",
    "operator_workflow_alerts_not_certified",
)
REMAINING_OPERATOR_WORKFLOWS_OPERATIONS_BLOCKERS = (
    "live_source_ingestion_certification_missing",
    "external_broker_runtime_proof_missing",
    "downstream_execution_outcome_authority_missing",
    "data_mesh_certification_missing",
    "gateway_workbench_proof_missing",
    "supported_feature_promotion_missing",
)
REQUIRED_OPERATOR_WORKFLOWS_OPERATIONS_EVIDENCE_REFS = (
    "contracts/observability/lotus-idea-operator-workflows-operations.v1.json",
    "contracts/observability/lotus-idea-operation-metrics.v1.json",
    "contracts/observability/lotus-idea-outbox-supportability.v1.json",
    "monitoring/grafana/dashboards/lotus-idea-operator-workflows-operations.json",
    "monitoring/prometheus/rules/lotus-idea-operator-workflows-operations.rules.yml",
    "monitoring/prometheus/tests/lotus-idea-outbox-supportability.test.yml",
    "docs/runbooks/operator-workflows-operations.md",
    "src/app/observability/logging.py",
    "src/app/observability/outbox/supportability.py",
    "tests/unit/test_operator_workflows_operations_proof.py",
    "make operator-workflows-ops-contract-gate",
    "make outbox-supportability-contract-gate",
    "make outbox-supportability-rule-test",
    "make operator-workflows-operations-proof-contract-gate",
)
EXPECTED_METRIC_NAME = "lotus_idea_operation_events_total"
EXPECTED_OUTBOX_SUPPORTABILITY_METRICS = (
    "lotus_idea_outbox_delivery_events",
    "lotus_idea_outbox_delivery_oldest_ready_age_seconds",
    "lotus_idea_outbox_delivery_configuration_ready",
    "lotus_idea_outbox_delivery_collection_success",
)
EXPECTED_DASHBOARD_UID = "lotus-idea-operator-workflows-operations"
EXPECTED_ALERT_IDS = (
    "source-ingestion-readiness-blocked",
    "outbox-delivery-readiness-blocked",
    "outbox-delivery-collection-failed",
    "outbox-delivery-dead-letter-present",
    "outbox-delivery-expired-lease-present",
    "outbox-delivery-backlog-stalled",
    "outbox-delivery-retry-pressure",
    "downstream-realization-readiness-blocked",
    "implementation-proof-readiness-blocked",
)
EXPECTED_DASHBOARD_OPERATIONS = (
    "source_ingestion_readiness_read",
    "source_ingestion_run_once",
    "outbox_delivery_readiness_read",
    "outbox_delivery_run_once",
    "downstream_realization_readiness_read",
    "downstream_realization_submission",
    "mesh_readiness_read",
    "mesh_trust_telemetry_preview_read",
    "mesh_trust_telemetry_snapshot_read",
    "implementation_proof_readiness_read",
)
FORBIDDEN_OBSERVABILITY_FRAGMENTS = (
    "account_id",
    "candidate_id",
    "client_id",
    "client_name",
    "conversion_intent_id",
    "correlation_id",
    "holding_id",
    "idempotency_key",
    "portfolio_id",
    "raw payload",
    "request_body",
    "response_body",
    "source_payload",
    "trace_id",
    "PB_SG_GLOBAL_BAL_001",
)
SOURCE_AUTHORITY_MATCHER = re.compile(r'source_authority\s*=~?\s*\\?"([^"\\]+)\\?"')


def build_operator_workflows_operations_proof_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
) -> dict[str, Any]:
    evidence_refs = tuple(REQUIRED_OPERATOR_WORKFLOWS_OPERATIONS_EVIDENCE_REFS)
    timezone_aware_generated_at_utc = (
        generated_at_utc.tzinfo is not None and generated_at_utc.utcoffset() is not None
    )
    file_evidence_present = required_file_evidence_present(
        repository_root=repository_root,
        sibling_roots={},
        evidence_refs=evidence_refs,
        non_file_ref_prefixes=("make ",),
    )
    make_target_evidence_present = required_make_target_evidence_present(
        repository_root=repository_root,
        evidence_refs=evidence_refs,
    )
    dashboard_certified = _dashboard_artifact_certified(repository_root)
    alert_rules_certified = _alert_rules_artifact_certified(repository_root)
    runbook_certified = _runbook_artifact_certified(repository_root)
    operations_contract_certified = _operations_contract_certified(repository_root)
    proof_valid = (
        timezone_aware_generated_at_utc
        and file_evidence_present
        and make_target_evidence_present
        and dashboard_certified
        and alert_rules_certified
        and runbook_certified
        and operations_contract_certified
    )
    return {
        "schemaVersion": OPERATOR_WORKFLOWS_OPERATIONS_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "operator_workflows_dashboard_alert_certification",
        "proofScope": "source_safe_operations_artifact_certification",
        "operatorWorkflowsOperationsProofValid": proof_valid,
        "aggregateBlockersCleared": OPERATOR_WORKFLOWS_OPERATIONS_BLOCKERS_CLEARED,
        "evidenceRefs": evidence_refs,
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": timezone_aware_generated_at_utc,
            "fileEvidencePresent": file_evidence_present,
            "makeTargetEvidencePresent": make_target_evidence_present,
            "dashboardArtifactCertified": dashboard_certified,
            "alertRulesArtifactCertified": alert_rules_certified,
            "runbookArtifactCertified": runbook_certified,
            "operationsContractCertified": operations_contract_certified,
        },
        "remainingCertificationBlockers": REMAINING_OPERATOR_WORKFLOWS_OPERATIONS_BLOCKERS,
        "metricFamily": EXPECTED_METRIC_NAME,
        "outboxSupportabilityMetricFamilies": EXPECTED_OUTBOX_SUPPORTABILITY_METRICS,
        "dashboardUid": EXPECTED_DASHBOARD_UID,
        "alertIds": EXPECTED_ALERT_IDS,
        "operatorDashboardCertified": proof_valid,
        "operatorAlertsCertified": proof_valid,
        "liveSourceIngestionCertified": False,
        "externalBrokerRuntimeCertified": False,
        "downstreamExecutionOutcomeAuthorityCertified": False,
        "dataMeshCertified": False,
        "gatewayWorkbenchProofCertified": False,
        "clientReadyPublicationAuthorized": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }


def operator_workflows_operations_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    expected_false_fields = (
        "liveSourceIngestionCertified",
        "externalBrokerRuntimeCertified",
        "downstreamExecutionOutcomeAuthorityCertified",
        "dataMeshCertified",
        "gatewayWorkbenchProofCertified",
        "clientReadyPublicationAuthorized",
        "supportedFeaturePromoted",
        "proofClosed",
    )
    expected_values = {
        "schemaVersion": OPERATOR_WORKFLOWS_OPERATIONS_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofType": "operator_workflows_dashboard_alert_certification",
        "proofScope": "source_safe_operations_artifact_certification",
        "operatorWorkflowsOperationsProofValid": True,
        "metricFamily": EXPECTED_METRIC_NAME,
        "dashboardUid": EXPECTED_DASHBOARD_UID,
        "operatorDashboardCertified": True,
        "operatorAlertsCertified": True,
    }
    if any(payload.get(key) != value for key, value in expected_values.items()):
        return False
    if any(payload.get(field_name) is not False for field_name in expected_false_fields):
        return False
    if tuple(payload.get("alertIds") or ()) != EXPECTED_ALERT_IDS:
        return False
    if tuple(payload.get("outboxSupportabilityMetricFamilies") or ()) != (
        EXPECTED_OUTBOX_SUPPORTABILITY_METRICS
    ):
        return False
    if not is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if tuple(payload.get("aggregateBlockersCleared") or ()) != (
        OPERATOR_WORKFLOWS_OPERATIONS_BLOCKERS_CLEARED
    ):
        return False
    if tuple(payload.get("evidenceRefs") or ()) != (
        REQUIRED_OPERATOR_WORKFLOWS_OPERATIONS_EVIDENCE_REFS
    ):
        return False
    if tuple(payload.get("remainingCertificationBlockers") or ()) != (
        REMAINING_OPERATOR_WORKFLOWS_OPERATIONS_BLOCKERS
    ):
        return False
    proof_checks = payload.get("proofChecks")
    if not isinstance(proof_checks, Mapping):
        return False
    return all(
        proof_checks.get(check_name) is True
        for check_name in (
            "timezoneAwareGeneratedAtUtc",
            "fileEvidencePresent",
            "makeTargetEvidencePresent",
            "dashboardArtifactCertified",
            "alertRulesArtifactCertified",
            "runbookArtifactCertified",
            "operationsContractCertified",
        )
    )


def _dashboard_artifact_certified(repository_root: Path) -> bool:
    path = (
        repository_root
        / "monitoring/grafana/dashboards/lotus-idea-operator-workflows-operations.json"
    )
    try:
        dashboard = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    serialized = json.dumps(dashboard, sort_keys=True)
    if dashboard.get("uid") != EXPECTED_DASHBOARD_UID:
        return False
    if dashboard.get("title") != "Lotus Idea Operator Workflow Operations":
        return False
    if _contains_forbidden_observability_fragment(serialized):
        return False
    if not _contains_only_governed_source_authorities(serialized):
        return False
    metric_names = set(re.findall(r"lotus_[a-z0-9_]+", serialized))
    if metric_names != {EXPECTED_METRIC_NAME, *EXPECTED_OUTBOX_SUPPORTABILITY_METRICS}:
        return False
    if not all(operation in serialized for operation in EXPECTED_DASHBOARD_OPERATIONS):
        return False
    panels = dashboard.get("panels")
    return isinstance(panels, list) and len(panels) == 7


def _alert_rules_artifact_certified(repository_root: Path) -> bool:
    path = (
        repository_root
        / "monitoring/prometheus/rules/lotus-idea-operator-workflows-operations.rules.yml"
    )
    text = read_text(path)
    if not text or _contains_forbidden_observability_fragment(text):
        return False
    if not _contains_only_governed_source_authorities(text):
        return False
    for alert_id in EXPECTED_ALERT_IDS:
        if f"alert_id: {alert_id}" not in text:
            return False
        if f"docs/runbooks/operator-workflows-operations.md#{alert_id}" not in text:
            return False
    return all(operation in text for operation in EXPECTED_DASHBOARD_OPERATIONS)


def _runbook_artifact_certified(repository_root: Path) -> bool:
    text = read_text(repository_root / "docs/runbooks/operator-workflows-operations.md")
    if not text or _contains_forbidden_observability_fragment(text):
        return False
    required_fragments = tuple(f"## {alert_id}" for alert_id in EXPECTED_ALERT_IDS) + (
        "supported-feature promotion",
        "downstream execution outcomes",
        "external broker publication",
    )
    return all(fragment in text for fragment in required_fragments)


def _operations_contract_certified(repository_root: Path) -> bool:
    path = (
        repository_root / "contracts/observability/lotus-idea-operator-workflows-operations.v1.json"
    )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if payload.get("dashboard_certified") is not True:
        return False
    if payload.get("alert_certified") is not True:
        return False
    source_of_truth = payload.get("source_of_truth")
    if not isinstance(source_of_truth, Mapping):
        return False
    expected_paths = {
        "dashboard": "monitoring/grafana/dashboards/lotus-idea-operator-workflows-operations.json",
        "alert_rules": "monitoring/prometheus/rules/"
        "lotus-idea-operator-workflows-operations.rules.yml",
        "operator_runbook": "docs/runbooks/operator-workflows-operations.md",
        "proof_contract_gate": "scripts/operator_workflows_operations_proof_contract_gate.py",
    }
    if any(source_of_truth.get(key) != value for key, value in expected_paths.items()):
        return False
    dashboard_statuses = {
        control.get("certification_status")
        for control in payload.get("operator_dashboard_controls", ())
        if isinstance(control, Mapping)
    }
    alert_statuses = {
        alert.get("certification_status")
        for alert in payload.get("operator_alert_candidates", ())
        if isinstance(alert, Mapping)
    }
    return dashboard_statuses == {"certified"} and alert_statuses == {"certified"}


def _contains_forbidden_observability_fragment(text: str) -> bool:
    lowered = text.lower()
    return any(fragment.lower() in lowered for fragment in FORBIDDEN_OBSERVABILITY_FRAGMENTS)


def _contains_only_governed_source_authorities(text: str) -> bool:
    governed = set(OPERATION_EVENT_SOURCE_AUTHORITIES)
    for match in SOURCE_AUTHORITY_MATCHER.finditer(text):
        raw_values = match.group(1).split("|")
        for raw_value in raw_values:
            source_authority = raw_value.strip()
            if source_authority and source_authority not in governed:
                return False
    return True
