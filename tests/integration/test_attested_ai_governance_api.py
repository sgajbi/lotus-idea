from datetime import UTC, datetime, timedelta
from typing import Mapping, cast

import pytest
from fastapi.testclient import TestClient

import app.api.ai_governance as ai_governance_api
from app.application.lotus_ai_idea_explanation_request import (
    build_lotus_ai_idea_explanation_input,
)
from app.domain.ai_governance import (
    AIExplanationCommand,
    AIWorkflowPackRef,
    AIWorkflowPurpose,
    GOVERNED_IDEA_EXPLANATION_WORKFLOW_PACK,
    build_ai_explanation_request,
)
from app.domain.lotus_ai_execution_digest import (
    LotusAIExecutionOutputContent,
    lotus_ai_input_evidence_sha256,
    lotus_ai_output_content_sha256,
)
from app.domain.lotus_ai_run_attestation import (
    LotusAIAttestationKeyDiscovery,
    LotusAIAttestationPublicKey,
)
from app.main import app
from app.runtime.repository_state import get_idea_repository, reset_idea_repository_for_tests
from tests.integration.test_ai_governance_api import (
    ai_headers,
    ai_request_payload,
    persisted_candidate_id,
    transition_candidate_to_review_ready,
)


def test_api_accepts_signed_bound_lotus_ai_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-attested-api-001")
    transition_candidate_to_review_ready(client, candidate_id)
    request_id = "attested-api-request-001"
    producer_output = _producer_output()
    issued_at = datetime.now(UTC) - timedelta(seconds=5)
    attestation = _attestation_payload(
        candidate_id=candidate_id,
        request_id=request_id,
        producer_output=producer_output,
        issued_at=issued_at,
    )
    monkeypatch.setattr(
        ai_governance_api,
        "get_lotus_ai_attestation_dependencies",
        lambda: (StaticKeySource(issued_at), AcceptingSignatureVerifier()),
    )
    payload = ai_request_payload(
        request_id=request_id,
        purpose="advisor_rationale_draft",
    )
    payload.update(
        {
            "producerRunId": "packrun_idea_explanation_attested-api-request-001",
            "producerExecutionOutput": producer_output,
            "runAttestation": attestation,
        }
    )

    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/ai-explanations/evaluate",
        json=payload,
        headers=ai_headers(idempotency_key="attested-api-request-001"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["posture"] == "ready_for_advisor_review"
    assert body["executionProvenancePosture"] == "lotus_ai_attestation_verified"
    assert body["lotusAiRuntimeExecuted"] is True
    assert body["grantsDownstreamAuthority"] is False
    assert body["supportedFeaturePromoted"] is False
    lineage = (
        get_idea_repository()
        .snapshot()
        .candidate_records[candidate_id]
        .ai_explanation_lineage_records[-1]
    )
    assert lineage.attestation_receipt is not None
    assert lineage.attestation_receipt.run_id == "packrun_idea_explanation_attested-api-request-001"
    reset_idea_repository_for_tests()


def _producer_output() -> dict[str, object]:
    message = "The evidence supports an internal advisor review of idle cash."
    return {
        "status": "COMPLETED",
        "output_label": "EXPLANATION_ONLY",
        "message": message,
        "structured_output": {
            "idea_workflow_output": {
                "output_id": "attested-output-001",
                "explanation_text": message,
                "claims": [
                    {
                        "claim_id": "claim-001",
                        "claim_text": "Cash attention is supported by Core portfolio state.",
                        "source_product_ids": ["lotus-core:PortfolioStateSnapshot:v1"],
                    }
                ],
                "proposed_actions": [
                    {
                        "action_type": "advisor_review",
                        "action_label": "Review evidence internally",
                    }
                ],
            }
        },
    }


def _attestation_payload(
    *,
    candidate_id: str,
    request_id: str,
    producer_output: dict[str, object],
    issued_at: datetime,
) -> dict[str, object]:
    repository = get_idea_repository()
    candidate = repository.snapshot().candidate_records[candidate_id].candidate
    contract = GOVERNED_IDEA_EXPLANATION_WORKFLOW_PACK
    explanation_request = build_ai_explanation_request(
        candidate,
        AIExplanationCommand(
            request_id=request_id,
            actor_subject="advisor-001",
            workflow_pack=AIWorkflowPackRef(
                workflow_pack_id=contract.request_workflow_pack_id,
                workflow_pack_version=contract.workflow_pack_version,
                purpose=AIWorkflowPurpose.ADVISOR_RATIONALE_DRAFT,
                evaluation_ref=contract.evaluation_ref,
            ),
            approved_metadata={"channel": "advisor-workbench"},
            requested_at_utc=datetime(2026, 6, 21, 10, 12, tzinfo=UTC),
        ),
    )
    execution_content = LotusAIExecutionOutputContent(
        status=str(producer_output["status"]),
        output_label=str(producer_output["output_label"]),
        message=str(producer_output["message"]),
        structured_output=cast(Mapping[str, object], producer_output["structured_output"]),
    )
    claims = {
        "schema_version": "lotus-ai.workflow-run-attestation.v1",
        "issuer": "lotus-ai",
        "audience": "lotus-idea",
        "run_id": "packrun_idea_explanation_attested-api-request-001",
        "consumer_request_id": request_id,
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
        "input_evidence_sha256": lotus_ai_input_evidence_sha256(
            build_lotus_ai_idea_explanation_input(explanation_request)
        ),
        "output_content_sha256": lotus_ai_output_content_sha256(execution_content),
        "issued_at_utc": issued_at.isoformat().replace("+00:00", "Z"),
        "execution_started_at_utc": (issued_at - timedelta(seconds=5))
        .isoformat()
        .replace("+00:00", "Z"),
        "execution_completed_at_utc": (issued_at - timedelta(seconds=1))
        .isoformat()
        .replace("+00:00", "Z"),
        "expires_at_utc": (issued_at + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
        "stubbed": False,
        "supportability_status": "READY",
    }
    return {
        "claims": claims,
        "signature": {
            "algorithm": "EdDSA",
            "key_id": "attestation-key-1",
            "rotation_epoch": 1,
            "signature_base64url": "c2lnbmF0dXJl",
        },
        "key_discovery_path": "/.well-known/lotus-ai-workflow-attestation-keys",
    }


class StaticKeySource:
    def __init__(self, issued_at: datetime) -> None:
        self._issued_at = issued_at

    def get_key_discovery(self) -> LotusAIAttestationKeyDiscovery:
        return LotusAIAttestationKeyDiscovery(
            schema_version="lotus-ai.workflow-run-attestation-keys.v1",
            issuer="lotus-ai",
            keys=(
                LotusAIAttestationPublicKey(
                    key_id="attestation-key-1",
                    algorithm="EdDSA",
                    curve="Ed25519",
                    public_key_base64url="cHVibGljLWtleQ",
                    rotation_epoch=1,
                    status="active",
                    not_before_utc=self._issued_at - timedelta(days=1),
                    not_after_utc=self._issued_at + timedelta(days=1),
                ),
            ),
        )


class AcceptingSignatureVerifier:
    def verify(
        self,
        *,
        public_key_base64url: str,
        signature_base64url: str,
        canonical_payload: bytes,
    ) -> None:
        assert public_key_base64url
        assert signature_base64url
        assert canonical_payload
