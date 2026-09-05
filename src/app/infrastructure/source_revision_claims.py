from __future__ import annotations

from collections.abc import Mapping
from typing import Any

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


def source_revision_claims_from_payloads(
    *payloads: Mapping[str, Any],
) -> SourceRevisionClaims | None:
    """Map common snake/camel owner fields without inferring missing authority."""

    return build_source_revision_claims(
        snapshot_id=first_text_from_payloads(payloads, "snapshot_id", "snapshotId"),
        source_revision=first_text_from_payloads(payloads, "source_revision", "sourceRevision"),
        restatement_version=first_text_from_payloads(
            payloads, "restatement_version", "restatementVersion"
        ),
        source_batch_id=first_text_from_payloads(
            payloads, "source_batch_fingerprint", "sourceBatchFingerprint"
        ),
        source_cut_id=first_text_from_payloads(payloads, "source_cut_id", "sourceCutId"),
        calculation_run_id=first_text_from_payloads(payloads, "calculation_id", "calculationId"),
        methodology_version=first_text_from_payloads(
            payloads, "methodology_version", "methodologyVersion"
        ),
        policy_version=first_text_from_payloads(payloads, "policy_version", "policyVersion"),
        reconciliation_status=first_text_from_payloads(
            payloads, "reconciliation_status", "reconciliationStatus"
        ),
    )


def first_text_from_payloads(payloads: tuple[Mapping[str, Any], ...], *keys: str) -> str | None:
    for payload in payloads:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None
