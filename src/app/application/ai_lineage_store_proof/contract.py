from __future__ import annotations

from app.domain.proof_evidence import EvidenceClass


AI_LINEAGE_STORE_PROOF_ENV = "LOTUS_IDEA_AI_LINEAGE_STORE_PROOF"
AI_LINEAGE_STORE_PROOF_SCHEMA_VERSION = "lotus-idea.ai-lineage-store-proof.v2"
AI_LINEAGE_STORE_REQUIRED_EVIDENCE_CLASS = EvidenceClass.CI_EXECUTION

REQUIRED_AI_LINEAGE_STORE_EVIDENCE_REFS = (
    "migrations/002_ai_explanation_lineage.sql",
    "migrations/002_ai_explanation_lineage.rollback.sql",
    "src/app/application/ai_governance.py",
    "src/app/domain/ai_lineage_persistence.py",
    "src/app/infrastructure/postgres_repository.py",
    "src/app/infrastructure/postgres_snapshot_writes.py",
    "tests/integration/test_postgres_runtime_integration.py",
    "make postgres-integration-gate",
    "Main Releasability / PostgreSQL Runtime Proof",
)

REQUIRED_AI_LINEAGE_STORE_ASSERTIONS = (
    "ai_lineage_schema_applied",
    "ai_lineage_write_accepted",
    "ai_lineage_reload_replay_verified",
    "ai_lineage_conflict_rejected",
    "ai_lineage_source_safety_verified",
)

REMAINING_AI_LINEAGE_STORE_CERTIFICATION_BLOCKERS = (
    "lotus_ai_live_provider_execution_missing",
    "certified_runtime_trust_telemetry_missing",
    "workbench_product_proof_missing",
    "supported_feature_promotion_missing",
)

TRUSTED_AI_LINEAGE_STORE_CI_REPOSITORY = "sgajbi/lotus-idea"
TRUSTED_AI_LINEAGE_STORE_CI_WORKFLOW_PATH = ".github/workflows/main-releasability.yml"
TRUSTED_AI_LINEAGE_STORE_CI_WORKFLOW_NAME = "Main Releasability Gate"
TRUSTED_AI_LINEAGE_STORE_CI_JOB_NAME = "Main Releasability / PostgreSQL Runtime Proof"
TRUSTED_AI_LINEAGE_STORE_CI_SOURCE_REF = "refs/heads/main"
TRUSTED_AI_LINEAGE_STORE_ARTIFACT_NAME = "postgres-runtime-proof-evidence"
