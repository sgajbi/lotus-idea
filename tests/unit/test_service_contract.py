from app.errors import ProblemDetails
from app.application.service_profile import current_service_profile
from app.domain.service_profile import DEFAULT_SERVICE_PROFILE, ServiceProfile
from app.main import SERVICE_NAME


def test_service_name_is_lotus_prefixed() -> None:
    assert SERVICE_NAME.startswith("lotus-")


def test_service_profile_is_domain_authoritative() -> None:
    profile = current_service_profile()
    assert profile is DEFAULT_SERVICE_PROFILE
    assert profile.name == "domain-service"
    assert "Domain-authoritative" in profile.description
    assert ServiceProfile(name=profile.name, description=profile.description) == profile


def test_problem_details_are_product_safe() -> None:
    problem = ProblemDetails(
        status=400,
        code="invalid_request",
        title="Invalid request",
        detail="Correct the request fields and retry.",
    )
    payload = problem.model_dump()
    assert payload == {
        "type": "about:blank",
        "status": 400,
        "code": "invalid_request",
        "title": "Invalid request",
        "detail": "Correct the request fields and retry.",
    }
    assert "portfolio" not in payload["detail"].lower()
    assert "holding" not in payload["detail"].lower()


def test_supported_features_policy_starts_unpromoted() -> None:
    import json
    from pathlib import Path

    payload = json.loads(Path("supported-features/supported-features.json").read_text())
    assert payload["features"] == []
    assert payload["policy"] == "Only implementation-backed behavior may be promoted to supported."


def test_endpoint_certification_ledger_matches_public_operations() -> None:
    import json
    from pathlib import Path

    payload = json.loads(Path("docs/operations/endpoint-certification-ledger.json").read_text())
    operations = {(endpoint["method"], endpoint["path"]) for endpoint in payload["endpoints"]}
    assert operations == {
        ("GET", "/api/v1/ai-explanations/readiness"),
        ("GET", "/api/v1/data-mesh/readiness"),
        ("GET", "/api/v1/data-mesh/trust-telemetry/runtime-preview"),
        ("GET", "/api/v1/data-mesh/trust-telemetry/runtime-snapshot"),
        ("GET", "/api/v1/downstream-realization/readiness"),
        ("GET", "/api/v1/implementation-proof/readiness"),
        ("GET", "/api/v1/outbox-delivery/readiness"),
        ("GET", "/api/v1/source-ingestion/readiness"),
        ("POST", "/api/v1/source-ingestion/run-once"),
        ("GET", "/api/v1/review-queues/advisor"),
        ("GET", "/api/v1/review-queues/advisor/readiness"),
        ("POST", "/api/v1/conversion-intents/{conversionIntentId}/downstream-submissions"),
        ("POST", "/api/v1/conversion-intents/{conversionIntentId}/outcomes"),
        ("POST", "/api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs"),
        ("POST", "/api/v1/outbox-delivery/run-once"),
        ("GET", "/api/v1/idea-candidates/{candidateId}"),
        ("POST", "/api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate"),
        ("POST", "/api/v1/idea-candidates/{candidateId}/conversion-intents"),
        ("POST", "/api/v1/idea-candidates/{candidateId}/evidence-replay"),
        ("POST", "/api/v1/idea-candidates/{candidateId}/feedback"),
        ("POST", "/api/v1/idea-candidates/{candidateId}/lifecycle-transitions"),
        ("POST", "/api/v1/idea-candidates/{candidateId}/review-actions"),
        ("POST", "/api/v1/idea-signals/high-cash/evaluate"),
        ("POST", "/api/v1/idea-signals/high-cash/evaluate-and-persist"),
        ("POST", "/api/v1/idea-signals/low-income/evaluate"),
        ("POST", "/api/v1/idea-signals/mandate-restriction/evaluate"),
        ("POST", "/api/v1/idea-signals/missing-benchmark/evaluate"),
        ("POST", "/api/v1/idea-signals/missing-risk-profile/evaluate"),
        ("POST", "/api/v1/idea-signals/missing-suitability/evaluate"),
        ("POST", "/api/v1/report-evidence-packs/{reportEvidencePackId}/downstream-submissions"),
        ("GET", "/health"),
        ("GET", "/health/live"),
        ("GET", "/health/ready"),
        ("GET", "/metadata"),
    }
    assert (
        payload["policy"]
        == "Every public OpenAPI operation requires certification evidence before promotion."
    )
