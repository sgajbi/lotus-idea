from fastapi.testclient import TestClient

from app.main import app


def test_http_sli_scrape_uses_route_templates_without_resource_identity() -> None:
    client = TestClient(app)
    candidate_id = "sensitive-candidate-identity"

    response = client.get(
        f"/api/v1/idea-candidates/{candidate_id}",
        headers={
            "X-Caller-Subject": "advisor-redacted",
            "X-Caller-Roles": "advisor",
            "X-Caller-Capabilities": "idea.candidate.detail.read",
            "X-Caller-Tenant-Ids": "tenant-private-bank-sg",
        },
    )
    metrics = client.get("/metrics")

    assert response.status_code == 404
    assert metrics.status_code == 200
    assert "lotus_idea_http_requests_total" in metrics.text
    assert "lotus_idea_http_request_duration_seconds_bucket" in metrics.text
    assert 'route="/api/v1/idea-candidates/{candidateId}"' in metrics.text
    assert candidate_id not in metrics.text
    assert "tenant-private-bank-sg" not in metrics.text
