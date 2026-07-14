import json
from pathlib import Path

from app.api.ai_governance_models import AIExplanationReadinessResponse
from app.application.ai_governance import build_ai_explanation_readiness_snapshot


ROOT = Path(__file__).resolve().parents[2]


def test_ai_explanation_readiness_reports_blocked_not_certified_posture() -> None:
    snapshot = build_ai_explanation_readiness_snapshot()

    assert snapshot.repository == "lotus-idea"
    assert snapshot.source_authority == "lotus-idea"
    assert snapshot.workflow_authority == "lotus-ai"
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.certification_ready is False
    assert snapshot.deterministic_fallback_available is True
    assert snapshot.verifier_available is True
    assert snapshot.redacted_evidence_envelope_available is True
    assert snapshot.unsupported_claim_blocking_available is True
    assert snapshot.claim_grounding_available is True
    assert snapshot.claim_grounding_policy_version == ("lotus-idea.ai-claim-grounding-policy.v1")
    assert snapshot.forbidden_action_blocking_available is True
    assert snapshot.action_content_policy_version == ("lotus-idea.ai-action-content-policy.v1")
    assert snapshot.lotus_ai_run_attestation_available is True
    assert snapshot.production_like_attestation_required is True
    assert snapshot.local_test_unattested_fixture_allowed is True
    assert snapshot.execution_provenance_policy_version == (
        "lotus-idea.ai-execution-provenance-policy.v1"
    )
    assert snapshot.durable_ai_lineage_store_backed is False
    assert snapshot.model_risk_operations_contract_available is True
    assert snapshot.model_risk_dashboard_contract_available is True
    assert snapshot.model_risk_alert_contract_available is True
    assert snapshot.model_risk_dashboard_certified is True
    assert snapshot.model_risk_alert_certified is True
    assert snapshot.lotus_ai_runtime_executed is False
    assert snapshot.supported_feature_promoted is False
    assert snapshot.certification_blockers == (
        "lotus_ai_runtime_execution_missing",
        "certified_ai_lineage_store_missing",
        "workflow_pack_runtime_contract_not_certified",
        "certified_runtime_trust_telemetry_missing",
        "workbench_product_proof_missing",
    )


def test_ai_explanation_readiness_reports_durable_lineage_store_without_certification() -> None:
    snapshot = build_ai_explanation_readiness_snapshot(
        durable_ai_lineage_store_backed=True,
    )

    assert snapshot.durable_ai_lineage_store_backed is True
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.certification_ready is False
    assert "lotus_ai_runtime_execution_missing" in snapshot.certification_blockers
    assert "certified_ai_lineage_store_missing" in snapshot.certification_blockers
    assert snapshot.supported_feature_promoted is False


def test_ai_explanation_readiness_ledger_example_matches_runtime_contract() -> None:
    ledger = json.loads(
        (ROOT / "docs/operations/endpoint-certification-ledger.json").read_text(encoding="utf-8")
    )
    endpoint = next(
        entry
        for entry in ledger["endpoints"]
        if entry["method"] == "GET" and entry["path"] == "/api/v1/ai-explanations/readiness"
    )
    documented = json.loads(endpoint["response_examples"][0])
    runtime = json.loads(
        AIExplanationReadinessResponse.from_domain(
            build_ai_explanation_readiness_snapshot()
        ).model_dump_json(by_alias=True)
    )

    assert documented == runtime
