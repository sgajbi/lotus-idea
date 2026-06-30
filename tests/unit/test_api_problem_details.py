from __future__ import annotations

from app.api.problem_details import (
    invalid_request_metadata,
    invalid_request_problem,
    permission_denied_problem,
)
from app.main import app


WORKFLOW_OPERATIONS = (
    ("post", "/api/v1/idea-candidates/{candidateId}/lifecycle-transitions", (400, 403, 404, 409)),
    ("post", "/api/v1/idea-candidates/{candidateId}/review-actions", (400, 403, 404, 409)),
    ("post", "/api/v1/idea-candidates/{candidateId}/feedback", (400, 403, 404, 409)),
    ("post", "/api/v1/idea-candidates/{candidateId}/conversion-intents", (400, 403, 404, 409)),
    ("post", "/api/v1/conversion-intents/{conversionIntentId}/outcomes", (400, 403, 404, 409)),
    (
        "post",
        "/api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs",
        (400, 403, 404, 409),
    ),
)


def test_problem_details_metadata_includes_product_safe_example() -> None:
    metadata = invalid_request_metadata(
        detail="Correct the lifecycle transition request and retry."
    )

    example = metadata[400]["content"]["application/json"]["example"]

    assert example == {
        "type": "about:blank",
        "status": 400,
        "code": "invalid_request",
        "title": "Invalid request",
        "detail": "Correct the lifecycle transition request and retry.",
    }


def test_permission_denied_problem_response_is_product_safe() -> None:
    response = permission_denied_problem("The caller is not permitted to record idea reviews.")

    assert response.status_code == 403
    assert b"permission_denied" in response.body
    assert b"The caller is not permitted to record idea reviews." in response.body


def test_invalid_request_problem_response_is_product_safe() -> None:
    response = invalid_request_problem("Correct the review workflow request and retry.")

    assert response.status_code == 400
    assert b"invalid_request" in response.body
    assert b"Correct the review workflow request and retry." in response.body


def test_workflow_openapi_error_responses_have_problem_details_examples() -> None:
    openapi = app.openapi()

    for method, path, status_codes in WORKFLOW_OPERATIONS:
        responses = openapi["paths"][path][method]["responses"]
        for status_code in status_codes:
            response = responses[str(status_code)]
            assert response["content"]["application/json"]["example"]["status"] == status_code
            assert response["content"]["application/json"]["example"]["type"] == "about:blank"
            assert response["content"]["application/json"]["example"]["code"]
            assert response["content"]["application/json"]["example"]["detail"]
