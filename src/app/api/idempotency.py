from __future__ import annotations

from collections.abc import Mapping
from typing import Any

IDEMPOTENCY_KEY_REQUIRED_MESSAGE = "idempotency key is required"
REQUIRED_OPENAPI_IDEMPOTENCY_OPERATIONS = (
    ("post", "/api/v1/idea-signals/high-cash/evaluate-and-persist"),
    ("post", "/api/v1/idea-candidates/{candidateId}/lifecycle-transitions"),
    ("post", "/api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate"),
    ("post", "/api/v1/idea-candidates/{candidateId}/review-actions"),
    ("post", "/api/v1/idea-candidates/{candidateId}/feedback"),
    ("post", "/api/v1/idea-candidates/{candidateId}/conversion-intents"),
    ("post", "/api/v1/conversion-intents/{conversionIntentId}/downstream-submissions"),
    ("post", "/api/v1/conversion-intents/{conversionIntentId}/outcomes"),
    ("post", "/api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs"),
    ("post", "/api/v1/report-evidence-packs/{reportEvidencePackId}/downstream-submissions"),
    ("post", "/api/v1/outbox-delivery/run-once"),
)


def validate_idempotency_key(idempotency_key: str) -> None:
    if not idempotency_key.strip():
        raise ValueError(IDEMPOTENCY_KEY_REQUIRED_MESSAGE)


def mark_required_idempotency_openapi_headers(openapi_schema: dict[str, Any]) -> dict[str, Any]:
    paths = openapi_schema.get("paths")
    if not isinstance(paths, Mapping):
        return openapi_schema
    for method, path in REQUIRED_OPENAPI_IDEMPOTENCY_OPERATIONS:
        path_item = paths.get(path)
        if not isinstance(path_item, Mapping):
            continue
        operation = path_item.get(method)
        if not isinstance(operation, dict):
            continue
        parameters = operation.get("parameters")
        if not isinstance(parameters, list):
            continue
        for parameter in parameters:
            if not isinstance(parameter, dict):
                continue
            if parameter.get("name") != "Idempotency-Key" or parameter.get("in") != "header":
                continue
            parameter["required"] = True
            schema = parameter.get("schema")
            if isinstance(schema, dict):
                schema.pop("default", None)
    return openapi_schema
