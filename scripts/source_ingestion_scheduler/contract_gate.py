from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import sys

from app.application.source_ingestion_scheduler import (
    CANONICAL_WORKER_MANIFEST_PATH,
    DOCKER_COMPOSE_WORKER_SERVICE,
    REQUIRED_SOURCE_PATHS,
    SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_SCHEMA_VERSION,
    SCHEDULED_WORKER_ENTRYPOINT,
    SCHEDULED_WORKER_SOURCE_CONTRACT_SCHEMA_VERSION,
    build_scheduled_worker_check_summary,
    build_scheduled_worker_deployment_evidence_payload,
    build_scheduled_worker_source_contract_payload,
    scheduled_worker_deployment_evidence_is_valid,
    scheduled_worker_deployment_matches_source_contract,
    scheduled_worker_source_contract_is_valid,
    source_ingestion_schedule_config_from_values,
)
from app.application.source_ingestion_worker import source_ingestion_worker_plan_from_manifest
from scripts.proof_source_safety import validate_forbidden_content


ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_MANIFEST_PATH = (
    ROOT / "docs" / "examples" / "source-ingestion" / "high-cash-worker-manifest.example.json"
)
RETIRED_PATHS = (
    "src/app/application/source_ingestion_scheduled_worker.py",
    "scripts/generate_scheduled_source_ingestion_worker_proof.py",
    "scripts/source_ingestion_scheduled_worker_contract_gate.py",
)
RETIRED_CONTRACT_TERMS = (
    "lotus-idea.source-ingestion.scheduled-worker-proof.v1",
    "LOTUS_IDEA_SOURCE_INGESTION_SCHEDULED_WORKER_PROOF",
    "--source-ingestion-scheduled-worker-proof",
)
FORBIDDEN_KEYS = {
    "accountId",
    "candidateId",
    "clientId",
    "correlationId",
    "idempotencyKey",
    "portfolioId",
    "requestBody",
    "responseBody",
    "sourcePayload",
    "traceId",
    "transactionId",
}
FORBIDDEN_TEXT = {
    "PB_SG_GLOBAL_BAL_001",
    "signal-ingestion:high-cash:lotus-core",
}


def validate_source_ingestion_scheduler_contracts() -> list[str]:
    errors: list[str] = []
    try:
        manifest = json.loads(EXAMPLE_MANIFEST_PATH.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError("example manifest must be an object")
        plan = source_ingestion_worker_plan_from_manifest(manifest)
        check_summary = build_scheduled_worker_check_summary(
            plan=plan,
            schedule=source_ingestion_schedule_config_from_values(
                interval_seconds=300,
                max_runs=1,
                run_forever=True,
            ),
        )
        source_contract = build_scheduled_worker_source_contract_payload(
            generated_at_utc=datetime(2026, 7, 16, 10, 10, tzinfo=UTC),
            check_summary=check_summary,
            repository_root=ROOT,
        )
        deployment_evidence = build_scheduled_worker_deployment_evidence_payload(
            generated_at_utc=datetime(2026, 7, 16, 10, 20, tzinfo=UTC),
            source_commit_sha="a" * 40,
            image_digest=f"sha256:{'b' * 64}",
            target_environment="integration-sg",
            environment_class="test",
            controller_workflow="deploy-integration",
            controller_run_id="29489107377",
            controller_run_attempt=1,
            deployment_actor="github-actions",
            workload_identity=DOCKER_COMPOSE_WORKER_SERVICE,
            rollout_completed_at_utc=datetime(2026, 7, 16, 10, 19, tzinfo=UTC),
            scheduler_configuration_digest=source_contract["schedulerConfigurationDigest"],
            source_contract_digest=source_contract["sourceContractDigest"],
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"cannot build scheduled-worker evidence contracts: {exc}"]

    if source_contract.get("schemaVersion") != SCHEDULED_WORKER_SOURCE_CONTRACT_SCHEMA_VERSION:
        errors.append("scheduled-worker source-contract schema drift")
    if not scheduled_worker_source_contract_is_valid(
        source_contract,
        repository_root=ROOT,
    ):
        errors.append("scheduled-worker source contract must validate against repository truth")
    if (
        deployment_evidence.get("schemaVersion")
        != SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_SCHEMA_VERSION
    ):
        errors.append("scheduled-worker deployment-evidence schema drift")
    if not scheduled_worker_deployment_evidence_is_valid(deployment_evidence):
        errors.append("scheduled-worker deployment evidence must validate")
    if not scheduled_worker_deployment_matches_source_contract(
        deployment_evidence,
        source_contract,
    ):
        errors.append("deployment evidence must bind the exact scheduler source contract")
    if deployment_evidence["blockerEffect"]["clears"] != ["scheduled_worker_deploy_proof_missing"]:
        errors.append("deployment evidence must clear only the deployment blocker")
    if source_contract["blockerEffect"]["clears"]:
        errors.append("source-contract evidence must clear no blocker")
    _validate_runtime_packaging(errors)
    _validate_retired_paths(errors)
    validate_forbidden_content(source_contract, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT)
    validate_forbidden_content(deployment_evidence, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT)
    return errors


def _validate_runtime_packaging(errors: list[str]) -> None:
    compose_text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    if (
        DOCKER_COMPOSE_WORKER_SERVICE not in compose_text
        or SCHEDULED_WORKER_ENTRYPOINT not in compose_text
    ):
        errors.append("docker-compose.yml must retain the scheduled-worker service")
    dockerfile_text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    for path in REQUIRED_SOURCE_PATHS:
        if path == "docker-compose.yml":
            continue
        if f"COPY {path} ./{path}" not in dockerfile_text:
            errors.append(f"Dockerfile must package scheduled-worker runtime file {path}")
    if CANONICAL_WORKER_MANIFEST_PATH not in REQUIRED_SOURCE_PATHS:
        errors.append("canonical worker manifest must remain source-contract evidence")


def _validate_retired_paths(errors: list[str]) -> None:
    for retired_path in RETIRED_PATHS:
        if (ROOT / retired_path).exists():
            errors.append(f"retired scheduled-worker v1 path must not exist: {retired_path}")
    for root in ("src", "scripts"):
        for file_path in (ROOT / root).rglob("*"):
            if not file_path.is_file() or file_path.suffix not in {".py", ".json", ".md"}:
                continue
            if file_path.resolve() == Path(__file__).resolve():
                continue
            text = file_path.read_text(encoding="utf-8")
            for term in RETIRED_CONTRACT_TERMS:
                if term in text:
                    errors.append(
                        f"{file_path.relative_to(ROOT).as_posix()}: retired term `{term}`"
                    )


def main() -> int:
    errors = validate_source_ingestion_scheduler_contracts()
    if errors:
        print("\n".join(errors))
        return 1
    print("Source ingestion scheduler contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
