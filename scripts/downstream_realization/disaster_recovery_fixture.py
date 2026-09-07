# ruff: noqa: E402
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.domain import (
    ConversionTarget,
    DownstreamSubmissionPosture,
    DownstreamSubmissionResourceType,
    SourceSystem,
    create_downstream_submission_claim,
)
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from scripts.downstream_realization.advise_recovery_fixture import (
    seed_advise_realization_recovery_fixture,
)
from scripts.downstream_realization.manage_recovery_fixture import (
    seed_manage_realization_recovery_fixture,
)


def seed_downstream_recovery_fixtures(
    repository: PostgresIdeaRepository,
    *,
    fixture_time: datetime,
    candidate_prefix: str,
) -> None:
    conversion_claim = create_downstream_submission_claim(
        tenant_id="tenant-private-bank-sg",
        idempotency_key="dr-fixture-downstream-conversion",
        request_fingerprint="sha256:dr-fixture-downstream-conversion",
        resource_type=DownstreamSubmissionResourceType.CONVERSION_INTENT,
        resource_id="dr-fixture-conversion-intent-001",
        target=ConversionTarget.REPORT_EVIDENCE,
        source_authority=SourceSystem.LOTUS_REPORT,
        actor_subject="dr-fixture-realization-worker",
        claimed_at_utc=fixture_time + timedelta(minutes=12),
        lease_owner="dr-fixture-realization-worker",
        lease_attempt_id="dr-fixture-downstream-attempt-001",
        lease_expires_at_utc=fixture_time + timedelta(minutes=17),
        correlation_id="corr-dr-fixture-downstream-001",
        trace_id="trace-dr-fixture-downstream-001",
    )
    repository.claim_downstream_submission(conversion_claim)
    report_claim = create_downstream_submission_claim(
        tenant_id="tenant-private-bank-sg",
        idempotency_key="dr-fixture-downstream-report",
        request_fingerprint="sha256:dr-fixture-downstream-report",
        resource_type=DownstreamSubmissionResourceType.REPORT_EVIDENCE_PACK,
        resource_id="dr-fixture-report-pack-001",
        target=ConversionTarget.REPORT_EVIDENCE,
        source_authority=SourceSystem.LOTUS_REPORT,
        actor_subject="dr-fixture-realization-worker",
        claimed_at_utc=fixture_time + timedelta(minutes=13),
        lease_owner="dr-fixture-realization-worker",
        lease_attempt_id="dr-fixture-downstream-attempt-002",
        lease_expires_at_utc=fixture_time + timedelta(minutes=18),
        correlation_id="corr-dr-fixture-downstream-002",
        trace_id="trace-dr-fixture-downstream-002",
    )
    repository.claim_downstream_submission(report_claim)
    repository.finalize_downstream_submission(
        tenant_id=report_claim.tenant_id,
        idempotency_key=report_claim.idempotency_key,
        lease_owner=report_claim.lease_owner or "",
        lease_attempt_id=report_claim.lease_attempt_id or "",
        posture=DownstreamSubmissionPosture.RECONCILIATION_REQUIRED,
        finalized_at_utc=fixture_time + timedelta(minutes=14),
        failure_reason="dr_fixture_commit_outcome_unknown",
    )
    seed_advise_realization_recovery_fixture(
        repository,
        fixture_time=fixture_time,
        candidate_id=f"{candidate_prefix}_conversion",
        conversion_intent_id="dr-fixture-conversion-intent-001",
        portfolio_id="portfolio-dr-fixture-conversion",
    )
    seed_manage_realization_recovery_fixture(
        repository,
        fixture_time=fixture_time,
        candidate_id=f"{candidate_prefix}_conversion",
        conversion_intent_id="dr-fixture-conversion-intent-001",
        portfolio_id="portfolio-dr-fixture-conversion",
    )


__all__ = ["seed_downstream_recovery_fixtures"]
