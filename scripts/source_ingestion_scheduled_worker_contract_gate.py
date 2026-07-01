from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.application.source_ingestion_scheduled_worker import (
    DOCKER_COMPOSE_WORKER_SERVICE,
    RUN_ONCE_WORKER_ENTRYPOINT,
    SCHEDULED_WORKER_ENTRYPOINT,
    SCHEDULED_WORKER_PROOF_SCHEMA_VERSION,
    SCHEDULED_WORKER_SCHEMA_VERSION,
    build_scheduled_worker_check_summary,
    build_scheduled_worker_deploy_proof_payload,
    scheduled_worker_deploy_proof_is_valid,
    source_ingestion_schedule_config_from_values,
)
from app.application.source_ingestion_worker import source_ingestion_worker_plan_from_manifest


try:
    from scripts.proof_source_safety import forbidden_content_validator, validate_forbidden_content
except ModuleNotFoundError:
    from proof_source_safety import forbidden_content_validator, validate_forbidden_content  # type: ignore[import-not-found,no-redef]

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_MANIFEST_PATH = (
    ROOT / "docs" / "examples" / "source-ingestion" / "high-cash-worker-manifest.example.json"
)

FORBIDDEN_KEYS = {
    "accountId",
    "candidateId",
    "clientId",
    "correlationId",
    "duplicateOfCandidateId",
    "holdingId",
    "idempotencyKey",
    "portfolioId",
    "requestBody",
    "responseBody",
    "sourcePayload",
    "sourceRoute",
    "traceId",
    "transactionId",
}

FORBIDDEN_TEXT_FRAGMENTS = {
    "/source/",
    "PB_SG_GLOBAL_BAL_001",
    "request-body",
    "response-body",
    "signal-ingestion:high-cash:lotus-core",
}


_validate_forbidden_content = forbidden_content_validator(
    FORBIDDEN_KEYS,
    FORBIDDEN_TEXT_FRAGMENTS,
)


def validate_source_ingestion_scheduled_worker_contract() -> list[str]:
    errors: list[str] = []
    try:
        manifest = _read_manifest(EXAMPLE_MANIFEST_PATH)
        plan = source_ingestion_worker_plan_from_manifest(manifest)
        schedule = source_ingestion_schedule_config_from_values(
            interval_seconds=300,
            max_runs=1,
        )
        check_summary = build_scheduled_worker_check_summary(plan=plan, schedule=schedule)
        proof = build_scheduled_worker_deploy_proof_payload(
            generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
            check_summary=check_summary,
            scheduler_entrypoint_present=(ROOT / SCHEDULED_WORKER_ENTRYPOINT).is_file(),
            run_once_worker_entrypoint_present=(ROOT / RUN_ONCE_WORKER_ENTRYPOINT).is_file(),
            docker_compose_service_present=_docker_compose_service_present(),
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"cannot build scheduled worker proof: {exc}"]

    if check_summary.get("schemaVersion") != SCHEDULED_WORKER_SCHEMA_VERSION:
        errors.append(f"scheduled check summary schema must be {SCHEDULED_WORKER_SCHEMA_VERSION}")
    if proof.get("schemaVersion") != SCHEDULED_WORKER_PROOF_SCHEMA_VERSION:
        errors.append(f"scheduled proof schema must be {SCHEDULED_WORKER_PROOF_SCHEMA_VERSION}")
    if not scheduled_worker_deploy_proof_is_valid(proof):
        errors.append("scheduled worker deploy proof must validate against its contract")
    if not _docker_compose_service_present():
        errors.append(
            f"docker-compose.yml must define {DOCKER_COMPOSE_WORKER_SERVICE} using "
            f"{SCHEDULED_WORKER_ENTRYPOINT}"
        )

    validate_forbidden_content(check_summary, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    validate_forbidden_content(proof, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


def _docker_compose_service_present() -> bool:
    try:
        compose_text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    except OSError:
        return False
    return (
        DOCKER_COMPOSE_WORKER_SERVICE in compose_text
        and SCHEDULED_WORKER_ENTRYPOINT in compose_text
    )


def _read_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("manifest must be a JSON object")
    return payload


def main() -> int:
    errors = validate_source_ingestion_scheduled_worker_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Source ingestion scheduled worker contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
