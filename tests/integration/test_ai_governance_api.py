from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.api.ai_governance as ai_governance_api
from app.runtime.repository_state import reset_idea_repository_for_tests
from app.domain import InMemoryIdeaRepository, InvalidAIWorkflowOutput
from app.main import app


def source_ref(product_id: str) -> dict[str, str]:
    return {
        "productId": product_id,
        "sourceSystem": "lotus-core",
        "productVersion": "v1",
        "route": f"/source/{product_id}",
        "asOfDate": "2026-06-21",
        "generatedAtUtc": "2026-06-21T10:00:00Z",
        "contentHash": f"sha256:{product_id}",
        "dataQualityStatus": "complete",
        "freshness": "current",
    }


def high_cash_payload() -> dict[str, Any]:
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "sourceReportedCashWeight": "0.18",
        "sourceEvidence": {
            "portfolioStateRef": source_ref("lotus-core:PortfolioStateSnapshot:v1"),
            "holdingsRef": source_ref("lotus-core:HoldingsAsOf:v1"),
            "cashMovementRef": source_ref("lotus-core:PortfolioCashMovementSummary:v1"),
            "cashflowProjectionRef": source_ref("lotus-core:PortfolioCashflowProjection:v1"),
        },
        "entitlementAllowed": True,
    }


def persist_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "signal-ingestion-worker",
        "X-Caller-Capabilities": "idea.candidate.persist",
        "Idempotency-Key": idempotency_key,
    }


def lifecycle_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "idea-lifecycle-worker",
        "X-Caller-Capabilities": "idea.candidate.lifecycle.transition",
        "Idempotency-Key": idempotency_key,
    }


def ai_headers(
    capabilities: str = "idea.ai-explanation.evaluate",
    *,
    idempotency_key: str = "ai-explanation-api-001",
) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": capabilities,
        "Idempotency-Key": idempotency_key,
        "X-Correlation-Id": "corr-ai-governance-api",
    }


def ai_readiness_headers(
    *,
    roles: str = "operator",
    capabilities: str = "idea.ai-explanation.readiness.read",
) -> dict[str, str]:
    return {
        "X-Caller-Subject": "platform-operator",
        "X-Caller-Roles": roles,
        "X-Caller-Capabilities": capabilities,
        "X-Correlation-Id": "corr-ai-readiness-api",
    }


class DurableInMemoryIdeaRepository(InMemoryIdeaRepository):
    durable_storage_backed = True


def lifecycle_payload(target_status: str, minute: int) -> dict[str, Any]:
    return {
        "transitionId": f"ai-lifecycle-{target_status}-001",
        "targetLifecycleStatus": target_status,
        "changedAtUtc": f"2026-06-21T10:{minute:02d}:00Z",
        "reasonCodes": ["review_required"],
    }


def ai_request_payload(
    *,
    request_id: str = "ai-explanation-001",
    purpose: str = "missing_evidence_check",
    workflow_output: dict[str, Any] | None = None,
    approved_metadata: dict[str, str] | None = None,
    workflow_pack: dict[str, str] | None = None,
) -> dict[str, Any]:
    payload = {
        "requestId": request_id,
        "workflowPack": workflow_pack
        or {
            "workflowPackId": "lotus-ai:idea-explanation:v1",
            "workflowPackVersion": "v1",
            "purpose": purpose,
            "evaluationRef": "lotus-ai:governed-verifier:v1",
        },
        "approvedMetadata": approved_metadata or {"channel": "advisor-workbench"},
        "requestedAtUtc": "2026-06-21T10:12:00Z",
        "fallbackReason": "ai_unavailable",
    }
    if workflow_output is not None:
        payload["workflowOutput"] = workflow_output
    return payload


def workflow_output(
    *,
    claim_source_ids: list[str] | None = None,
    action_type: str = "advisor_review",
    action_label: str = "Route to advisor review",
    explanation_text: str = "Candidate has elevated idle cash and source-ready evidence.",
    claim_text: str = "Cash weight is above idle-liquidity policy threshold.",
) -> dict[str, Any]:
    return {
        "outputId": "ai-output-001",
        "explanationText": explanation_text,
        "claims": [
            {
                "claimId": "claim-001",
                "claimText": claim_text,
                "sourceProductIds": claim_source_ids or ["lotus-core:PortfolioStateSnapshot:v1"],
            }
        ],
        "proposedActions": [
            {
                "actionType": action_type,
                "actionLabel": action_label,
            }
        ],
        "verifierRanAtUtc": "2026-06-21T10:12:30Z",
    }


def persisted_candidate_id(client: TestClient, *, idempotency_key: str) -> str:
    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(),
        headers=persist_headers(idempotency_key),
    )
    assert response.status_code == 200
    return str(response.json()["persistence"]["candidateId"])


def transition_candidate_to_review_ready(client: TestClient, candidate_id: str) -> None:
    for index, target_status in enumerate(
        ("enriched", "scored", "governance_checked", "ready_for_review"),
        start=1,
    ):
        response = client.post(
            f"/api/v1/idea-candidates/{candidate_id}/lifecycle-transitions",
            json=lifecycle_payload(target_status, index),
            headers=lifecycle_headers(f"ai-lifecycle-{target_status}-001"),
        )
        assert response.status_code == 200


def test_ai_explanation_api_returns_deterministic_fallback_without_runtime_claim() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-ai-fallback-001")

    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/ai-explanations/evaluate",
        json=ai_request_payload(),
        headers=ai_headers(),
    )

    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == "corr-ai-governance-api"
    payload = response.json()
    assert payload["posture"] == "fallback_used"
    assert payload["verifierOutcome"] == "not_run"
    assert payload["fallbackUsed"] is True
    assert payload["fallbackReason"] == "ai_unavailable"
    assert payload["grantsDownstreamAuthority"] is False
    assert payload["aiLineageRecorded"] is True
    assert payload["aiLineagePersistenceDecision"] == "accepted"
    assert payload["outputIntegrityVersion"] == "lotus-idea.ai-output-integrity.v1"
    assert payload["outputContentDigest"].startswith("sha256:")
    assert payload["executionProvenancePosture"] == "not_applicable_fallback"
    assert payload["executionProvenancePolicyVersion"] == (
        "lotus-idea.ai-execution-provenance-policy.v1"
    )
    assert payload["metadataEnvelopeVersion"] == "lotus-idea.ai-metadata-envelope.v1"
    assert payload["durableStorageBacked"] is False
    assert payload["lotusAiRuntimeExecuted"] is False
    assert payload["supportedFeaturePromoted"] is False
    assert payload["redactedEvidence"]["candidateId"] == candidate_id
    assert "route" not in response.text


def test_production_like_ai_output_requires_provenance_before_lineage_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = DurableInMemoryIdeaRepository()
    try:
        reset_idea_repository_for_tests(repository=repository)
        client = TestClient(app)
        candidate_id = persisted_candidate_id(
            client,
            idempotency_key="seed-ai-production-provenance-001",
        )
        transition_candidate_to_review_ready(client, candidate_id)
        before_lineage = (
            repository.snapshot().candidate_records[candidate_id].ai_explanation_lineage_records
        )
        monkeypatch.setenv("LOTUS_IDEA_RUNTIME_PROFILE", "production")
        monkeypatch.setenv("LOTUS_IDEA_DATABASE_URL", "postgresql://configured")
        monkeypatch.setenv("LOTUS_IDEA_TRUSTED_CALLER_CONTEXT_TOKEN", "trusted-ingress")
        headers = {
            **ai_headers(idempotency_key="ai-production-provenance-001"),
            "X-Lotus-Trusted-Caller-Context": "trusted-ingress",
        }

        rejected = client.post(
            f"/api/v1/idea-candidates/{candidate_id}/ai-explanations/evaluate",
            json=ai_request_payload(
                purpose="advisor_rationale_draft",
                workflow_output=workflow_output(),
            ),
            headers=headers,
        )
        after_rejected_lineage = (
            repository.snapshot().candidate_records[candidate_id].ai_explanation_lineage_records
        )
        fallback = client.post(
            f"/api/v1/idea-candidates/{candidate_id}/ai-explanations/evaluate",
            json=ai_request_payload(request_id="ai-production-fallback-001"),
            headers={**headers, "Idempotency-Key": "ai-production-fallback-001"},
        )

        assert rejected.status_code == 400
        assert rejected.json()["code"] == "ai_execution_provenance_required"
        assert "workflow output" not in rejected.text.lower()
        assert after_rejected_lineage == before_lineage
        assert fallback.status_code == 200
        assert fallback.json()["executionProvenancePosture"] == "not_applicable_fallback"
        assert (
            len(
                repository.snapshot().candidate_records[candidate_id].ai_explanation_lineage_records
            )
            == len(before_lineage) + 1
        )
    finally:
        reset_idea_repository_for_tests()


def test_ai_explanation_api_accepts_verified_output_for_review_ready_candidate() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-ai-accepted-001")
    transition_candidate_to_review_ready(client, candidate_id)

    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/ai-explanations/evaluate",
        json=ai_request_payload(
            purpose="advisor_rationale_draft",
            workflow_output=workflow_output(),
        ),
        headers=ai_headers(idempotency_key="ai-explanation-accepted-api-001"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["posture"] == "ready_for_advisor_review"
    assert payload["verifierOutcome"] == "passed"
    assert payload["reasonCodes"] == ["ai_verifier_passed"]
    assert payload["verifiedOutput"]["outputId"] == "ai-output-001"
    assert payload["verifiedOutput"]["claimIds"] == ["claim-001"]
    assert payload["verifiedOutput"]["actionPolicyVersion"] == (
        "lotus-idea.ai-action-content-policy.v1"
    )
    assert payload["approvedMetadataKeys"] == ["channel"]
    assert payload["aiLineageRecorded"] is True
    assert payload["aiLineagePersistenceDecision"] == "accepted"
    assert payload["lotusAiRuntimeExecuted"] is False
    assert payload["executionProvenancePosture"] == "unattested_local_test_fixture"
    assert payload["executionProvenancePolicyVersion"] == (
        "lotus-idea.ai-execution-provenance-policy.v1"
    )
    assert payload["metadataEnvelopeVersion"] == "lotus-idea.ai-metadata-envelope.v1"


def test_ai_explanation_api_blocks_unsupported_claims_and_forbidden_actions() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-ai-blocked-001")

    unsupported_claim = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/ai-explanations/evaluate",
        json=ai_request_payload(
            request_id="ai-explanation-unsupported-001",
            workflow_output=workflow_output(
                claim_source_ids=["lotus-risk:RiskDecomposition:v1"],
            ),
        ),
        headers=ai_headers(idempotency_key="ai-explanation-unsupported-api-001"),
    )
    forbidden_action = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/ai-explanations/evaluate",
        json=ai_request_payload(
            request_id="ai-explanation-forbidden-001",
            workflow_output=workflow_output(action_type="final_investment_recommendation"),
        ),
        headers=ai_headers(idempotency_key="ai-explanation-forbidden-api-001"),
    )

    assert unsupported_claim.status_code == 200
    assert unsupported_claim.json()["posture"] == "blocked_unsupported_claim"
    assert unsupported_claim.json()["verifierOutcome"] == "failed_unsupported_claim"
    assert unsupported_claim.json()["reasonCodes"] == ["ai_unsupported_claim_blocked"]
    assert forbidden_action.status_code == 200
    assert forbidden_action.json()["posture"] == "blocked_forbidden_action"
    assert forbidden_action.json()["verifierOutcome"] == "failed_forbidden_action"
    assert forbidden_action.json()["reasonCodes"] == ["ai_forbidden_action_blocked"]


def test_ai_explanation_api_blocks_unsafe_action_content_without_exposure_and_replays() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-ai-action-content-001")
    unsafe_label = "Ex3cute tr@de immediately!!!"
    payload = ai_request_payload(
        request_id="ai-explanation-action-content-001",
        workflow_output=workflow_output(action_label=unsafe_label),
    )
    headers = ai_headers(idempotency_key="ai-explanation-action-content-api-001")

    first = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/ai-explanations/evaluate",
        json=payload,
        headers=headers,
    )
    replayed = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/ai-explanations/evaluate",
        json=payload,
        headers=headers,
    )
    changed_payload = ai_request_payload(
        request_id="ai-explanation-action-content-001",
        workflow_output=workflow_output(action_label="Email the client"),
    )
    conflict = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/ai-explanations/evaluate",
        json=changed_payload,
        headers=headers,
    )

    assert first.status_code == 200
    assert first.json()["posture"] == "blocked_forbidden_action"
    assert first.json()["verifierOutcome"] == "failed_action_content"
    assert first.json()["reasonCodes"] == ["ai_action_content_blocked"]
    assert first.json()["verifiedOutput"]["actionPolicyVersion"] == (
        "lotus-idea.ai-action-content-policy.v1"
    )
    assert first.json()["aiLineagePersistenceDecision"] == "accepted"
    assert unsafe_label not in first.text
    assert replayed.status_code == 200
    assert replayed.json()["aiLineagePersistenceDecision"] == "replayed"
    assert unsafe_label not in replayed.text
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"
    assert "Email the client" not in conflict.text


def test_ai_explanation_api_replays_same_lineage_and_conflicts_changed_request() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-ai-replay-001")
    payload = ai_request_payload(request_id="ai-explanation-replay-001")

    first = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/ai-explanations/evaluate",
        json=payload,
        headers=ai_headers(idempotency_key="ai-explanation-replay-api-001"),
    )
    replayed = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/ai-explanations/evaluate",
        json=payload,
        headers=ai_headers(idempotency_key="ai-explanation-replay-api-001"),
    )
    changed = dict(payload)
    changed["fallbackReason"] = "workflow_not_approved"
    conflict = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/ai-explanations/evaluate",
        json=changed,
        headers=ai_headers(idempotency_key="ai-explanation-replay-api-001"),
    )

    assert first.status_code == 200
    assert first.json()["aiLineagePersistenceDecision"] == "accepted"
    assert replayed.status_code == 200
    assert replayed.json()["aiLineagePersistenceDecision"] == "replayed"
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"
    assert "workflow_not_approved" not in conflict.text


@pytest.mark.parametrize(
    ("changed_output", "changed_text"),
    [
        (
            workflow_output(explanation_text="Changed advisor explanation."),
            "Changed advisor explanation.",
        ),
        (workflow_output(claim_text="Changed governed claim."), "Changed governed claim."),
        (
            workflow_output(action_label="Request the missing governed evidence"),
            "Request the missing governed evidence",
        ),
    ],
)
def test_ai_explanation_api_conflicts_reused_request_identity_when_content_changes(
    changed_output: dict[str, Any],
    changed_text: str,
) -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(
        client,
        idempotency_key=f"seed-ai-integrity-{changed_output['claims'][0]['claimText']}",
    )
    transition_candidate_to_review_ready(client, candidate_id)
    request_id = "ai-explanation-content-integrity-001"
    baseline = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/ai-explanations/evaluate",
        json=ai_request_payload(
            request_id=request_id,
            purpose="advisor_rationale_draft",
            workflow_output=workflow_output(),
        ),
        headers=ai_headers(idempotency_key="ai-integrity-first-001"),
    )
    changed = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/ai-explanations/evaluate",
        json=ai_request_payload(
            request_id=request_id,
            purpose="advisor_rationale_draft",
            workflow_output=changed_output,
        ),
        headers=ai_headers(idempotency_key="ai-integrity-changed-002"),
    )

    assert baseline.status_code == 200
    assert baseline.json()["aiLineagePersistenceDecision"] == "accepted"
    assert changed.status_code == 409
    assert changed.json()["code"] == "ai_explanation_lineage_conflict"
    assert changed_text not in changed.text


def test_ai_explanation_api_requires_idempotency_key() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-ai-idempotency-001")
    headers = ai_headers(idempotency_key="ai-explanation-missing-api-001")
    headers.pop("Idempotency-Key")

    missing = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/ai-explanations/evaluate",
        json=ai_request_payload(request_id="ai-explanation-missing-idempotency-001"),
        headers=headers,
    )
    blank = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/ai-explanations/evaluate",
        json=ai_request_payload(request_id="ai-explanation-blank-idempotency-001"),
        headers={**headers, "Idempotency-Key": " "},
    )

    assert missing.status_code == 400
    assert missing.json()["code"] == "invalid_request"
    assert blank.status_code == 400
    assert blank.json()["code"] == "invalid_request"
    assert "ai-explanation-missing-idempotency-001" not in missing.text


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    (
        ("workflowPackId", "lotus-ai:idea-unsupported-claim-verifier"),
        ("workflowPackVersion", "v1.0.0"),
        ("evaluationRef", "lotus-ai-eval:idea-verifier:v1"),
    ),
)
def test_ai_explanation_api_rejects_unregistered_workflow_pack_identity(
    field_name: str,
    field_value: str,
) -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    field_slug = field_name.lower()
    candidate_id = persisted_candidate_id(
        client,
        idempotency_key=f"seed-ai-invalid-pack-{field_slug}",
    )
    workflow_pack = {
        "workflowPackId": "lotus-ai:idea-explanation:v1",
        "workflowPackVersion": "v1",
        "purpose": "missing_evidence_check",
        "evaluationRef": "lotus-ai:governed-verifier:v1",
    }
    workflow_pack[field_name] = field_value

    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/ai-explanations/evaluate",
        json=ai_request_payload(
            request_id=f"ai-explanation-invalid-pack-{field_slug}",
            workflow_pack=workflow_pack,
        ),
        headers=ai_headers(idempotency_key=f"ai-explanation-invalid-pack-{field_slug}"),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_ai_workflow_pack"
    assert field_value not in response.text
    assert candidate_id not in response.text


def test_ai_explanation_api_requires_permission_and_existing_candidate() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-ai-permission-001")

    denied = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/ai-explanations/evaluate",
        json=ai_request_payload(),
        headers=ai_headers("idea.review.record", idempotency_key="ai-explanation-denied-api-001"),
    )
    missing = client.post(
        "/api/v1/idea-candidates/missing-candidate/ai-explanations/evaluate",
        json=ai_request_payload(),
        headers=ai_headers(idempotency_key="ai-explanation-missing-candidate-api-001"),
    )

    assert denied.status_code == 403
    assert denied.json()["code"] == "permission_denied"
    assert missing.status_code == 404
    assert missing.json()["code"] == "candidate_not_found"


def test_ai_explanation_api_rejects_invalid_purpose_for_current_state_and_metadata() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-ai-invalid-001")

    invalid_state = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/ai-explanations/evaluate",
        json=ai_request_payload(purpose="advisor_rationale_draft"),
        headers=ai_headers(idempotency_key="ai-explanation-invalid-state-api-001"),
    )
    leaked_metadata = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/ai-explanations/evaluate",
        json=ai_request_payload(approved_metadata={"prompt": "summarize private client data"}),
        headers=ai_headers(idempotency_key="ai-explanation-leaked-metadata-api-001"),
    )

    assert invalid_state.status_code == 409
    assert invalid_state.json()["code"] == "ai_explanation_conflict"
    assert leaked_metadata.status_code == 400
    assert leaked_metadata.json()["code"] == "invalid_request"
    assert "summarize private client data" not in leaked_metadata.text


@pytest.mark.parametrize("unknown_key", ["customerEmail", "accountNumber", "authorization"])
def test_ai_explanation_api_rejects_unknown_metadata_before_route_execution(
    unknown_key: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_called(*args: Any, **kwargs: Any) -> None:
        del args, kwargs
        raise AssertionError("request validation must fail before route execution")

    monkeypatch.setattr(
        ai_governance_api,
        "evaluate_ai_explanation_to_repository",
        fail_if_called,
    )
    response = TestClient(app).post(
        "/api/v1/idea-candidates/not-looked-up/ai-explanations/evaluate",
        json=ai_request_payload(approved_metadata={unknown_key: "classified-value"}),
        headers=ai_headers(idempotency_key=f"ai-metadata-unknown-{unknown_key}"),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert unknown_key not in response.text
    assert "classified-value" not in response.text


@pytest.mark.parametrize(
    "unsafe_value",
    [
        "client@example.com",
        "ACCT-123",
        "Bearer eyJhbGciOiJIUzI1NiJ9.secret",
        "advisor-workbench\nAuthorization: secret",
        "x" * 65,
    ],
)
def test_ai_explanation_api_rejects_sensitive_metadata_values_without_lineage(
    unsafe_value: str,
) -> None:
    repository = InMemoryIdeaRepository()
    try:
        reset_idea_repository_for_tests(repository=repository)
        client = TestClient(app)
        candidate_id = persisted_candidate_id(
            client,
            idempotency_key=f"seed-ai-metadata-{len(unsafe_value)}",
        )

        response = client.post(
            f"/api/v1/idea-candidates/{candidate_id}/ai-explanations/evaluate",
            json=ai_request_payload(approved_metadata={"channel": unsafe_value}),
            headers=ai_headers(idempotency_key=f"ai-metadata-value-{len(unsafe_value)}"),
        )

        assert response.status_code == 400
        assert response.json()["code"] == "invalid_ai_metadata"
        assert unsafe_value not in response.text
        assert (
            repository.snapshot().candidate_records[candidate_id].ai_explanation_lineage_records
            == ()
        )
    finally:
        reset_idea_repository_for_tests()


def test_ai_explanation_api_returns_product_safe_errors_for_invalid_output_and_metadata_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-ai-safe-errors-001")

    def raise_invalid_output(*_: Any, **__: Any) -> None:
        raise InvalidAIWorkflowOutput("output request_id does not match request")

    monkeypatch.setattr(
        ai_governance_api,
        "evaluate_ai_explanation_to_repository",
        raise_invalid_output,
    )
    invalid_output = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/ai-explanations/evaluate",
        json=ai_request_payload(),
        headers=ai_headers(idempotency_key="ai-explanation-invalid-output-api-001"),
    )
    monkeypatch.undo()

    blank_metadata_value = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/ai-explanations/evaluate",
        json=ai_request_payload(approved_metadata={"channel": " "}),
        headers=ai_headers(idempotency_key="ai-explanation-blank-metadata-api-001"),
    )

    assert invalid_output.status_code == 400
    assert invalid_output.json()["code"] == "invalid_ai_output"
    assert "request_id" not in invalid_output.text
    assert blank_metadata_value.status_code == 400
    assert blank_metadata_value.json()["code"] == "invalid_ai_metadata"


def test_ai_explanation_readiness_api_returns_source_safe_blocked_posture() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)

    response = client.get(
        "/api/v1/ai-explanations/readiness",
        headers=ai_readiness_headers(),
    )

    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == "corr-ai-readiness-api"
    payload = response.json()
    assert payload == {
        "repository": "lotus-idea",
        "sourceAuthority": "lotus-idea",
        "workflowAuthority": "lotus-ai",
        "readinessStatus": "blocked",
        "supportabilityStatus": "not_certified",
        "certificationReady": False,
        "deterministicFallbackAvailable": True,
        "verifierAvailable": True,
        "redactedEvidenceEnvelopeAvailable": True,
        "unsupportedClaimBlockingAvailable": True,
        "forbiddenActionBlockingAvailable": True,
        "actionContentPolicyVersion": "lotus-idea.ai-action-content-policy.v1",
        "lotusAiRunAttestationAvailable": True,
        "productionLikeAttestationRequired": True,
        "localTestUnattestedFixtureAllowed": True,
        "executionProvenancePolicyVersion": ("lotus-idea.ai-execution-provenance-policy.v1"),
        "metadataEnvelopeVersion": "lotus-idea.ai-metadata-envelope.v1",
        "durableAiLineageStoreBacked": False,
        "modelRiskOperationsContractAvailable": True,
        "modelRiskDashboardContractAvailable": True,
        "modelRiskAlertContractAvailable": True,
        "modelRiskDashboardCertified": True,
        "modelRiskAlertCertified": True,
        "lotusAiRuntimeExecuted": False,
        "certificationBlockers": [
            "lotus_ai_runtime_execution_missing",
            "certified_ai_lineage_store_missing",
            "workflow_pack_runtime_contract_not_certified",
            "lotus_ai_run_attestation_mainline_proof_missing",
            "certified_runtime_trust_telemetry_missing",
            "workbench_product_proof_missing",
        ],
        "supportedFeaturePromoted": False,
    }
    assert "prompt" not in response.text.lower()
    assert "provider" not in response.text.lower()
    assert "candidateId" not in response.text
    assert "portfolioId" not in response.text


def test_ai_explanation_readiness_api_reports_durable_repository_lineage_posture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    try:
        reset_idea_repository_for_tests(repository=DurableInMemoryIdeaRepository())
        events: list[tuple[str, str, str, bool, bool, str | None]] = []

        def capture(event: Any) -> None:
            events.append(
                (
                    event.operation.value,
                    event.outcome.value,
                    event.supportability_status.value,
                    event.durable_storage_backed,
                    event.supported_feature_promoted,
                    event.error_code,
                )
            )

        monkeypatch.setattr(ai_governance_api, "emit_operation_event", capture)
        client = TestClient(app)

        response = client.get(
            "/api/v1/ai-explanations/readiness",
            headers=ai_readiness_headers(),
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["durableAiLineageStoreBacked"] is True
        assert payload["readinessStatus"] == "blocked"
        assert payload["supportabilityStatus"] == "not_certified"
        assert payload["lotusAiRuntimeExecuted"] is False
        assert payload["supportedFeaturePromoted"] is False
        assert "certified_ai_lineage_store_missing" in payload["certificationBlockers"]
        assert events == [
            (
                "ai_explanation_readiness_read",
                "blocked",
                "not_certified",
                True,
                False,
                None,
            )
        ]
        assert "prompt" not in response.text.lower()
        assert "provider" not in response.text.lower()
    finally:
        reset_idea_repository_for_tests()


def test_ai_explanation_readiness_api_requires_operator_role_and_capability() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)

    missing_role = client.get(
        "/api/v1/ai-explanations/readiness",
        headers=ai_readiness_headers(roles="advisor"),
    )
    missing_capability = client.get(
        "/api/v1/ai-explanations/readiness",
        headers=ai_readiness_headers(capabilities="idea.ai-explanation.evaluate"),
    )

    assert missing_role.status_code == 403
    assert missing_role.json()["code"] == "permission_denied"
    assert missing_capability.status_code == 403
    assert missing_capability.json()["code"] == "permission_denied"
