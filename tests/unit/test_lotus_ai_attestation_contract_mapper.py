from datetime import UTC, datetime

from app.infrastructure.lotus_ai_attestation_contract_mapper import (
    map_lotus_ai_run_attestation,
)


def test_maps_exact_producer_envelope_and_preserves_canonical_claim_values() -> None:
    payload = _attestation_payload()

    envelope = map_lotus_ai_run_attestation(payload)

    assert envelope.claims.run_id == "packrun_idea_explanation_request-001"
    assert envelope.claims.issued_at_utc == datetime(2026, 7, 11, 10, 5, tzinfo=UTC)
    assert envelope.signature.key_id == "attestation-key-1"
    assert envelope.canonical_claims["issued_at_utc"] == "2026-07-11T10:05:00Z"
    assert envelope.key_discovery_path == "/.well-known/lotus-ai-workflow-attestation-keys"


def _attestation_payload() -> dict[str, object]:
    return {
        "claims": {
            "schema_version": "lotus-ai.workflow-run-attestation.v1",
            "issuer": "lotus-ai",
            "audience": "lotus-idea",
            "run_id": "packrun_idea_explanation_request-001",
            "consumer_request_id": "request-001",
            "replay_nonce": "a" * 64,
            "workflow_pack_id": "idea_explanation.pack",
            "workflow_pack_version": "v1",
            "registration_ref": "idea_explanation.pack@v1",
            "evaluator_id": "idea-explanation-guardrails",
            "evaluator_policy_version": "idea-explanation-policy.v1",
            "provider_id": "text.openai",
            "provider_mode": "openai",
            "model_id": "gpt-5.4",
            "model_version": "2026-06-01",
            "model_risk_status": "approved",
            "model_risk_approval_ref": "model-risk://lotus-ai/gpt-5.4/2026-06-01",
            "input_evidence_sha256": "b" * 64,
            "output_content_sha256": "c" * 64,
            "issued_at_utc": "2026-07-11T10:05:00Z",
            "execution_started_at_utc": "2026-07-11T10:04:50Z",
            "execution_completed_at_utc": "2026-07-11T10:04:54Z",
            "expires_at_utc": "2026-07-11T10:10:00Z",
            "stubbed": False,
            "supportability_status": "READY",
        },
        "signature": {
            "algorithm": "EdDSA",
            "key_id": "attestation-key-1",
            "rotation_epoch": 1,
            "signature_base64url": "c2lnbmF0dXJl",
        },
        "key_discovery_path": "/.well-known/lotus-ai-workflow-attestation-keys",
    }
