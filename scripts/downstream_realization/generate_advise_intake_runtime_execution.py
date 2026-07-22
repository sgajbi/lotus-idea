# ruff: noqa: E402
from __future__ import annotations

import argparse
from collections.abc import Mapping
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any
from urllib import error, request


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.downstream_realization.advise_intake_runtime_execution import (  # noqa: E402
    build_advise_intake_runtime_execution_payload,
    source_safe_receipt_digest,
)

try:
    from scripts.proof_generator_io import parse_generated_at_utc, write_json_payload
except ImportError:  # pragma: no cover - supports direct script execution
    from proof_generator_io import (  # type: ignore[import-not-found,no-redef]
        parse_generated_at_utc,
        write_json_payload,
    )

ROUTE_PATH = "/advisory/proposals/idea-intake"


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        generated_at_utc = parse_generated_at_utc(args.generated_at_utc)
        if args.runtime_mode == "http_service":
            receipt_evidence = _execute_http_service(args.advise_base_url)
        else:
            receipt_evidence = _execute_advise_testclient(
                advise_root=Path(args.advise_root),
                advise_python=args.advise_python,
            )
        payload = build_advise_intake_runtime_execution_payload(
            generated_at_utc=generated_at_utc,
            repository_root=Path.cwd(),
            advise_root=Path(args.advise_root),
            runtime_mode=args.runtime_mode,
            receipt_evidence=receipt_evidence,
        )
        write_json_payload(payload, output=args.output)
        return 0
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        print(f"Advise intake runtime proof generation error: {detail}", file=sys.stderr)
        return 2
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Advise intake runtime proof generation error: {exc}", file=sys.stderr)
        return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate source-safe lotus-advise idea intake runtime-execution proof."
    )
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--advise-root", default="../lotus-advise")
    parser.add_argument(
        "--runtime-mode",
        choices=("local_asgi_testclient", "http_service"),
        default="local_asgi_testclient",
    )
    parser.add_argument("--advise-base-url")
    parser.add_argument("--advise-python", default=sys.executable)
    return parser


def _execute_advise_testclient(
    *, advise_root: Path, advise_python: str
) -> dict[str, dict[str, Any]]:
    script = r"""
import json
from fastapi.testclient import TestClient
from src.api.main import app
from src.core.proposals.idea_proposal_intake import reset_idea_proposal_intake_idempotency_for_tests

ROUTE = "/advisory/proposals/idea-intake"

def payload(intent_type="REVIEW_FOR_ADVISORY_PROPOSAL", conversion_intent_id="conversion_intent_001"):
    return {
        "source_system": "lotus-idea",
        "source_product": "lotus-idea:IdeaCandidate:v1",
        "idea_candidate_id": "idea_candidate_001",
        "conversion_intent_id": conversion_intent_id,
        "intent_type": intent_type,
        "source_refs": [{
            "source_system": "lotus-idea",
            "source_type": "IdeaCandidate",
            "source_id": "idea_candidate_001",
            "content_hash": "sha256:abc123",
        }],
    }

def headers(idempotency_key="idea-intake-proof-001", tenant_id="tenant-private-bank-sg", legal_entity_code="SGPB", capabilities="advisory.idea_proposal_intake.accept"):
    return {
        "Idempotency-Key": idempotency_key,
        "X-Actor-Id": "svc-lotus-idea",
        "X-Role": "SERVICE",
        "X-Tenant-Id": tenant_id,
        "X-Legal-Entity-Code": legal_entity_code,
        "X-Service-Identity": "lotus-idea",
        "X-Capabilities": capabilities,
        "X-Correlation-Id": "corr-idea-advise-runtime-proof",
    }

reset_idea_proposal_intake_idempotency_for_tests()
client = TestClient(app)
accepted = client.post(ROUTE, json=payload(), headers=headers())
accepted_replay = client.post(ROUTE, json=payload(), headers=headers())
rejected = client.post(
    ROUTE,
    json=payload(intent_type="CREATE_ADVISORY_PROPOSAL_DRAFT"),
    headers=headers(idempotency_key="idea-intake-proof-rejected"),
)
conflict = client.post(
    ROUTE,
    json=payload(conversion_intent_id="conversion_intent_changed"),
    headers=headers(),
)
authorization_denied = client.post(
    ROUTE,
    json=payload(),
    headers=headers(
        idempotency_key="idea-intake-proof-auth-denied",
        capabilities="advisory.proposals.read",
    ),
)
tenant_scoped = client.post(
    ROUTE,
    json=payload(),
    headers=headers(
        idempotency_key="idea-intake-proof-001",
        tenant_id="tenant-private-bank-hk",
        legal_entity_code="HKPB",
    ),
)

def response_payload(response):
    try:
        body = response.json()
    except Exception:
        body = {}
    return {"statusCode": response.status_code, "body": body}

print(json.dumps({
    "accepted": response_payload(accepted),
    "acceptedReplay": response_payload(accepted_replay),
    "rejected": response_payload(rejected),
    "idempotencyConflict": response_payload(conflict),
    "authorizationDenied": response_payload(authorization_denied),
    "tenantScopedIdempotency": response_payload(tenant_scoped),
}, sort_keys=True))
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(advise_root.resolve())
    env.setdefault("ENVIRONMENT", "test")
    env.setdefault("PROPOSAL_STORE_BACKEND", "POSTGRES")
    env.setdefault("PROPOSAL_POSTGRES_DSN", "postgresql://test:test@localhost:5432/proposals")
    env.setdefault("POLICY_STORE_BACKEND", "POSTGRES")
    env.setdefault("POLICY_POSTGRES_DSN", "postgresql://test:test@localhost:5432/policy")
    env.setdefault("WORKSPACE_STORE_BACKEND", "POSTGRES")
    env.setdefault("WORKSPACE_POSTGRES_DSN", "postgresql://test:test@localhost:5432/workspace")
    completed = subprocess.run(
        [advise_python, "-c", script],
        cwd=advise_root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    raw = json.loads(completed.stdout)
    if not isinstance(raw, dict):
        raise ValueError("Advise testclient execution did not return a JSON object")
    return _source_safe_receipts(raw)


def _execute_http_service(base_url: str | None) -> dict[str, dict[str, Any]]:
    if not base_url:
        raise ValueError("--advise-base-url is required for http_service mode")
    endpoint = f"{base_url.rstrip('/')}{ROUTE_PATH}"
    calls = {
        "accepted": _http_post(endpoint, _payload(), _headers()),
        "acceptedReplay": _http_post(endpoint, _payload(), _headers()),
        "rejected": _http_post(
            endpoint,
            _payload(intent_type="CREATE_ADVISORY_PROPOSAL_DRAFT"),
            _headers(idempotency_key="idea-intake-proof-rejected"),
        ),
        "idempotencyConflict": _http_post(
            endpoint,
            _payload(conversion_intent_id="conversion_intent_changed"),
            _headers(),
        ),
        "authorizationDenied": _http_post(
            endpoint,
            _payload(),
            _headers(
                idempotency_key="idea-intake-proof-auth-denied",
                capabilities="advisory.proposals.read",
            ),
        ),
        "tenantScopedIdempotency": _http_post(
            endpoint,
            _payload(),
            _headers(
                idempotency_key="idea-intake-proof-001",
                tenant_id="tenant-private-bank-hk",
                legal_entity_code="HKPB",
            ),
        ),
    }
    return _source_safe_receipts(calls)


def _http_post(
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


def _source_safe_receipts(raw: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    receipts: dict[str, dict[str, Any]] = {}
    for name, response in raw.items():
        body = response.get("body") if isinstance(response, Mapping) else {}
        receipt = {
            "statusCode": response.get("statusCode") if isinstance(response, Mapping) else None,
            "intakeStatus": _body_get(body, "intake_status"),
            "intakeReceiptAccepted": _body_get(body, "intake_receipt_accepted"),
            "idempotencyReplay": _body_get(body, "idempotency_replay"),
            "receiptDigest": None,
            "reasonCodes": _reason_codes(body),
            "proposalRecordCreated": bool(_body_get(body, "proposal_record_created") or False),
            "suitabilityAuthorityGranted": bool(
                _body_get(body, "suitability_authority_granted") or False
            ),
            "orderCreated": bool(_body_get(body, "order_created") or False),
            "clientPublicationAuthorized": bool(
                _body_get(body, "client_publication_authorized") or False
            ),
        }
        receipt["receiptDigest"] = source_safe_receipt_digest(receipt)
        receipts[str(name)] = receipt
    return receipts


def _body_get(body: object, key: str) -> object:
    if isinstance(body, Mapping):
        return body.get(key)
    return None


def _reason_codes(body: object) -> list[str]:
    if not isinstance(body, Mapping):
        return []
    reason_codes = body.get("outcome_reason_codes")
    if isinstance(reason_codes, list):
        return [str(item) for item in reason_codes]
    detail = body.get("detail")
    if isinstance(detail, str):
        return [detail]
    return []


def _payload(
    *,
    intent_type: str = "REVIEW_FOR_ADVISORY_PROPOSAL",
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


def _headers(
    *,
    idempotency_key: str = "idea-intake-proof-001",
    tenant_id: str = "tenant-private-bank-sg",
    legal_entity_code: str = "SGPB",
    capabilities: str = "advisory.idea_proposal_intake.accept",
) -> dict[str, str]:
    return {
        "Idempotency-Key": idempotency_key,
        "X-Actor-Id": "svc-lotus-idea",
        "X-Role": "SERVICE",
        "X-Tenant-Id": tenant_id,
        "X-Legal-Entity-Code": legal_entity_code,
        "X-Service-Identity": "lotus-idea",
        "X-Capabilities": capabilities,
        "X-Correlation-Id": "corr-idea-advise-runtime-proof",
    }


if __name__ == "__main__":
    sys.exit(main())
