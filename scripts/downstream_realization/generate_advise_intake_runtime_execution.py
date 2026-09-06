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

from app.application.downstream_realization.advise_intake_runtime_execution import (  # noqa: E402
    build_advise_intake_runtime_execution_payload,
)
from scripts.downstream_realization.advise_postgres_restart_evidence import (  # noqa: E402
    execute_advise_postgres_restart_tests,
    execute_idea_postgres_reconciliation_test,
)
from scripts.downstream_realization.advise_runtime_evidence_projection import (  # noqa: E402
    source_safe_execution_evidence,
)

try:
    from scripts.proof_generator_io import parse_generated_at_utc, write_json_payload
except ImportError:  # pragma: no cover - supports direct script execution
    from proof_generator_io import (  # type: ignore[import-not-found,no-redef]
        parse_generated_at_utc,
        write_json_payload,
    )


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        generated_at_utc = parse_generated_at_utc(args.generated_at_utc)
        execution_evidence = _execute_advise_testclient(
            advise_root=Path(args.advise_root),
            advise_python=args.advise_python,
        )
        owner_restart_evidence = execute_advise_postgres_restart_tests(
            advise_root=Path(args.advise_root),
            advise_python=args.advise_python,
            postgres_dsn=args.advise_postgres_dsn,
            allow_database_reset=args.allow_destructive_test_database_reset,
        )
        idea_reconciliation_evidence = execute_idea_postgres_reconciliation_test(
            repository_root=Path.cwd(),
            idea_python=sys.executable,
            postgres_dsn=args.idea_postgres_dsn,
            allow_database_reset=args.allow_destructive_test_database_reset,
        )
        payload = build_advise_intake_runtime_execution_payload(
            generated_at_utc=generated_at_utc,
            repository_root=Path.cwd(),
            advise_root=Path(args.advise_root),
            runtime_mode=args.runtime_mode,
            receipt_evidence={
                name: evidence
                for name, evidence in execution_evidence.items()
                if name
                not in {
                    "ownerRealization",
                    "ownerAdvancement",
                    "submittedIntent",
                    "preCommitTimeout",
                }
            },
            submitted_intent_evidence=execution_evidence["submittedIntent"],
            owner_realization_evidence=execution_evidence["ownerRealization"],
            owner_advancement_evidence=execution_evidence["ownerAdvancement"],
            owner_restart_evidence=owner_restart_evidence,
            idea_reconciliation_evidence=idea_reconciliation_evidence,
            pre_commit_timeout_evidence=execution_evidence["preCommitTimeout"],
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
        choices=("local_asgi_testclient",),
        default="local_asgi_testclient",
    )
    parser.add_argument("--advise-python", default=sys.executable)
    parser.add_argument(
        "--advise-postgres-dsn",
        default=os.getenv("PROPOSAL_POSTGRES_INTEGRATION_DSN", "").strip(),
        help="Disposable, migrated Advise PostgreSQL test database; never retained in evidence.",
    )
    parser.add_argument(
        "--idea-postgres-dsn",
        default=os.getenv("LOTUS_IDEA_POSTGRES_INTEGRATION_URL", "").strip(),
        help="Disposable, migrated Idea PostgreSQL test database; never retained in evidence.",
    )
    parser.add_argument(
        "--allow-destructive-test-database-reset",
        action="store_true",
        help="Required because the owner integration tests reset their dedicated database.",
    )
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
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from uuid import uuid4
import src.api.proposals.router as proposals_router
import src.runtime.proposal_repositories as proposal_repositories
from src.api.main import app
from src.core.proposals.persistence_models import ProposalRecord
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository
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
    return (
        r"""

owner_repository = InMemoryProposalRepository()
proposal_repositories.PostgresProposalRepository = lambda **_kwargs: owner_repository
proposals_router.reset_proposal_workflow_service_for_tests()
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
"""
        + _advise_owner_advancement_scenario_script()
        + _advise_precommit_timeout_scenario_script()
        + _advise_testclient_result_script()
    )


def _advise_testclient_result_script() -> str:
    return r"""

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
    "ownerAdvancement": {
        "linked": response_payload(owner_linked),
        "staleCorrection": response_payload(stale_owner_correction),
        "afterStaleCorrection": response_payload(owner_after_stale_correction),
        "concurrentAdvancement": [
            response_payload(response) for response in concurrent_owner_advancement
        ],
        "finalReadback": response_payload(owner_after_advancement),
    },
    "submittedIntent": {
        "ideaCandidateId": "idea_candidate_001",
        "conversionIntentId": f"conversion_intent_{RUN_ID}",
        "portfolioId": "PB_SG_GLOBAL_BAL_001",
        "tenantId": "tenant-private-bank-sg",
        "legalEntityCode": "SGPB",
    },
    "preCommitTimeout": {
        "failureStage": "before_owner_request_dispatch",
        "downstreamPostAttemptCount": 0,
        "automaticResubmissionAttemptCount": 0,
        "ownerStateObserved": False,
        "ideaCandidateId": "idea_candidate_precommit_timeout_001",
        "conversionIntentId": precommit_conversion_intent_id,
        "portfolioId": "PB_SG_GLOBAL_BAL_001",
        "tenantId": "tenant-private-bank-sg",
        "legalEntityCode": "SGPB",
        "ownerLookup": response_payload(precommit_owner_lookup),
        "repeatedOwnerLookup": response_payload(precommit_owner_lookup_replay),
    },
}, sort_keys=True))
"""


def _advise_owner_advancement_scenario_script() -> str:
    return r"""
proposal_id = f"pp_idea_runtime_{RUN_ID}"
proposal_created_at = datetime.now(timezone.utc)
owner_repository.create_proposal(ProposalRecord(
    proposal_id=proposal_id,
    portfolio_id="PB_SG_GLOBAL_BAL_001",
    created_by="advisor-runtime-proof",
    created_at=proposal_created_at,
    last_event_at=proposal_created_at,
    current_state="DRAFT",
    current_version_no=1,
))
owner_reconciliation_route = (
    f"{ROUTE}/{accepted.json()['intake_id']}/realization/proposal-reconciliation"
)
owner_reconciliation_headers = {
    **headers(capabilities="advisory.idea_proposal_realization.write"),
    "X-Portfolio-Id": accepted.json()["portfolio_id"],
    "X-Authorized-Portfolio-Id": accepted.json()["portfolio_id"],
}
owner_linked = client.post(
    owner_reconciliation_route,
    json={"proposal_id": proposal_id, "expected_source_event_version": 1},
    headers=owner_reconciliation_headers,
)
owner_repository.update_proposal(
    owner_repository.get_proposal(proposal_id=proposal_id).model_copy(update={
        "current_state": "REJECTED",
        "last_event_at": datetime.now(timezone.utc),
    })
)
stale_owner_correction = client.post(
    owner_reconciliation_route,
    json={"proposal_id": proposal_id, "expected_source_event_version": 1},
    headers=owner_reconciliation_headers,
)
owner_after_stale_correction = client.get(
    f"{ROUTE}/{accepted.json()['intake_id']}/realization",
    headers={
        **headers(capabilities="advisory.idea_proposal_realization.read"),
        "X-Portfolio-Id": accepted.json()["portfolio_id"],
        "X-Authorized-Portfolio-Id": accepted.json()["portfolio_id"],
    },
)
with ThreadPoolExecutor(max_workers=2) as executor:
    concurrent_owner_advancement = [
        future.result()
        for future in (
            executor.submit(
                client.post,
                owner_reconciliation_route,
                json={"proposal_id": proposal_id, "expected_source_event_version": 2},
                headers=owner_reconciliation_headers,
            ),
            executor.submit(
                client.post,
                owner_reconciliation_route,
                json={"proposal_id": proposal_id, "expected_source_event_version": 2},
                headers=owner_reconciliation_headers,
            ),
        )
    ]
owner_after_advancement = client.get(
    f"{ROUTE}/{accepted.json()['intake_id']}/realization",
    headers={
        **headers(capabilities="advisory.idea_proposal_realization.read"),
        "X-Portfolio-Id": accepted.json()["portfolio_id"],
        "X-Authorized-Portfolio-Id": accepted.json()["portfolio_id"],
    },
)
"""


def _advise_precommit_timeout_scenario_script() -> str:
    return r"""
precommit_conversion_intent_id = f"conversion_intent_precommit_timeout_{RUN_ID}"
precommit_lookup_headers = {
    **headers(capabilities="advisory.idea_proposal_realization.read"),
    "X-Portfolio-Id": "PB_SG_GLOBAL_BAL_001",
    "X-Authorized-Portfolio-Id": "PB_SG_GLOBAL_BAL_001",
}
precommit_owner_lookup = client.get(
    f"{ROUTE}/realization",
    params={"conversion_intent_id": precommit_conversion_intent_id},
    headers=precommit_lookup_headers,
)
precommit_owner_lookup_replay = client.get(
    f"{ROUTE}/realization",
    params={"conversion_intent_id": precommit_conversion_intent_id},
    headers=precommit_lookup_headers,
)
"""


def _advise_testclient_env(advise_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(advise_root.resolve())
    env.setdefault("ENVIRONMENT", "test")
    env.setdefault("IDEA_PROPOSAL_RECONCILIATION_ENABLED", "true")
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


if __name__ == "__main__":
    sys.exit(main())
