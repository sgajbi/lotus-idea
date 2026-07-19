# ruff: noqa: E402
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.deployment_migrations import (
    deployment_migration_evidence,
    run_deployment_migrations,
)
from app.application.deployment_migration_contract import (
    load_deployment_migration_contract,
)
from app.domain.deployment_migrations import (
    DeploymentEnvironmentClass,
    DeploymentMigrationCommand,
    DeploymentMigrationError,
    DeploymentMigrationOperation,
    MigrationReleaseIdentity,
)
from app.infrastructure.capacity_artifact_io import write_json_atomic
from app.infrastructure.postgres_deployment_migrations import (
    PostgresDeploymentMigrationExecutor,
)


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = ROOT / "migrations"
CONTRACT_PATH = ROOT / "contracts" / "operations" / "lotus-idea-deployment-migrations.v1.json"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run governed Lotus Idea deployment migrations from an immutable image."
    )
    parser.add_argument(
        "--operation",
        choices=[operation.value for operation in DeploymentMigrationOperation],
        default=DeploymentMigrationOperation.APPLY.value,
    )
    parser.add_argument(
        "--environment-class",
        choices=[value.value for value in DeploymentEnvironmentClass],
        required=True,
    )
    parser.add_argument("--rollback-count", type=int, default=0)
    parser.add_argument("--evidence-output", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    database_url = os.getenv("LOTUS_IDEA_DATABASE_URL", "").strip()
    if not database_url:
        print("deployment_migration_database_url_missing", file=sys.stderr)
        return 2
    try:
        contract = load_deployment_migration_contract(CONTRACT_PATH)
        operation = DeploymentMigrationOperation(args.operation)
        command = DeploymentMigrationCommand(
            operation=operation,
            release=_release_identity(args.environment_class),
            expected_migration_bundle_sha256=contract.migration_bundle_sha256,
            rollback_count=args.rollback_count,
            expected_schema_fingerprint=(
                contract.schema_fingerprint_sha256
                if operation is DeploymentMigrationOperation.ADOPT
                else None
            ),
        )
        import psycopg

        with psycopg.connect(database_url) as connection:
            result = run_deployment_migrations(
                command,
                executor=PostgresDeploymentMigrationExecutor(
                    connection,  # type: ignore[arg-type]
                    migrations_dir=MIGRATIONS_DIR,
                ),
            )
        write_json_atomic(args.evidence_output, deployment_migration_evidence(result))
    except (DeploymentMigrationError, ValueError) as exc:
        code = exc.code if isinstance(exc, DeploymentMigrationError) else "invalid_migration_input"
        print(code, file=sys.stderr)
        return 2
    except Exception:
        print("deployment_migration_execution_failed", file=sys.stderr)
        return 1
    print("Deployment migration execution passed")
    return 0


def _release_identity(environment_class: str) -> MigrationReleaseIdentity:
    return MigrationReleaseIdentity(
        repository=os.getenv("GITHUB_REPOSITORY", ""),
        git_commit_sha=os.getenv("GITHUB_SHA", ""),
        git_ref=os.getenv("GITHUB_REF", ""),
        ci_run_id=os.getenv("GITHUB_RUN_ID", ""),
        image_digest_reference=os.getenv("LOTUS_RELEASE_IMAGE_DIGEST_REFERENCE", ""),
        environment_class=DeploymentEnvironmentClass(environment_class),
        change_reference=os.getenv("LOTUS_DEPLOYMENT_CHANGE_REFERENCE", ""),
        deployment_actor=os.getenv("GITHUB_ACTOR", ""),
    )


if __name__ == "__main__":
    sys.exit(main())
