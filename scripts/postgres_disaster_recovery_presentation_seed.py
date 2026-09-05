# ruff: noqa: E402
from datetime import timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.domain import CandidatePresentationReceipt, IdeaCandidate, PresentationReceiptDecision
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from scripts.postgres_disaster_recovery_fixture_data import FIXTURE_TIME


def seed_presentation_receipt(
    repository: PostgresIdeaRepository,
    candidate: IdeaCandidate,
) -> None:
    result = repository.record_presentation_receipt(
        CandidatePresentationReceipt(
            receipt_id="dr-fixture-presentation-receipt-001",
            candidate_id=candidate.candidate_id,
            tenant_id="tenant-dr-fixture",
            presented_at_utc=FIXTURE_TIME + timedelta(minutes=15),
            rank_at_presentation=1,
            visible_candidate_count=2,
            queue_snapshot_digest=f"sha256:{'c' * 64}",
            queue_policy_version="idea-review-queue-v1",
            ranking_policy_version="idea-score-v2",
            candidate_material_version=candidate.identity.material_version,
            candidate_evidence_version=candidate.identity.evidence_version,
            source_revision_vector_digest=candidate.evidence_packet.source_revision_vector_digest,
            source_cut_posture=candidate.evidence_packet.source_cut_posture,
            accepted_at_utc=FIXTURE_TIME + timedelta(minutes=15),
        )
    )
    if result.decision is not PresentationReceiptDecision.ACCEPTED:
        raise RuntimeError("fixture presentation receipt was not persisted")


__all__ = ["seed_presentation_receipt"]
