from __future__ import annotations

from app.domain import (
    CausalInputRevision,
    SourceReconciliationPosture,
    SourceRevisionClaims,
)


def build_source_revision_claims(
    *,
    snapshot_id: str | None = None,
    source_revision: str | None = None,
    restatement_version: str | None = None,
    source_batch_id: str | None = None,
    source_cut_id: str | None = None,
    calculation_run_id: str | None = None,
    methodology_version: str | None = None,
    policy_version: str | None = None,
    causal_input_revisions: tuple[CausalInputRevision, ...] = (),
    reconciliation_status: str | None = None,
) -> SourceRevisionClaims | None:
    if not any(
        (
            snapshot_id,
            source_revision,
            restatement_version,
            source_batch_id,
            source_cut_id,
            calculation_run_id,
            methodology_version,
            policy_version,
            causal_input_revisions,
        )
    ):
        return None
    return SourceRevisionClaims(
        snapshot_id=snapshot_id,
        source_revision=source_revision,
        restatement_version=restatement_version,
        source_batch_id=source_batch_id,
        source_cut_id=source_cut_id,
        calculation_run_id=calculation_run_id,
        methodology_version=methodology_version,
        policy_version=policy_version,
        causal_input_revisions=causal_input_revisions,
        reconciliation_posture=source_reconciliation_posture(reconciliation_status),
    )


def source_reconciliation_posture(value: str | None) -> SourceReconciliationPosture:
    normalized = value.strip().lower() if value is not None else "unknown"
    aliases = {
        "complete": SourceReconciliationPosture.COMPLETE,
        "partial": SourceReconciliationPosture.PARTIAL,
        "failed": SourceReconciliationPosture.FAILED,
        "unreconciled": SourceReconciliationPosture.FAILED,
        "not_applicable": SourceReconciliationPosture.NOT_APPLICABLE,
    }
    return aliases.get(normalized, SourceReconciliationPosture.UNKNOWN)
