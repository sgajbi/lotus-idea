from app.errors import ProblemDetails
from app.main import SERVICE_NAME


def test_service_name_is_lotus_prefixed() -> None:
    assert SERVICE_NAME.startswith("lotus-")


def test_problem_details_are_product_safe() -> None:
    problem = ProblemDetails(
        code="invalid_request",
        title="Invalid request",
        detail="Correct the request fields and retry.",
    )
    payload = problem.model_dump()
    assert payload == {
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


def test_endpoint_certification_ledger_starts_with_scaffold_operations() -> None:
    import json
    from pathlib import Path

    payload = json.loads(Path("docs/operations/endpoint-certification-ledger.json").read_text())
    operations = {(endpoint["method"], endpoint["path"]) for endpoint in payload["endpoints"]}
    assert operations == {
        ("GET", "/health"),
        ("GET", "/health/live"),
        ("GET", "/health/ready"),
        ("GET", "/metadata"),
    }
    assert (
        payload["policy"]
        == "Every public OpenAPI operation requires certification evidence before promotion."
    )
