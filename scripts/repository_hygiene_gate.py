from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

PROHIBITED_EXACT_PATHS = {
    ".coverage",
    ".env",
    "coverage.xml",
}

PROHIBITED_PATH_PARTS = {
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
    "node_modules",
}

PROHIBITED_SUFFIXES = {
    ".db",
    ".egg-info",
    ".log",
    ".pyc",
    ".pyo",
}

REQUIRED_BOUNDED_MODULE_PATHS = {
    "src/app/domain/review_queue/__init__.py",
    "src/app/domain/review_queue/policy.py",
    "src/app/domain/review_queue/snapshot.py",
    "src/app/infrastructure/persistence/__init__.py",
    "src/app/infrastructure/persistence/aggregate_mutation.py",
    "src/app/infrastructure/persistence/postgres_mutation.py",
    "src/app/infrastructure/persistence/postgres_replay.py",
    "tests/integration/persistence/__init__.py",
    "tests/integration/persistence/test_candidate_persistence_runtime.py",
    "tests/unit/persistence/__init__.py",
    "tests/unit/persistence/test_aggregate_mutation.py",
    "scripts/outbox/__init__.py",
    "scripts/outbox/_bootstrap.py",
    "scripts/outbox/broker_proof_contract_gate.py",
    "scripts/outbox/consumer_contract_gate.py",
    "scripts/outbox/consumer_runtime_proof_contract_gate.py",
    "scripts/outbox/event_contract_gate.py",
    "scripts/outbox/generate_broker_proof.py",
    "scripts/outbox/generate_consumer_runtime_proof.py",
    "scripts/outbox/generate_platform_mesh_event_publication_proof.py",
    "scripts/outbox/platform_mesh_event_publication_proof_contract_gate.py",
    "scripts/outbox/recovery_contract_gate.py",
    "scripts/outbox/supportability_contract_gate.py",
    "src/app/api/outbox/__init__.py",
    "src/app/api/outbox/delivery.py",
    "src/app/api/outbox/delivery_models.py",
    "src/app/api/outbox/recovery.py",
    "src/app/api/outbox/recovery_models.py",
    "src/app/application/outbox/__init__.py",
    "src/app/application/outbox/broker_proof.py",
    "src/app/application/outbox/consumer_runtime_proof.py",
    "src/app/application/outbox/delivery.py",
    "src/app/application/outbox/platform_mesh_event_publication_proof.py",
    "src/app/application/outbox/readiness.py",
    "src/app/application/outbox/recovery.py",
    "src/app/application/outbox/supportability_alerts.py",
    "src/app/domain/outbox/__init__.py",
    "src/app/domain/outbox/delivery.py",
    "src/app/domain/outbox/events.py",
    "src/app/domain/outbox/persistence.py",
    "src/app/domain/outbox/recovery.py",
    "src/app/infrastructure/outbox/__init__.py",
    "src/app/infrastructure/outbox/postgres_delivery.py",
    "src/app/infrastructure/outbox/postgres_recovery.py",
    "src/app/infrastructure/outbox/postgres_repository.py",
    "src/app/infrastructure/outbox/postgres_writes.py",
    "src/app/infrastructure/outbox/publisher.py",
    "src/app/observability/outbox/__init__.py",
    "src/app/observability/outbox/supportability.py",
    "src/app/ports/outbox/__init__.py",
    "src/app/ports/outbox/publisher.py",
    "src/app/runtime/outbox/__init__.py",
    "src/app/runtime/outbox/publisher_state.py",
    "tests/integration/outbox/test_delivery_readiness_api.py",
    "tests/integration/outbox/test_event_lineage_api.py",
    "tests/integration/outbox/test_postgres_recovery_runtime.py",
    "tests/integration/outbox/test_recovery_api.py",
    "tests/unit/outbox/postgres_fake_helpers.py",
    "tests/unit/outbox/test_outbox_delivery.py",
    "tests/unit/outbox/test_outbox_recovery.py",
    "tests/unit/outbox/test_outbox_publisher_adapter.py",
    "tests/unit/outbox/test_postgres_delivery_adapter.py",
    "scripts/data_lifecycle/__init__.py",
    "scripts/data_lifecycle/run_scheduled_review.py",
    "scripts/data_lifecycle/scheduled_review_proof_gate.py",
    "scripts/data_lifecycle/seed_scheduled_review_fixture.py",
    "src/app/api/data_lifecycle/__init__.py",
    "src/app/api/data_lifecycle/models.py",
    "src/app/application/data_lifecycle/__init__.py",
    "src/app/application/data_lifecycle/authority_verification.py",
    "src/app/domain/data_lifecycle/__init__.py",
    "src/app/domain/data_lifecycle/authority.py",
    "src/app/domain/data_lifecycle/schedule.py",
    "src/app/infrastructure/data_lifecycle/__init__.py",
    "src/app/infrastructure/data_lifecycle/authority_key_source.py",
    "src/app/infrastructure/data_lifecycle/postgres_policy.py",
    "src/app/infrastructure/data_lifecycle/postgres_redaction.py",
    "src/app/infrastructure/data_lifecycle/postgres_schedule.py",
    "src/app/integration/data_lifecycle/__init__.py",
    "src/app/integration/data_lifecycle/authority_contract.py",
    "src/app/ports/data_lifecycle/__init__.py",
    "src/app/ports/data_lifecycle/authority.py",
    "src/app/runtime/data_lifecycle/__init__.py",
    "src/app/runtime/data_lifecycle/authority_state.py",
    "tests/unit/data_lifecycle/test_authority_verification.py",
    "tests/unit/data_lifecycle/test_policy.py",
    "tests/unit/data_lifecycle/test_schedule.py",
}

PROHIBITED_LEGACY_MODULE_PATHS = {
    "src/app/domain/review_queue_snapshot.py",
    "scripts/generate_outbox_broker_proof.py",
    "scripts/generate_outbox_consumer_runtime_proof.py",
    "scripts/generate_outbox_platform_mesh_event_publication_proof.py",
    "scripts/outbox_broker_proof_contract_gate.py",
    "scripts/outbox_consumer_contract_gate.py",
    "scripts/outbox_consumer_runtime_proof_contract_gate.py",
    "scripts/outbox_event_contract_gate.py",
    "scripts/outbox_platform_mesh_event_publication_proof_contract_gate.py",
    "scripts/outbox_recovery_contract_gate.py",
    "scripts/outbox_supportability_contract_gate.py",
    "src/app/api/outbox_delivery_readiness.py",
    "src/app/api/outbox_delivery_readiness_models.py",
    "src/app/api/outbox_recovery.py",
    "src/app/api/outbox_recovery_models.py",
    "src/app/application/outbox_broker_proof.py",
    "src/app/application/outbox_consumer_runtime_proof.py",
    "src/app/application/outbox_delivery.py",
    "src/app/application/outbox_delivery_readiness.py",
    "src/app/application/outbox_platform_mesh_event_publication_proof.py",
    "src/app/application/outbox_recovery.py",
    "src/app/application/outbox_supportability_alerts.py",
    "src/app/domain/events.py",
    "src/app/domain/outbox_delivery_state.py",
    "src/app/domain/outbox_recovery.py",
    "src/app/domain/persistence_outbox.py",
    "src/app/infrastructure/outbox_publisher.py",
    "src/app/infrastructure/postgres_outbox_delivery.py",
    "src/app/infrastructure/postgres_outbox_recovery.py",
    "src/app/infrastructure/postgres_outbox_repository.py",
    "src/app/infrastructure/postgres_outbox_writes.py",
    "src/app/observability/outbox_supportability.py",
    "src/app/ports/outbox_publisher.py",
    "src/app/runtime/outbox_publisher_state.py",
    "tests/integration/test_outbox_delivery_readiness_api.py",
    "tests/integration/test_outbox_event_lineage_api.py",
    "tests/integration/test_outbox_recovery_api.py",
    "tests/integration/test_postgres_outbox_recovery_runtime.py",
    "tests/unit/test_outbox_broker_proof.py",
    "tests/unit/test_outbox_consumer_contract_gate.py",
    "tests/unit/test_outbox_consumer_runtime_proof.py",
    "tests/unit/test_outbox_delivery.py",
    "tests/unit/test_outbox_delivery_readiness.py",
    "tests/unit/test_outbox_event_contract_gate.py",
    "tests/unit/test_outbox_persistence.py",
    "tests/unit/test_outbox_platform_mesh_event_publication_proof.py",
    "tests/unit/test_outbox_publisher_adapter.py",
    "tests/unit/test_outbox_recovery.py",
    "tests/unit/test_outbox_recovery_application.py",
    "tests/unit/test_outbox_recovery_contract_gate.py",
    "tests/unit/test_outbox_supportability_alerts.py",
    "tests/unit/test_outbox_supportability_contract_gate.py",
    "tests/unit/test_outbox_supportability_metrics.py",
    "tests/unit/postgres_outbox_fake_helpers.py",
    "tests/unit/test_postgres_outbox_delivery_adapter.py",
    "tests/unit/test_postgres_outbox_readiness.py",
    "scripts/run_scheduled_data_lifecycle_review.py",
    "scripts/scheduled_data_lifecycle_review_proof_gate.py",
    "scripts/seed_scheduled_data_lifecycle_fixture.py",
    "src/app/api/data_lifecycle.py",
    "src/app/api/data_lifecycle_models.py",
    "src/app/application/data_lifecycle.py",
    "src/app/application/lifecycle_authority_verification.py",
    "src/app/domain/data_lifecycle.py",
    "src/app/domain/data_lifecycle_schedule.py",
    "src/app/domain/lifecycle_authority.py",
    "src/app/infrastructure/http_lifecycle_authority_keys.py",
    "src/app/infrastructure/postgres_data_lifecycle.py",
    "src/app/infrastructure/postgres_data_lifecycle_redaction.py",
    "src/app/infrastructure/postgres_data_lifecycle_schedule.py",
    "src/app/integration/lifecycle_authority_contract.py",
    "src/app/ports/data_lifecycle.py",
    "src/app/ports/lifecycle_authority.py",
    "src/app/runtime/lifecycle_authority_state.py",
    "tests/unit/test_data_lifecycle.py",
    "tests/unit/test_data_lifecycle_schedule.py",
    "tests/unit/test_lifecycle_authority_verification.py",
}

EXECUTABLE_PATH_PREFIXES = (
    ".github/workflows/",
    "migrations/",
    "scripts/",
    "src/",
    "tests/",
)
RFC_COUPLED_EXECUTABLE_NAME = re.compile(r"(^|[/_-])(rfc|slice)[-_]?\d", re.IGNORECASE)
RFC_TRACKING_EXECUTABLE_PATHS: frozenset[str] = frozenset()


def _tracked_paths() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=False,
    )
    return [path.decode("utf-8") for path in result.stdout.split(b"\0") if path]


def _normalise(path: str) -> str:
    return path.replace("\\", "/").strip("/")


def find_repository_hygiene_violations(tracked_paths: list[str]) -> list[str]:
    violations: list[str] = []
    for tracked_path in tracked_paths:
        normalised = _normalise(tracked_path)
        parts = set(normalised.split("/"))
        suffixes = Path(normalised).suffixes

        if normalised in PROHIBITED_EXACT_PATHS:
            violations.append(f"{normalised}: generated or local-only artifact must not be tracked")
            continue
        if parts & PROHIBITED_PATH_PARTS:
            violations.append(
                f"{normalised}: generated or dependency directory content must not be tracked"
            )
            continue
        if any(suffix in PROHIBITED_SUFFIXES for suffix in suffixes):
            violations.append(
                f"{normalised}: generated or local-only file type must not be tracked"
            )

    return sorted(violations)


def find_bounded_module_placement_violations(tracked_paths: list[str]) -> list[str]:
    normalised_paths = {_normalise(path) for path in tracked_paths}
    violations = [
        f"{path}: required bounded-module path is missing"
        for path in REQUIRED_BOUNDED_MODULE_PATHS - normalised_paths
    ]
    violations.extend(
        f"{path}: legacy flat-module path must not be reintroduced"
        for path in PROHIBITED_LEGACY_MODULE_PATHS & normalised_paths
    )
    return sorted(violations)


def find_executable_naming_violations(
    tracked_paths: list[str],
    *,
    rfc_tracking_paths: frozenset[str] = RFC_TRACKING_EXECUTABLE_PATHS,
) -> list[str]:
    return sorted(
        f"{path}: executable artifact must be named for its capability, not an RFC or slice"
        for tracked_path in tracked_paths
        if (path := _normalise(tracked_path)).startswith(EXECUTABLE_PATH_PREFIXES)
        and path not in rfc_tracking_paths
        and RFC_COUPLED_EXECUTABLE_NAME.search(path)
    )


def main() -> int:
    tracked_paths = _tracked_paths()
    violations = [
        *find_repository_hygiene_violations(tracked_paths),
        *find_bounded_module_placement_violations(tracked_paths),
        *find_executable_naming_violations(tracked_paths),
    ]
    if violations:
        print("Repository hygiene gate failed:")
        print("\n".join(violations))
        return 1

    print("Repository hygiene gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
