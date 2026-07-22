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


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.downstream_realization.manage_intake_runtime_execution import (  # noqa: E402
    build_manage_intake_runtime_execution_payload,
    source_safe_manage_receipt_digest,
)
from scripts.downstream_realization.intake_runtime_generator_common import (  # noqa: E402
    body_get,
    http_post,
    idea_conversion_payload,
    reason_codes,
)

try:
    from scripts.proof_generator_io import parse_generated_at_utc, write_json_payload
except ImportError:  # pragma: no cover - supports direct script execution
    from proof_generator_io import (  # type: ignore[import-not-found,no-redef]
        parse_generated_at_utc,
        write_json_payload,
    )

ROUTE_PATH = "/api/v1/rebalance/idea-action-intake"


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        generated_at_utc = parse_generated_at_utc(args.generated_at_utc)
        if args.runtime_mode == "http_service":
            receipt_evidence = _execute_http_service(args.manage_base_url)
        else:
            receipt_evidence = _execute_manage_testclient(
                manage_root=Path(args.manage_root),
                manage_python=args.manage_python,
            )
        payload = build_manage_intake_runtime_execution_payload(
            generated_at_utc=generated_at_utc,
            repository_root=Path.cwd(),
            manage_root=Path(args.manage_root),
            runtime_mode=args.runtime_mode,
            receipt_evidence=receipt_evidence,
        )
        write_json_payload(payload, output=args.output)
        return 0
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        print(f"Manage intake runtime proof generation error: {detail}", file=sys.stderr)
        return 2
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Manage intake runtime proof generation error: {exc}", file=sys.stderr)
        return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate source-safe lotus-manage idea action-intake runtime-execution proof."
    )
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--manage-root", default="../lotus-manage")
    parser.add_argument(
        "--runtime-mode",
        choices=("local_asgi_testclient", "http_service"),
        default="local_asgi_testclient",
    )
    parser.add_argument("--manage-base-url")
    parser.add_argument("--manage-python", default=sys.executable)
    return parser


def _execute_manage_testclient(
    *, manage_root: Path, manage_python: str
) -> dict[str, dict[str, Any]]:
    script = r"""
import json
from fastapi.testclient import TestClient
from src.api.main import app
from src.core.rebalance_runs import reset_idea_action_intake_idempotency_for_tests

ROUTE = "/api/v1/rebalance/idea-action-intake"

def payload(intent_type="REVIEW_FOR_REBALANCE", conversion_intent_id="conversion_intent_001"):
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

def headers(idempotency_key="idea-action-intake-proof-001", tenant_id="tenant-private-bank-sg", legal_entity_code="SGPB", capabilities="manage.idea_action_intake.accept"):
    return {
        "Idempotency-Key": idempotency_key,
        "X-Actor-Id": "svc-lotus-idea",
        "X-Role": "SERVICE",
        "X-Tenant-Id": tenant_id,
        "X-Legal-Entity-Code": legal_entity_code,
        "X-Service-Identity": "lotus-idea",
        "X-Capabilities": capabilities,
        "X-Correlation-Id": "corr-idea-manage-runtime-proof",
        "X-Principal-Status": "ACTIVE",
    }

reset_idea_action_intake_idempotency_for_tests()
client = TestClient(app)
accepted = client.post(ROUTE, json=payload(), headers=headers())
accepted_replay = client.post(ROUTE, json=payload(), headers=headers())
rejected = client.post(
    ROUTE,
    json=payload(intent_type="CREATE_MANAGEMENT_ACTION_DRAFT"),
    headers=headers(idempotency_key="idea-action-intake-proof-rejected"),
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
        idempotency_key="idea-action-intake-proof-auth-denied",
        capabilities="manage.rebalance.read",
    ),
)
tenant_scoped = client.post(
    ROUTE,
    json=payload(),
    headers=headers(
        idempotency_key="idea-action-intake-proof-001",
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
    env["PYTHONPATH"] = str(manage_root.resolve())
    env.setdefault("ENVIRONMENT", "test")
    completed = subprocess.run(
        [manage_python, "-c", script],
        cwd=manage_root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    raw = json.loads(completed.stdout)
    if not isinstance(raw, dict):
        raise ValueError("Manage testclient execution did not return a JSON object")
    return _source_safe_receipts(raw)


def _execute_http_service(base_url: str | None) -> dict[str, dict[str, Any]]:
    if not base_url:
        raise ValueError("--manage-base-url is required for http_service mode")
    endpoint = f"{base_url.rstrip('/')}{ROUTE_PATH}"
    calls = {
        "accepted": http_post(
            endpoint,
            idea_conversion_payload(intent_type="REVIEW_FOR_REBALANCE"),
            _headers(),
        ),
        "acceptedReplay": http_post(
            endpoint,
            idea_conversion_payload(intent_type="REVIEW_FOR_REBALANCE"),
            _headers(),
        ),
        "rejected": http_post(
            endpoint,
            idea_conversion_payload(intent_type="CREATE_MANAGEMENT_ACTION_DRAFT"),
            _headers(idempotency_key="idea-action-intake-proof-rejected"),
        ),
        "idempotencyConflict": http_post(
            endpoint,
            idea_conversion_payload(
                intent_type="REVIEW_FOR_REBALANCE",
                conversion_intent_id="conversion_intent_changed",
            ),
            _headers(),
        ),
        "authorizationDenied": http_post(
            endpoint,
            idea_conversion_payload(intent_type="REVIEW_FOR_REBALANCE"),
            _headers(
                idempotency_key="idea-action-intake-proof-auth-denied",
                capabilities="manage.rebalance.read",
            ),
        ),
        "tenantScopedIdempotency": http_post(
            endpoint,
            idea_conversion_payload(intent_type="REVIEW_FOR_REBALANCE"),
            _headers(
                idempotency_key="idea-action-intake-proof-001",
                tenant_id="tenant-private-bank-hk",
                legal_entity_code="HKPB",
            ),
        ),
    }
    return _source_safe_receipts(calls)


def _source_safe_receipts(raw: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    receipts: dict[str, dict[str, Any]] = {}
    for name, response in raw.items():
        body = response.get("body") if isinstance(response, Mapping) else {}
        receipt = {
            "statusCode": response.get("statusCode") if isinstance(response, Mapping) else None,
            "intakeStatus": body_get(body, "intake_status"),
            "intakeReceiptAccepted": body_get(body, "action_receipt_accepted"),
            "idempotencyReplay": body_get(body, "idempotency_replay"),
            "receiptDigest": None,
            "reasonCodes": reason_codes(body),
            "actionRegisterCreated": bool(body_get(body, "action_register_created") or False),
            "rebalanceExecutionAuthorityGranted": bool(
                body_get(body, "rebalance_execution_authority_granted") or False
            ),
            "orderCreated": bool(body_get(body, "order_created") or False),
            "clientPublicationAuthorized": bool(
                body_get(body, "client_publication_authorized") or False
            ),
        }
        receipt["receiptDigest"] = source_safe_manage_receipt_digest(receipt)
        receipts[str(name)] = receipt
    return receipts


def _headers(
    *,
    idempotency_key: str = "idea-action-intake-proof-001",
    tenant_id: str = "tenant-private-bank-sg",
    legal_entity_code: str = "SGPB",
    capabilities: str = "manage.idea_action_intake.accept",
) -> dict[str, str]:
    return {
        "Idempotency-Key": idempotency_key,
        "X-Actor-Id": "svc-lotus-idea",
        "X-Role": "SERVICE",
        "X-Tenant-Id": tenant_id,
        "X-Legal-Entity-Code": legal_entity_code,
        "X-Service-Identity": "lotus-idea",
        "X-Capabilities": capabilities,
        "X-Correlation-Id": "corr-idea-manage-runtime-proof",
        "X-Principal-Status": "ACTIVE",
    }


if __name__ == "__main__":
    sys.exit(main())
