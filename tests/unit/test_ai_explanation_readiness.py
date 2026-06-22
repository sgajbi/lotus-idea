from app.application.ai_governance import build_ai_explanation_readiness_snapshot


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
    assert snapshot.forbidden_action_blocking_available is True
    assert snapshot.durable_ai_lineage_store_backed is False
    assert snapshot.lotus_ai_runtime_executed is False
    assert snapshot.supported_feature_promoted is False
    assert snapshot.certification_blockers == (
        "lotus_ai_runtime_execution_missing",
        "durable_ai_lineage_store_missing",
        "workflow_pack_runtime_contract_not_certified",
        "model_risk_operations_dashboard_missing",
        "certified_runtime_trust_telemetry_missing",
        "workbench_product_proof_missing",
    )
