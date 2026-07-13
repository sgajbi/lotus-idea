from app.errors import ProblemDetails
from pytest import MonkeyPatch
from app.application.service_profile import current_service_profile
from app.domain.service_profile import DEFAULT_SERVICE_PROFILE, ServiceProfile
from app.main import BUILD_METADATA, SERVICE_NAME, app


def test_service_name_is_lotus_prefixed() -> None:
    assert SERVICE_NAME.startswith("lotus-")


def test_version_endpoint_exposes_build_metadata() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(app)
    metadata_response = client.get("/metadata")
    version_response = client.get("/version")

    assert metadata_response.status_code == 200
    assert version_response.status_code == 200
    assert version_response.json() == metadata_response.json()
    assert version_response.json()["build"] == BUILD_METADATA
    assert set(version_response.json()["build"]) == {
        "gitCommitSha",
        "gitBranch",
        "buildTimestamp",
        "repoUrl",
        "ciRunId",
        "imageBuildId",
        "imageIdentityContractVersion",
        "registryDigestBinding",
        "imageDigest",
        "imageDigestReference",
        "releaseIdentityStatus",
    }


def test_version_endpoint_exposes_digest_bound_runtime_identity(monkeypatch: MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    digest = f"sha256:{'a' * 64}"
    reference = f"ghcr.io/sgajbi/lotus-idea@{digest}"
    monkeypatch.setenv("LOTUS_RELEASE_IMAGE_DIGEST", digest)
    monkeypatch.setenv("LOTUS_RELEASE_IMAGE_DIGEST_REFERENCE", reference)

    payload = TestClient(app).get("/version").json()["build"]

    assert payload["imageDigest"] == digest
    assert payload["imageDigestReference"] == reference
    assert payload["releaseIdentityStatus"] == "digest_bound"


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
        ("POST", "/api/v1/data-lifecycle/candidates/{candidateId}/actions"),
        ("GET", "/api/v1/downstream-realization/readiness"),
        ("GET", "/api/v1/downstream-submissions/reconciliation"),
        ("GET", "/api/v1/implementation-proof/readiness"),
        ("GET", "/api/v1/outbox-delivery/readiness"),
        ("GET", "/api/v1/outbox-delivery/dead-letters"),
        ("GET", "/api/v1/source-ingestion/readiness"),
        ("POST", "/api/v1/source-ingestion/run-once"),
            ("GET", "/api/v1/review-queues/advisor"),
            ("GET", "/api/v1/review-queues/portfolio-manager"),
            ("GET", "/api/v1/review-queues/compliance"),
            ("GET", "/api/v1/review-queues/advisor/readiness"),
        ("POST", "/api/v1/conversion-intents/{conversionIntentId}/downstream-submissions"),
        ("POST", "/api/v1/conversion-intents/{conversionIntentId}/outcomes"),
        ("POST", "/api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs"),
        ("POST", "/api/v1/outbox-delivery/run-once"),
        (
            "POST",
            "/api/v1/downstream-submissions/reconciliation/{supportReference}",
        ),
        (
            "POST",
            "/api/v1/outbox-delivery/dead-letters/{supportReference}/redrive",
        ),
        ("GET", "/api/v1/idea-candidates/{candidateId}"),
        ("POST", "/api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate"),
        ("POST", "/api/v1/idea-candidates/{candidateId}/conversion-intents"),
        ("POST", "/api/v1/idea-candidates/{candidateId}/evidence-replay"),
        ("POST", "/api/v1/idea-candidates/{candidateId}/feedback"),
        ("POST", "/api/v1/idea-candidates/{candidateId}/lifecycle-transitions"),
        ("POST", "/api/v1/idea-candidates/{candidateId}/review-actions"),
        ("POST", "/api/v1/idea-signals/allocation-drift/evaluate"),
        ("POST", "/api/v1/idea-signals/allocation-drift/evaluate-from-source"),
        ("POST", "/api/v1/idea-signals/bond-maturity/evaluate"),
        ("POST", "/api/v1/idea-signals/bond-maturity/evaluate-from-source"),
        ("POST", "/api/v1/idea-signals/concentration-risk/evaluate"),
        ("POST", "/api/v1/idea-signals/concentration-risk/evaluate-from-source"),
        ("POST", "/api/v1/idea-signals/drawdown-review/evaluate"),
        ("POST", "/api/v1/idea-signals/drawdown-review/evaluate-from-source"),
        ("POST", "/api/v1/idea-signals/high-volatility/evaluate"),
        ("POST", "/api/v1/idea-signals/high-volatility/evaluate-from-source"),
        ("POST", "/api/v1/idea-signals/high-cash/evaluate"),
        ("POST", "/api/v1/idea-signals/high-cash/evaluate-from-source"),
        ("POST", "/api/v1/idea-signals/high-cash/evaluate-and-persist"),
        ("POST", "/api/v1/idea-signals/low-income/evaluate"),
        ("POST", "/api/v1/idea-signals/low-income/evaluate-from-source"),
        ("POST", "/api/v1/idea-signals/mandate-restriction/evaluate"),
        ("POST", "/api/v1/idea-signals/mandate-restriction/evaluate-from-source"),
        ("POST", "/api/v1/idea-signals/missing-benchmark/evaluate"),
        ("POST", "/api/v1/idea-signals/missing-benchmark/evaluate-from-source"),
        ("POST", "/api/v1/idea-signals/missing-risk-profile/evaluate"),
        ("POST", "/api/v1/idea-signals/missing-risk-profile/evaluate-from-source"),
        ("POST", "/api/v1/idea-signals/missing-suitability/evaluate-from-source"),
        ("POST", "/api/v1/idea-signals/missing-suitability/evaluate"),
        ("POST", "/api/v1/idea-signals/underperformance/evaluate"),
        ("POST", "/api/v1/idea-signals/underperformance/evaluate-from-source"),
        ("POST", "/api/v1/report-evidence-packs/{reportEvidencePackId}/downstream-submissions"),
        ("GET", "/health"),
        ("GET", "/health/live"),
        ("GET", "/health/ready"),
        ("GET", "/metadata"),
        ("GET", "/version"),
    }
    assert (
        payload["policy"]
        == "Every public OpenAPI operation requires certification evidence before promotion."
    )


def test_lifecycle_transition_openapi_excludes_downstream_authority_input_statuses() -> None:
    schema = app.openapi()
    request_schema = schema["components"]["schemas"]["CandidateLifecycleTransitionRequest"]
    target_ref = request_schema["properties"]["targetLifecycleStatus"]["$ref"]
    target_schema_name = target_ref.removeprefix("#/components/schemas/")
    target_enum = set(schema["components"]["schemas"][target_schema_name]["enum"])

    assert target_schema_name == "CallerSettableIdeaLifecycleStatus"
    assert {"accepted", "executed"}.isdisjoint(target_enum)
    assert {"approved", "converted_to_report", "closed"}.issubset(target_enum)
    assert {"accepted", "executed"}.issubset(
        set(schema["components"]["schemas"]["IdeaLifecycleStatus"]["enum"])
    )


def test_source_ingestion_openapi_publishes_both_dependency_failure_codes() -> None:
    schema = app.openapi()
    response = schema["paths"]["/api/v1/source-ingestion/run-once"]["post"]["responses"]["502"]

    assert set(response["content"]["application/problem+json"]["examples"]) == {
        "source_dependency_entitlement_denied",
        "source_dependency_unavailable",
    }
    assert response["content"]["application/problem+json"]["schema"] == {
        "$ref": "#/components/schemas/ProblemDetails"
    }
