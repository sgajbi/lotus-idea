# ruff: noqa: E402
from __future__ import annotations

import argparse
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any
from uuid import uuid4


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.downstream_realization.advise_intake_runtime_execution import (  # noqa: E402
    build_advise_intake_runtime_execution_payload,
)
from scripts.downstream_realization.advise_runtime_evidence_projection import (  # noqa: E402
    source_safe_execution_evidence,
)
from scripts.downstream_realization.intake_runtime_generator_common import (  # noqa: E402
    body_get,
    http_get,
    http_post,
    idea_conversion_payload,
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
            execution_evidence = _execute_http_service(args.advise_base_url)
        else:
            execution_evidence = _execute_advise_testclient(
                advise_root=Path(args.advise_root),
                advise_python=args.advise_python,
            )
        payload = build_advise_intake_runtime_execution_payload(
            generated_at_utc=generated_at_utc,
            repository_root=Path.cwd(),
            advise_root=Path(args.advise_root),
            runtime_mode=args.runtime_mode,
            receipt_evidence={
                name: evidence
                for name, evidence in execution_evidence.items()
                if name not in {"ownerRealization", "submittedIntent"}
            },
            submitted_intent_evidence=execution_evidence["submittedIntent"],
            owner_realization_evidence=execution_evidence["ownerRealization"],
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
    completed = _run_advise_testclient_script(
        advise_root=advise_root,
        advise_python=advise_python,
        script=_advise_testclient_script(),
        env=_advise_testclient_env(advise_root),
    )
    return source_safe_execution_evidence(
        _json_object_from_stdout(
            completed.stdout,
            "Advise testclient execution did not return a JSON object",
        )
    )


def _advise_testclient_script() -> str:
    return _advise_testclient_setup_script() + _advise_testclient_scenario_script()


def _advise_testclient_setup_script() -> str:
    return r"""
import json
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from uuid import uuid4
from src.api.main import app
from src.core.proposals.idea_proposal_intake import reset_idea_proposal_intake_idempotency_for_tests
ROUTE = "/advisory/proposals/idea-intake"
RUN_ID = uuid4().hex
def payload(intent_type="REVIEW_FOR_ADVISORY_PROPOSAL", conversion_intent_id=None):
    resolved_conversion_intent_id = conversion_intent_id or f"conversion_intent_{RUN_ID}"
    return {
        "source_system": "lotus-idea",
        "source_product": "lotus-idea:IdeaCandidate:v1",
        "idea_candidate_id": "idea_candidate_001",
        "conversion_intent_id": resolved_conversion_intent_id,
        "intent_type": intent_type,
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "source_refs": [{
            "source_system": "lotus-idea",
            "source_type": "IdeaCandidate",
            "source_id": "idea_candidate_001",
            "content_hash": "sha256:abc123",
        }],
    }
def headers(idempotency_key=None, tenant_id="tenant-private-bank-sg", legal_entity_code="SGPB", capabilities="advisory.idea_proposal_intake.accept"):
    resolved_idempotency_key = idempotency_key or f"idea-intake-proof-{RUN_ID}"
    return {
        "Idempotency-Key": resolved_idempotency_key,
        "X-Actor-Id": "svc-lotus-idea",
        "X-Role": "SERVICE",
        "X-Tenant-Id": tenant_id,
        "X-Legal-Entity-Code": legal_entity_code,
        "X-Service-Identity": "lotus-idea",
        "X-Capabilities": capabilities,
        "X-Correlation-Id": "corr-idea-advise-runtime-proof",
    }
"""


def _advise_testclient_scenario_script() -> str:
    return r"""

reset_idea_proposal_intake_idempotency_for_tests()
client = TestClient(app)
accepted = client.post(ROUTE, json=payload(), headers=headers())
accepted_replay = client.post(ROUTE, json=payload(), headers=headers())
with ThreadPoolExecutor(max_workers=2) as executor:
    concurrent_responses = [
        future.result()
        for future in (
            executor.submit(
                client.post,
                ROUTE,
                json=payload(conversion_intent_id=f"conversion_intent_concurrent_{RUN_ID}"),
                headers=headers(idempotency_key=f"idea-intake-proof-concurrent-{RUN_ID}"),
            ),
            executor.submit(
                client.post,
                ROUTE,
                json=payload(conversion_intent_id=f"conversion_intent_concurrent_{RUN_ID}"),
                headers=headers(idempotency_key=f"idea-intake-proof-concurrent-{RUN_ID}"),
            ),
        )
    ]
concurrent = {
    response.json().get("intake_status"): response for response in concurrent_responses
}
rejected = client.post(
    ROUTE,
    json=payload(
        intent_type="CREATE_ADVISORY_PROPOSAL_DRAFT",
        conversion_intent_id=f"conversion_intent_rejected_{RUN_ID}",
    ),
    headers=headers(idempotency_key=f"idea-intake-proof-rejected-{RUN_ID}"),
)
conflict = client.post(
    ROUTE,
    json=payload(conversion_intent_id=f"conversion_intent_changed_{RUN_ID}"),
    headers=headers(),
)
authorization_denied = client.post(
    ROUTE,
    json=payload(),
    headers=headers(
        idempotency_key=f"idea-intake-proof-auth-denied-{RUN_ID}",
        capabilities="advisory.proposals.read",
    ),
)
tenant_scoped = client.post(
    ROUTE,
    json=payload(),
    headers=headers(
        idempotency_key=f"idea-intake-proof-{RUN_ID}",
        tenant_id="tenant-private-bank-hk",
        legal_entity_code="HKPB",
    ),
)
owner_realization = client.get(
    f"{ROUTE}/{accepted.json()['intake_id']}/realization",
    headers={
        **headers(capabilities="advisory.idea_proposal_realization.read"),
        "X-Portfolio-Id": accepted.json()["portfolio_id"],
        "X-Authorized-Portfolio-Id": accepted.json()["portfolio_id"],
    },
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
    "concurrentAccepted": response_payload(concurrent["ACCEPTED"]),
    "concurrentReplay": response_payload(concurrent["ACCEPTED_REPLAYED"]),
    "rejected": response_payload(rejected),
    "idempotencyConflict": response_payload(conflict),
    "authorizationDenied": response_payload(authorization_denied),
    "tenantScopedIdempotency": response_payload(tenant_scoped),
    "ownerRealization": response_payload(owner_realization),
    "submittedIntent": {
        "ideaCandidateId": "idea_candidate_001",
        "conversionIntentId": f"conversion_intent_{RUN_ID}",
        "portfolioId": "PB_SG_GLOBAL_BAL_001",
        "tenantId": "tenant-private-bank-sg",
        "legalEntityCode": "SGPB",
    },
}, sort_keys=True))
"""


def _advise_testclient_env(advise_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(advise_root.resolve())
    env.setdefault("ENVIRONMENT", "test")
    env.setdefault("PROPOSAL_STORE_BACKEND", "POSTGRES")
    env.setdefault("PROPOSAL_POSTGRES_DSN", "postgresql://test:test@localhost:5432/proposals")
    env.setdefault("POLICY_STORE_BACKEND", "POSTGRES")
    env.setdefault("POLICY_POSTGRES_DSN", "postgresql://test:test@localhost:5432/policy")
    env.setdefault("WORKSPACE_STORE_BACKEND", "POSTGRES")
    env.setdefault("WORKSPACE_POSTGRES_DSN", "postgresql://test:test@localhost:5432/workspace")
    return env


def _run_advise_testclient_script(
    *,
    advise_root: Path,
    advise_python: str,
    script: str,
    env: Mapping[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [advise_python, "-c", script],
        cwd=advise_root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def _json_object_from_stdout(stdout: str, error_message: str) -> dict[str, Any]:
    raw = json.loads(stdout)
    if not isinstance(raw, dict):
        raise ValueError(error_message)
    return raw


def _execute_http_service(base_url: str | None) -> dict[str, dict[str, Any]]:
    if not base_url:
        raise ValueError("--advise-base-url is required for http_service mode")
    endpoint = f"{base_url.rstrip('/')}{ROUTE_PATH}"
    run_id = uuid4().hex
    idempotency_key = f"idea-intake-proof-{run_id}"
    submitted_payload = idea_conversion_payload(
        intent_type="REVIEW_FOR_ADVISORY_PROPOSAL",
        conversion_intent_id=f"conversion_intent_{run_id}",
    )
    accepted = http_post(
        endpoint,
        submitted_payload,
        _headers(idempotency_key=idempotency_key),
    )
    with ThreadPoolExecutor(max_workers=2) as executor:
        concurrent_responses = [
            future.result()
            for future in (
                executor.submit(
                    http_post,
                    endpoint,
                    idea_conversion_payload(
                        intent_type="REVIEW_FOR_ADVISORY_PROPOSAL",
                        conversion_intent_id=f"conversion_intent_concurrent_{run_id}",
                    ),
                    _headers(idempotency_key=f"idea-intake-proof-concurrent-{run_id}"),
                ),
                executor.submit(
                    http_post,
                    endpoint,
                    idea_conversion_payload(
                        intent_type="REVIEW_FOR_ADVISORY_PROPOSAL",
                        conversion_intent_id=f"conversion_intent_concurrent_{run_id}",
                    ),
                    _headers(idempotency_key=f"idea-intake-proof-concurrent-{run_id}"),
                ),
            )
        ]
    concurrent = {
        body_get(response.get("body"), "intake_status"): response
        for response in concurrent_responses
    }
    accepted_body = accepted.get("body")
    intake_id = body_get(accepted_body, "intake_id")
    portfolio_id = body_get(accepted_body, "portfolio_id")
    calls = {
        "accepted": accepted,
        "acceptedReplay": http_post(
            endpoint,
            submitted_payload,
            _headers(idempotency_key=idempotency_key),
        ),
        "concurrentAccepted": concurrent.get("ACCEPTED", {}),
        "concurrentReplay": concurrent.get("ACCEPTED_REPLAYED", {}),
        "rejected": http_post(
            endpoint,
            idea_conversion_payload(
                intent_type="CREATE_ADVISORY_PROPOSAL_DRAFT",
                conversion_intent_id=f"conversion_intent_rejected_{run_id}",
            ),
            _headers(idempotency_key=f"idea-intake-proof-rejected-{run_id}"),
        ),
        "idempotencyConflict": http_post(
            endpoint,
            idea_conversion_payload(
                intent_type="REVIEW_FOR_ADVISORY_PROPOSAL",
                conversion_intent_id=f"conversion_intent_changed_{run_id}",
            ),
            _headers(idempotency_key=idempotency_key),
        ),
        "authorizationDenied": http_post(
            endpoint,
            submitted_payload,
            _headers(
                idempotency_key=f"idea-intake-proof-auth-denied-{run_id}",
                capabilities="advisory.proposals.read",
            ),
        ),
        "tenantScopedIdempotency": http_post(
            endpoint,
            submitted_payload,
            _headers(
                idempotency_key=idempotency_key,
                tenant_id="tenant-private-bank-hk",
                legal_entity_code="HKPB",
            ),
        ),
        "ownerRealization": http_get(
            f"{endpoint}/{intake_id}/realization",
            {
                **_headers(capabilities="advisory.idea_proposal_realization.read"),
                "X-Portfolio-Id": str(portfolio_id or ""),
                "X-Authorized-Portfolio-Id": str(portfolio_id or ""),
            },
        ),
        "submittedIntent": {
            "ideaCandidateId": submitted_payload["idea_candidate_id"],
            "conversionIntentId": submitted_payload["conversion_intent_id"],
            "portfolioId": submitted_payload["portfolio_id"],
            "tenantId": "tenant-private-bank-sg",
            "legalEntityCode": "SGPB",
        },
    }
    return source_safe_execution_evidence(calls)


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
