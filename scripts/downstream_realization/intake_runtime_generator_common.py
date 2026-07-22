from __future__ import annotations

from collections.abc import Mapping
import json
from typing import Any
from urllib import error, request


def http_post(
    endpoint: str, payload: Mapping[str, Any], headers: Mapping[str, str]
) -> dict[str, Any]:
    encoded = json.dumps(payload).encode()
    req = request.Request(
        endpoint,
        data=encoded,
        headers={**dict(headers), "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=15) as response:
            body = json.loads(response.read().decode())
            return {"statusCode": response.status, "body": body}
    except error.HTTPError as exc:
        body = json.loads(exc.read().decode())
        return {"statusCode": exc.code, "body": body}


def body_get(body: object, key: str) -> object:
    if isinstance(body, Mapping):
        return body.get(key)
    return None


def reason_codes(body: object) -> list[str]:
    if not isinstance(body, Mapping):
        return []
    outcome_reason_codes = body.get("outcome_reason_codes")
    if isinstance(outcome_reason_codes, list):
        return [str(item) for item in outcome_reason_codes]
    detail = body.get("detail")
    if isinstance(detail, str):
        return [detail]
    return []


def idea_conversion_payload(
    *,
    intent_type: str,
    conversion_intent_id: str = "conversion_intent_001",
) -> dict[str, Any]:
    return {
        "source_system": "lotus-idea",
        "source_product": "lotus-idea:IdeaCandidate:v1",
        "idea_candidate_id": "idea_candidate_001",
        "conversion_intent_id": conversion_intent_id,
        "intent_type": intent_type,
        "source_refs": [
            {
                "source_system": "lotus-idea",
                "source_type": "IdeaCandidate",
                "source_id": "idea_candidate_001",
                "content_hash": "sha256:abc123",
            }
        ],
    }
