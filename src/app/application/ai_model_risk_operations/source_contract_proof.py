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
from app.domain.proof_evidence import EvidenceClass, evidence_class_can_clear

AI_MODEL_RISK_OPERATIONS_PROOF_ENV = "LOTUS_IDEA_AI_MODEL_RISK_OPERATIONS_PROOF"
AI_MODEL_RISK_OPERATIONS_PROOF_SCHEMA_VERSION = "lotus-idea.ai-model-risk-operations-proof.v2"
AI_MODEL_RISK_OPERATIONS_REQUIRED_BLOCKER_EVIDENCE_CLASSES: tuple[tuple[str, str], ...] = ()

AI_MODEL_RISK_OPERATIONS_BLOCKERS_CLEARED: tuple[str, ...] = ()

REMAINING_AI_MODEL_RISK_OPERATIONS_BLOCKERS = (
    "model_risk_dashboard_runtime_proof_missing",
    "model_risk_alert_rules_runtime_proof_missing",
    "certified_runtime_trust_telemetry_missing",
    "workbench_product_proof_missing",
    "supported_feature_promotion_missing",
)

REQUIRED_AI_MODEL_RISK_OPERATIONS_EVIDENCE_REFS = (
    "contracts/observability/lotus-idea-ai-model-risk-operations.v1.json",
    "contracts/observability/lotus-idea-operation-metrics.v1.json",
    "monitoring/grafana/dashboards/lotus-idea-ai-model-risk-operations.json",
    "monitoring/prometheus/rules/lotus-idea-ai-model-risk-operations.rules.yml",
    "docs/runbooks/ai-model-risk-operations.md",
    "src/app/observability/logging.py",
    "src/app/application/ai_model_risk_operations/source_contract_proof.py",
    "scripts/ai_model_risk_operations/generate_source_contract_proof.py",
    "scripts/ai_model_risk_operations/source_contract_proof_gate.py",
    "tests/unit/ai_model_risk_operations/test_source_contract_proof.py",
    "make ai-model-risk-operations-proof-contract-gate",
)

EXPECTED_METRIC_NAME = "lotus_idea_operation_events_total"
EXPECTED_DASHBOARD_UID = "lotus-idea-ai-model-risk-operations"
EXPECTED_ALERT_IDS = (
    "ai-explanation-unsupported-claim-block-rate",
    "ai-explanation-readiness-remains-blocked",
)
EXPECTED_DASHBOARD_OPERATIONS = (
    "ai_explanation",
    "ai_explanation_readiness_read",
)
FORBIDDEN_OBSERVABILITY_FRAGMENTS = (
    "account_id",
    "client_id",
    "client_name",
    "correlation_id",
    "holding_id",
    "portfolio_id",
    "raw prompt",
    "raw provider",
    "request_body",
    "response_body",
    "source_payload",
    "trace_id",
    "PB_SG_GLOBAL_BAL_001",
)


def build_ai_model_risk_operations_proof_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
) -> dict[str, Any]:
    evidence_refs = tuple(REQUIRED_AI_MODEL_RISK_OPERATIONS_EVIDENCE_REFS)
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
    dashboard_source_contract_valid = _dashboard_source_contract_is_valid(repository_root)
    alert_rules_source_contract_valid = _alert_rules_source_contract_is_valid(repository_root)
    runbook_source_contract_valid = _runbook_source_contract_is_valid(repository_root)
    operations_source_contract_valid = _operations_source_contract_is_valid(repository_root)
    evidence_class_matches_blockers = all(
        evidence_class_can_clear(
            actual=EvidenceClass.SOURCE_CONTRACT,
            required=EvidenceClass(required_class),
        )
        for _blocker, required_class in (AI_MODEL_RISK_OPERATIONS_REQUIRED_BLOCKER_EVIDENCE_CLASSES)
    )
    proof_valid = (
        timezone_aware_generated_at_utc
        and file_evidence_present
        and make_target_evidence_present
        and dashboard_source_contract_valid
        and alert_rules_source_contract_valid
        and runbook_source_contract_valid
        and operations_source_contract_valid
        and evidence_class_matches_blockers
    )
    return {
        "schemaVersion": AI_MODEL_RISK_OPERATIONS_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "ai_model_risk_operations_source_contract",
        "proofScope": "source_safe_operations_artifact_contract",
        "evidenceClass": EvidenceClass.SOURCE_CONTRACT.value,
        "requiredBlockerEvidenceClasses": dict(
            AI_MODEL_RISK_OPERATIONS_REQUIRED_BLOCKER_EVIDENCE_CLASSES
        ),
        "aiModelRiskOperationsProofValid": proof_valid,
        "aggregateBlockersCleared": AI_MODEL_RISK_OPERATIONS_BLOCKERS_CLEARED,
        "evidenceRefs": evidence_refs,
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": timezone_aware_generated_at_utc,
            "fileEvidencePresent": file_evidence_present,
            "makeTargetEvidencePresent": make_target_evidence_present,
            "dashboardSourceContractValid": dashboard_source_contract_valid,
            "alertRulesSourceContractValid": alert_rules_source_contract_valid,
            "runbookSourceContractValid": runbook_source_contract_valid,
            "operationsSourceContractValid": operations_source_contract_valid,
            "evidenceClassMatchesBlockers": evidence_class_matches_blockers,
        },
        "remainingCertificationBlockers": REMAINING_AI_MODEL_RISK_OPERATIONS_BLOCKERS,
        "metricFamily": EXPECTED_METRIC_NAME,
        "dashboardUid": EXPECTED_DASHBOARD_UID,
        "alertIds": EXPECTED_ALERT_IDS,
        "modelRiskDashboardSourceContractValid": dashboard_source_contract_valid,
        "modelRiskAlertRulesSourceContractValid": alert_rules_source_contract_valid,
        "runtimeExecutionObserved": False,
        "deploymentObserved": False,
        "productionCertificationGranted": False,
        "lotusAiRuntimeExecuted": False,
        "liveProviderExecuted": False,
        "runtimeTrustTelemetryCertified": False,
        "workbenchProductProofCertified": False,
        "clientReadyPublicationAuthorized": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }


def ai_model_risk_operations_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    if payload.get("schemaVersion") != AI_MODEL_RISK_OPERATIONS_PROOF_SCHEMA_VERSION:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("proofType") != "ai_model_risk_operations_source_contract":
        return False
    if payload.get("proofScope") != "source_safe_operations_artifact_contract":
        return False
    if payload.get("evidenceClass") != EvidenceClass.SOURCE_CONTRACT.value:
        return False
    required_classes = payload.get("requiredBlockerEvidenceClasses")
    if not isinstance(required_classes, Mapping):
        return False
    if tuple(required_classes.items()) != (
        AI_MODEL_RISK_OPERATIONS_REQUIRED_BLOCKER_EVIDENCE_CLASSES
    ):
        return False
    if payload.get("aiModelRiskOperationsProofValid") is not True:
        return False
    if payload.get("metricFamily") != EXPECTED_METRIC_NAME:
        return False
    if payload.get("dashboardUid") != EXPECTED_DASHBOARD_UID:
        return False
    if tuple(payload.get("alertIds") or ()) != EXPECTED_ALERT_IDS:
        return False
    if payload.get("modelRiskDashboardSourceContractValid") is not True:
        return False
    if payload.get("modelRiskAlertRulesSourceContractValid") is not True:
        return False
    if payload.get("runtimeExecutionObserved") is not False:
        return False
    if payload.get("deploymentObserved") is not False:
        return False
    if payload.get("productionCertificationGranted") is not False:
        return False
    if payload.get("lotusAiRuntimeExecuted") is not False:
        return False
    if payload.get("liveProviderExecuted") is not False:
        return False
    if payload.get("runtimeTrustTelemetryCertified") is not False:
        return False
    if payload.get("workbenchProductProofCertified") is not False:
        return False
    if payload.get("clientReadyPublicationAuthorized") is not False:
        return False
    if payload.get("supportedFeaturePromoted") is not False:
        return False
    if payload.get("proofClosed") is not False:
        return False
    if not is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if tuple(payload.get("aggregateBlockersCleared") or ()) != (
        AI_MODEL_RISK_OPERATIONS_BLOCKERS_CLEARED
    ):
        return False
    if tuple(payload.get("evidenceRefs") or ()) != (
        REQUIRED_AI_MODEL_RISK_OPERATIONS_EVIDENCE_REFS
    ):
        return False
    if tuple(payload.get("remainingCertificationBlockers") or ()) != (
        REMAINING_AI_MODEL_RISK_OPERATIONS_BLOCKERS
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
            "dashboardSourceContractValid",
            "alertRulesSourceContractValid",
            "runbookSourceContractValid",
            "operationsSourceContractValid",
            "evidenceClassMatchesBlockers",
        )
    )


def _dashboard_source_contract_is_valid(repository_root: Path) -> bool:
    path = (
        repository_root / "monitoring/grafana/dashboards/lotus-idea-ai-model-risk-operations.json"
    )
    try:
        dashboard = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    serialized = json.dumps(dashboard, sort_keys=True)
    if dashboard.get("uid") != EXPECTED_DASHBOARD_UID:
        return False
    if dashboard.get("title") != "Lotus Idea AI Model-Risk Operations":
        return False
    if _contains_forbidden_observability_fragment(serialized):
        return False
    metric_names = set(re.findall(r"lotus_[a-z0-9_]+", serialized))
    if metric_names != {EXPECTED_METRIC_NAME}:
        return False
    if not all(operation in serialized for operation in EXPECTED_DASHBOARD_OPERATIONS):
        return False
    panels = dashboard.get("panels")
    return isinstance(panels, list) and len(panels) == 3


def _alert_rules_source_contract_is_valid(repository_root: Path) -> bool:
    path = (
        repository_root
        / "monitoring/prometheus/rules/lotus-idea-ai-model-risk-operations.rules.yml"
    )
    text = read_text(path)
    if not text or _contains_forbidden_observability_fragment(text):
        return False
    if text.count(EXPECTED_METRIC_NAME) != 2:
        return False
    for alert_id in EXPECTED_ALERT_IDS:
        if f"alert_id: {alert_id}" not in text:
            return False
        if f"docs/runbooks/ai-model-risk-operations.md#{alert_id}" not in text:
            return False
    return all(operation in text for operation in EXPECTED_DASHBOARD_OPERATIONS)


def _runbook_source_contract_is_valid(repository_root: Path) -> bool:
    text = read_text(repository_root / "docs/runbooks/ai-model-risk-operations.md")
    if not text:
        return False
    normalized_text = " ".join(text.split())
    required_fragments = (
        "## ai-explanation-unsupported-claim-block-rate",
        "## ai-explanation-readiness-remains-blocked",
        "without exposing prompt content",
        "restricted client references",
        "Static validation does not prove",
        "live-provider execution",
        "supported-feature promotion",
    )
    return all(fragment in normalized_text for fragment in required_fragments)


def _operations_source_contract_is_valid(repository_root: Path) -> bool:
    path = repository_root / "contracts/observability/lotus-idea-ai-model-risk-operations.v1.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if payload.get("dashboard_source_contract_valid") is not True:
        return False
    if payload.get("alert_rules_source_contract_valid") is not True:
        return False
    source_of_truth = payload.get("source_of_truth")
    if not isinstance(source_of_truth, Mapping):
        return False
    expected_paths = {
        "dashboard": "monitoring/grafana/dashboards/lotus-idea-ai-model-risk-operations.json",
        "alert_rules": "monitoring/prometheus/rules/lotus-idea-ai-model-risk-operations.rules.yml",
        "model_risk_runbook": "docs/runbooks/ai-model-risk-operations.md",
        "proof_contract_gate": "scripts/ai_model_risk_operations/source_contract_proof_gate.py",
    }
    if any(source_of_truth.get(key) != value for key, value in expected_paths.items()):
        return False
    dashboard_statuses = {
        control.get("source_contract_status")
        for control in payload.get("model_risk_dashboard_controls", ())
        if isinstance(control, Mapping)
    }
    alert_statuses = {
        alert.get("source_contract_status")
        for alert in payload.get("model_risk_alert_candidates", ())
        if isinstance(alert, Mapping)
    }
    return dashboard_statuses == {"valid"} and alert_statuses == {"valid"}


def _contains_forbidden_observability_fragment(text: str) -> bool:
    lowered = text.lower()
    return any(fragment.lower() in lowered for fragment in FORBIDDEN_OBSERVABILITY_FRAGMENTS)
