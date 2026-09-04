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
    DownstreamSubmissionOwnerReceipt,
    DownstreamSubmissionPosture,
    DownstreamSubmissionResourceType,
    ManageActionRealizationEvent,
    ManageActionRealizationEventType,
    ManageActionRealizationHistory,
    ManageActionRealizationStatus,
    SourceSystem,
    create_downstream_submission_claim,
)
from app.infrastructure.postgres_repository import PostgresIdeaRepository


def seed_manage_realization_recovery_fixture(
    repository: PostgresIdeaRepository,
    *,
    fixture_time: datetime,
    candidate_id: str,
    conversion_intent_id: str,
    portfolio_id: str,
) -> None:
    """Persist one receipt-bound Manage action history for backup/restore validation."""
    claim = create_downstream_submission_claim(
        idempotency_key="dr-fixture-downstream-manage",
        request_fingerprint="sha256:dr-fixture-downstream-manage",
        resource_type=DownstreamSubmissionResourceType.CONVERSION_INTENT,
        resource_id=conversion_intent_id,
        target=ConversionTarget.MANAGE_REVIEW,
        source_authority=SourceSystem.LOTUS_MANAGE,
        actor_subject="dr-fixture-realization-worker",
        claimed_at_utc=fixture_time + timedelta(minutes=17),
        lease_owner="dr-fixture-realization-worker",
        lease_attempt_id="dr-fixture-downstream-attempt-004",
        lease_expires_at_utc=fixture_time + timedelta(minutes=22),
        correlation_id="corr-dr-fixture-downstream-004",
        trace_id="trace-dr-fixture-downstream-004",
    )
    repository.claim_downstream_submission(claim)
    receipt = DownstreamSubmissionOwnerReceipt(
        owner_authority=SourceSystem.LOTUS_MANAGE,
        owner_request_id="iai_dr_fixture_001",
        owner_realization_id="ima_dr_fixture_001",
        owner_work_id="ima_dr_fixture_001",
        source_event_version=1,
        source_evidence_fingerprint="sha256:aabbccddeeff",
    )
    repository.finalize_downstream_submission(
        idempotency_key=claim.idempotency_key,
        lease_owner=claim.lease_owner or "",
        lease_attempt_id=claim.lease_attempt_id or "",
        posture=DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
        finalized_at_utc=fixture_time + timedelta(minutes=18),
        owner_receipt=receipt,
    )
    intake_event = ManageActionRealizationEvent(
        event_id="imae_dr_fixture_001",
        action_id=receipt.owner_realization_id,
        source_event_version=1,
        event_type=ManageActionRealizationEventType.INTAKE_ACCEPTED,
        previous_status=None,
        status=ManageActionRealizationStatus.PENDING_REVIEW,
        occurred_at_utc=fixture_time + timedelta(minutes=18),
        actor_id="dr-fixture-manage-service",
        actor_role="SERVICE",
        reason_code="idea_conversion_intent_accepted_for_management_review",
        correlation_id="corr-dr-fixture-downstream-004",
        causation_id=conversion_intent_id,
    )
    repository.persist_manage_realization_history(
        support_reference=claim.support_reference,
        history=ManageActionRealizationHistory(
            contract_version="lotus-manage.idea-action-outcome-history.v1",
            intake_id=receipt.owner_request_id,
            management_action_id=receipt.owner_realization_id,
            source_authority="lotus-manage",
            portfolio_id=portfolio_id,
            idea_candidate_id=candidate_id,
            conversion_intent_id=conversion_intent_id,
            status=intake_event.status,
            source_event_version=intake_event.source_event_version,
            rebalance_execution_proven=False,
            order_execution_proven=False,
            client_publication_proven=False,
            events=(intake_event,),
        ),
    )
