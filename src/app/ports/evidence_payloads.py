from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.domain import (
    CausalInputRevision,
    SourceCutTolerance,
    SourceReconciliationPosture,
    SourceRef,
    SourceRevisionClaims,
)
from app.domain.access_scope import ReviewAccessScope
from app.domain.source_revision import source_revision_claims_payload


def source_ref_payload(source_ref: SourceRef) -> dict[str, Any]:
    return {
        "product_id": source_ref.product_id,
        "source_system": source_ref.source_system.value,
        "product_version": source_ref.product_version,
        "route": source_ref.route,
        "as_of_date": source_ref.as_of_date.isoformat(),
        "generated_at_utc": source_ref.generated_at_utc.isoformat(),
        "content_hash": source_ref.content_hash,
        "data_quality_status": source_ref.data_quality_status,
        "freshness": source_ref.freshness.value,
        "revision_claims": source_revision_claims_payload(source_ref.revision_claims),
    }


def source_revision_claims_from_payload(
    payload: Mapping[str, Any] | None,
) -> SourceRevisionClaims | None:
    if payload is None:
        return None
    claim_posture = payload.get("claim_posture")
    if claim_posture == "unknown":
        if set(payload) != {"claim_posture"}:
            raise ValueError("unknown source revision claims cannot carry owner claim fields")
        return None
    if claim_posture != "owner_claimed":
        raise ValueError("source revision claim_posture is invalid")
    causal_payload = payload.get("causal_input_revisions", ())
    if not isinstance(causal_payload, (list, tuple)):
        raise ValueError("causal_input_revisions must be an array")
    return SourceRevisionClaims(
        snapshot_id=_optional_text(payload, "snapshot_id"),
        source_revision=_optional_text(payload, "source_revision"),
        restatement_version=_optional_text(payload, "restatement_version"),
        source_batch_id=_optional_text(payload, "source_batch_id"),
        source_cut_id=_optional_text(payload, "source_cut_id"),
        calculation_run_id=_optional_text(payload, "calculation_run_id"),
        methodology_version=_optional_text(payload, "methodology_version"),
        policy_version=_optional_text(payload, "policy_version"),
        causal_input_revisions=tuple(_causal_input_revision(item) for item in causal_payload),
        reconciliation_posture=SourceReconciliationPosture(
            str(payload.get("reconciliation_posture", "unknown"))
        ),
    )


def source_cut_tolerance_payload(tolerance: SourceCutTolerance | None) -> dict[str, Any] | None:
    if tolerance is None:
        return None
    return {
        "policy_version": tolerance.policy_version,
        "maximum_generated_time_skew_seconds": tolerance.maximum_generated_time_skew_seconds,
    }


def source_cut_tolerance_from_payload(
    payload: Mapping[str, Any] | None,
) -> SourceCutTolerance | None:
    if payload is None:
        return None
    return SourceCutTolerance(
        policy_version=str(payload["policy_version"]),
        maximum_generated_time_skew_seconds=int(payload["maximum_generated_time_skew_seconds"]),
    )


def _causal_input_revision(payload: object) -> CausalInputRevision:
    if not isinstance(payload, Mapping):
        raise ValueError("causal input revision must be an object")
    return CausalInputRevision(
        product_id=str(payload["product_id"]),
        source_revision=str(payload["source_revision"]),
        restatement_version=_optional_text(payload, "restatement_version"),
    )


def _optional_text(payload: Mapping[str, Any], field_name: str) -> str | None:
    value = payload.get(field_name)
    return str(value) if value is not None else None


def access_scope_payload(scope: ReviewAccessScope | None) -> dict[str, Any] | None:
    if scope is None:
        return None
    return {
        "tenant_id": scope.tenant_id,
        "book_id": scope.book_id,
        "portfolio_id": scope.portfolio_id,
        "client_id": scope.client_id,
    }
