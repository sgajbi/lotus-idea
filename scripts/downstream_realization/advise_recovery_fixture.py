# ruff: noqa: E402
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.domain import (
    AdviseProposalRealizationHistory,
    AdviseProposalRealizationOutcome,
    AdviseProposalRealizationStatus,
    AdviseProposalReviewWorkStatus,
    ConversionTarget,
    DownstreamSubmissionOwnerReceipt,
    DownstreamSubmissionPosture,
    DownstreamSubmissionResourceType,
    SourceSystem,
    create_downstream_submission_claim,
)
from app.infrastructure.postgres_repository import PostgresIdeaRepository


def seed_advise_realization_recovery_fixture(
    repository: PostgresIdeaRepository,
    *,
    fixture_time: datetime,
    candidate_id: str,
    conversion_intent_id: str,
    portfolio_id: str,
) -> None:
    """Persist one receipt-bound Advise history for backup/restore validation."""
    claim = create_downstream_submission_claim(
        idempotency_key="dr-fixture-downstream-advise",
        request_fingerprint="sha256:dr-fixture-downstream-advise",
        resource_type=DownstreamSubmissionResourceType.CONVERSION_INTENT,
        resource_id=conversion_intent_id,
        target=ConversionTarget.ADVISE_PROPOSAL,
        source_authority=SourceSystem.LOTUS_ADVISE,
        actor_subject="dr-fixture-realization-worker",
        claimed_at_utc=fixture_time + timedelta(minutes=15),
        lease_owner="dr-fixture-realization-worker",
        lease_attempt_id="dr-fixture-downstream-attempt-003",
        lease_expires_at_utc=fixture_time + timedelta(minutes=20),
        correlation_id="corr-dr-fixture-downstream-003",
        trace_id="trace-dr-fixture-downstream-003",
    )
    repository.claim_downstream_submission(claim)
    receipt = DownstreamSubmissionOwnerReceipt(
        owner_authority=SourceSystem.LOTUS_ADVISE,
        owner_request_id="ipi_dr_fixture_001",
        owner_realization_id="ipr_dr_fixture_001",
        owner_work_id="iarw_dr_fixture_001",
        source_event_version=1,
        source_evidence_fingerprint="sha256:dr-fixture-owner-evidence",
    )
    repository.finalize_downstream_submission(
        idempotency_key=claim.idempotency_key,
        lease_owner=claim.lease_owner or "",
        lease_attempt_id=claim.lease_attempt_id or "",
        posture=DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
        finalized_at_utc=fixture_time + timedelta(minutes=16),
        owner_receipt=receipt,
    )
    outcome = AdviseProposalRealizationOutcome(
        outcome_id="ipro_dr_fixture_001",
        source_event_version=1,
        status=AdviseProposalRealizationStatus.ACCEPTED_FOR_REVIEW,
        reason_code="idea_intake_accepted_for_adviser_review",
        occurred_at_utc=fixture_time + timedelta(minutes=16),
        review_work_id="iarw_dr_fixture_001",
        proposal_id=None,
        terminal=False,
    )
    repository.persist_advise_realization_history(
        support_reference=claim.support_reference,
        history=AdviseProposalRealizationHistory(
            realization_id=receipt.owner_realization_id,
            intake_id=receipt.owner_request_id,
            review_work_id=receipt.owner_work_id,
            review_work_status=AdviseProposalReviewWorkStatus.PENDING_ADVISER_REVIEW,
            source_authority="lotus-idea",
            realization_authority="lotus-advise",
            tenant_id="tenant-dr-fixture",
            legal_entity_code="SGPB",
            portfolio_id=portfolio_id,
            idea_candidate_id=candidate_id,
            conversion_intent_id=conversion_intent_id,
            source_evidence_fingerprint=receipt.source_evidence_fingerprint,
            current_status=outcome.status,
            current_source_event_version=outcome.source_event_version,
            proposal_id=None,
            proposal_record_created=False,
            suitability_authority_granted=False,
            order_created=False,
            client_publication_authorized=False,
            created_at_utc=outcome.occurred_at_utc,
            updated_at_utc=outcome.occurred_at_utc,
            outcomes=(outcome,),
        ),
    )
