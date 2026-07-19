# ruff: noqa: E402
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
from typing import cast

import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.domain import (  # noqa: E402
    CandidatePersistenceDecision,
    DownstreamSubmissionClaimDecision,
    DownstreamSubmissionMutationDecision,
    DownstreamSubmissionPosture,
    OutboxRecoveryDecision,
    outbox_recovery_request_payload,
)
from app.infrastructure.postgres_disaster_recovery import (  # noqa: E402
    PostgresRestoredDatabaseInspector,
)
from app.infrastructure.postgres_protocols import PostgresConnection  # noqa: E402
from app.infrastructure.postgres_repository import PostgresIdeaRepository  # noqa: E402
from scripts.disaster_recovery_evidence_io import (  # noqa: E402
    write_dataclass_evidence_atomic,
)

TARGET_DATABASE_URL_ENV = "LOTUS_IDEA_DR_TARGET_DATABASE_URL"
DEFAULT_OUTPUT_PATH = ROOT / "output/disaster-recovery/postgres-resume-evidence.json"
REPLAY_CANDIDATE_ID = "idea_dr_fixture_conversion"
REPLAY_CANDIDATE_KEY = "dr-fixture-conversion"


@dataclass(frozen=True)
class RestoreResumeEvidence:
    evidence_version: str
    status: str
    operator_id: str
    correlation_id: str
    candidate_replay_decision: str
    outbox_recovery_replay_decision: str
    downstream_claim_decisions: dict[str, str]
    stale_lease_finalize_decision: str
    table_content_sha256_before: dict[str, str]
    table_content_sha256_after: dict[str, str]
    no_duplicate_or_mutation: bool
    source_safe: bool = True
    supported_feature_promoted: bool = False
    certification_status: str = "not_certified"


def validate_restore_resume_safety(
    database_url: str,
    *,
    operator_id: str,
    correlation_id: str,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> RestoreResumeEvidence:
    if not database_url.strip():
        raise ValueError("database_url is required")
    normalized_operator_id = _safe_identifier(operator_id, "operator_id")
    normalized_correlation_id = _safe_identifier(correlation_id, "correlation_id")
    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        typed_connection = cast(PostgresConnection, connection)
        repository = PostgresIdeaRepository(typed_connection)
        before_snapshot = repository.snapshot()
        owned_tables = frozenset(_owned_tables())
        before = PostgresRestoredDatabaseInspector(database_url).inspect(
            expected_tables=owned_tables
        )

        candidate_record = before_snapshot.candidate_records[REPLAY_CANDIDATE_ID]
        candidate_replay = repository.persist_candidate(
            candidate_record.candidate,
            idempotency_key=REPLAY_CANDIDATE_KEY,
            payload={"candidateId": REPLAY_CANDIDATE_ID},
            actor_subject="dr-fixture-ingestion-worker",
            occurred_at_utc=candidate_record.persisted_at_utc,
        )
        recovery_audit = repository.outbox_recovery_audit_records()[0]
        recovery_payload = outbox_recovery_request_payload(
            support_reference=recovery_audit.support_reference,
            reason=recovery_audit.reason,
            change_reference=recovery_audit.change_reference,
            actor_subject=recovery_audit.actor_subject,
        )
        recovery_replay = repository.claim_dead_letter_for_recovery(
            support_reference=recovery_audit.support_reference,
            idempotency_key="dr-fixture-outbox-recovery-001",
            request_payload=recovery_payload,
            actor_subject=recovery_audit.actor_subject,
            reason=recovery_audit.reason,
            change_reference=recovery_audit.change_reference,
            requested_at_utc=recovery_audit.requested_at_utc,
            lease_owner=recovery_audit.lease_owner,
            lease_attempt_id=recovery_audit.lease_attempt_id,
            lease_expires_at_utc=recovery_audit.lease_expires_at_utc,
        )
        downstream_decisions: dict[str, str] = {}
        records = tuple(before_snapshot.downstream_submission_records.values())
        for record in records:
            decision = repository.claim_downstream_submission(record).decision
            downstream_decisions[record.resource_type.value] = decision.value
        in_flight = next(
            record for record in records if record.status is DownstreamSubmissionPosture.IN_FLIGHT
        )
        stale_finalize = repository.finalize_downstream_submission(
            idempotency_key=in_flight.idempotency_key,
            lease_owner="stale-restore-worker",
            lease_attempt_id="stale-restore-attempt",
            posture=DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
            finalized_at_utc=in_flight.updated_at_utc,
        )

    after = PostgresRestoredDatabaseInspector(database_url).inspect(expected_tables=owned_tables)
    no_mutation = before.table_content_sha256 == after.table_content_sha256
    passed = (
        candidate_replay.decision is CandidatePersistenceDecision.REPLAYED
        and recovery_replay.decision is OutboxRecoveryDecision.REPLAYED
        and set(downstream_decisions.values())
        == {DownstreamSubmissionClaimDecision.RECONCILIATION_REQUIRED.value}
        and stale_finalize.decision is DownstreamSubmissionMutationDecision.LEASE_CONFLICT
        and no_mutation
    )
    evidence = RestoreResumeEvidence(
        evidence_version="1.0.0",
        status="passed" if passed else "failed",
        operator_id=normalized_operator_id,
        correlation_id=normalized_correlation_id,
        candidate_replay_decision=candidate_replay.decision.value,
        outbox_recovery_replay_decision=recovery_replay.decision.value,
        downstream_claim_decisions=dict(sorted(downstream_decisions.items())),
        stale_lease_finalize_decision=stale_finalize.decision.value,
        table_content_sha256_before=dict(sorted(before.table_content_sha256.items())),
        table_content_sha256_after=dict(sorted(after.table_content_sha256.items())),
        no_duplicate_or_mutation=no_mutation,
    )
    write_dataclass_evidence_atomic(output_path, evidence)
    return evidence


def _owned_tables() -> tuple[str, ...]:
    contract_path = ROOT / "contracts/operations/lotus-idea-postgres-disaster-recovery.v1.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    return tuple(contract["restore_verification"]["owned_tables"])


def _safe_identifier(value: str, field_name: str) -> str:
    if (
        not value
        or len(value) > 128
        or not all(character.isalnum() or character in "._:-" for character in value)
    ):
        raise ValueError(f"{field_name} must be a source-safe identifier")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prove no-duplicate resume safety on restored Lotus Idea PostgreSQL state"
    )
    parser.add_argument("--operator-id", required=True)
    parser.add_argument("--correlation-id", required=True)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser


def main() -> int:
    args = _parser().parse_args()
    database_url = os.getenv(TARGET_DATABASE_URL_ENV, "").strip()
    if not database_url:
        print(f"{TARGET_DATABASE_URL_ENV} is required")
        return 2
    try:
        evidence = validate_restore_resume_safety(
            database_url,
            operator_id=args.operator_id,
            correlation_id=args.correlation_id,
            output_path=args.output_path,
        )
    except (KeyError, OSError, RuntimeError, TypeError, ValueError, psycopg.Error) as exc:
        print(f"PostgreSQL restore resume validation failed: {type(exc).__name__}")
        return 1
    print(f"PostgreSQL restore resume validation {evidence.status}")
    return 0 if evidence.status == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
