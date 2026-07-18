from __future__ import annotations

from app.domain.proof_evidence import EvidenceClass


DURABLE_REPOSITORY_PROOF_ENV = "LOTUS_IDEA_DURABLE_REPOSITORY_PROOF"
DURABLE_REPOSITORY_PROOF_SCHEMA_VERSION = "lotus-idea.durable-repository-proof.v2"
DURABLE_REPOSITORY_REQUIRED_EVIDENCE_CLASS = EvidenceClass.CI_EXECUTION

DURABLE_REPOSITORY_BLOCKERS_CLEARED = (
    "durable_repository_not_configured",
    "repository_side_queue_pagination_not_certified",
)

REQUIRED_DURABLE_REPOSITORY_EVIDENCE_REFS = (
    "migrations/001_idea_repository_foundation.sql",
    "migrations/001_idea_repository_foundation.rollback.sql",
    "src/app/infrastructure/postgres_repository.py",
    "src/app/infrastructure/postgres_snapshot_writes.py",
    "src/app/infrastructure/postgres_review_queue.py",
    "src/app/infrastructure/postgres_codecs.py",
    "src/app/runtime/repository_state.py",
    "tests/integration/test_postgres_runtime_integration.py",
    "tests/integration/persistence/test_candidate_persistence_runtime.py",
    "tests/integration/test_postgres_review_queue_runtime.py",
    "make migration-contract-gate",
    "make migration-execution-gate",
    "make postgres-integration-gate",
    "Main Releasability / PostgreSQL Runtime Proof",
)

REQUIRED_DURABLE_REPOSITORY_ASSERTIONS = (
    "schema_migration_rollback_reapply_verified",
    "candidate_persistence_reload_verified",
    "idempotent_replay_verified",
    "candidate_identity_audit_outbox_concurrency_verified",
    "repository_side_review_queue_pagination_verified",
)

REMAINING_DURABLE_REPOSITORY_CERTIFICATION_BLOCKERS = (
    "production_migration_deploy_evidence_missing",
    "live_core_source_proof_missing",
    "data_mesh_runtime_telemetry_not_certified",
    "gateway_workbench_proof_missing",
    "supported_feature_promotion_missing",
)

TRUSTED_DURABLE_REPOSITORY_CI_REPOSITORY = "sgajbi/lotus-idea"
TRUSTED_DURABLE_REPOSITORY_CI_WORKFLOW_PATH = ".github/workflows/main-releasability.yml"
TRUSTED_DURABLE_REPOSITORY_CI_WORKFLOW_NAME = "Main Releasability Gate"
TRUSTED_DURABLE_REPOSITORY_CI_JOB_NAME = "Main Releasability / PostgreSQL Runtime Proof"
TRUSTED_DURABLE_REPOSITORY_CI_SOURCE_REF = "refs/heads/main"
TRUSTED_DURABLE_REPOSITORY_ARTIFACT_NAME = "postgres-runtime-proof-evidence"
