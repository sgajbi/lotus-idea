from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Protocol


class SourceReconciliationPosture(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class SourceCutPosture(StrEnum):
    COHERENT = "coherent"
    COHERENT_WITH_DECLARED_TOLERANCE = "coherent_with_declared_tolerance"
    MIXED = "mixed"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


SOURCE_CUT_AUTHORITY_POLICY_VERSION = "idea-source-cut-authority-v1"
AUTHORITATIVE_SOURCE_CUT_POSTURES = frozenset(
    {
        SourceCutPosture.COHERENT,
        SourceCutPosture.COHERENT_WITH_DECLARED_TOLERANCE,
    }
)


def source_cut_is_authoritative(posture: SourceCutPosture) -> bool:
    return posture in AUTHORITATIVE_SOURCE_CUT_POSTURES


def _require_normalized_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")
    if value != value.strip():
        raise ValueError(f"{field_name} must not contain surrounding whitespace")


def _validate_optional_text(value: str | None, field_name: str) -> None:
    if value is not None:
        _require_normalized_text(value, field_name)


@dataclass(frozen=True)
class CausalInputRevision:
    product_id: str
    source_revision: str
    restatement_version: str | None = None

    def __post_init__(self) -> None:
        _require_normalized_text(self.product_id, "product_id")
        _require_normalized_text(self.source_revision, "source_revision")
        _validate_optional_text(self.restatement_version, "restatement_version")


@dataclass(frozen=True)
class SourceRevisionClaims:
    snapshot_id: str | None = None
    source_revision: str | None = None
    restatement_version: str | None = None
    source_batch_id: str | None = None
    source_cut_id: str | None = None
    calculation_run_id: str | None = None
    methodology_version: str | None = None
    policy_version: str | None = None
    causal_input_revisions: tuple[CausalInputRevision, ...] = ()
    reconciliation_posture: SourceReconciliationPosture = SourceReconciliationPosture.UNKNOWN

    def __post_init__(self) -> None:
        for field_name in (
            "snapshot_id",
            "source_revision",
            "restatement_version",
            "source_batch_id",
            "source_cut_id",
            "calculation_run_id",
            "methodology_version",
            "policy_version",
        ):
            _validate_optional_text(getattr(self, field_name), field_name)
        object.__setattr__(self, "causal_input_revisions", tuple(self.causal_input_revisions))
        product_ids = tuple(item.product_id for item in self.causal_input_revisions)
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("causal_input_revisions must have unique product_id values")
        if not self.has_revision_identity:
            raise ValueError("source revision claims require an owner-issued revision identity")

    @property
    def has_revision_identity(self) -> bool:
        return any(
            (
                self.snapshot_id,
                self.source_revision,
                self.restatement_version,
                self.source_batch_id,
                self.source_cut_id,
                self.calculation_run_id,
                self.methodology_version,
                self.policy_version,
                self.causal_input_revisions,
            )
        )

    @property
    def has_primary_revision_identity(self) -> bool:
        return any(
            (
                self.snapshot_id,
                self.source_revision,
                self.source_batch_id,
                self.source_cut_id,
                self.calculation_run_id,
            )
        )

    @property
    def is_authoritative(self) -> bool:
        return self.has_primary_revision_identity and self.reconciliation_posture in {
            SourceReconciliationPosture.COMPLETE,
            SourceReconciliationPosture.NOT_APPLICABLE,
        }


@dataclass(frozen=True)
class SourceCutTolerance:
    policy_version: str
    maximum_generated_time_skew_seconds: int

    def __post_init__(self) -> None:
        _require_normalized_text(self.policy_version, "policy_version")
        if self.maximum_generated_time_skew_seconds < 0:
            raise ValueError("maximum_generated_time_skew_seconds must be non-negative")


class RevisionSourceRef(Protocol):
    @property
    def product_id(self) -> str: ...

    @property
    def source_system(self) -> StrEnum: ...

    @property
    def product_version(self) -> str: ...

    @property
    def route(self) -> str: ...

    @property
    def as_of_date(self) -> date: ...

    @property
    def generated_at_utc(self) -> datetime: ...

    @property
    def content_hash(self) -> str: ...

    @property
    def data_quality_status(self) -> str: ...

    @property
    def freshness(self) -> StrEnum: ...

    @property
    def revision_claims(self) -> SourceRevisionClaims | None: ...


def source_revision_claims_payload(claims: SourceRevisionClaims | None) -> dict[str, object]:
    if claims is None:
        return {"claim_posture": SourceCutPosture.UNKNOWN.value}
    return {
        "claim_posture": "owner_claimed",
        "calculation_run_id": claims.calculation_run_id,
        "causal_input_revisions": [
            {
                "product_id": item.product_id,
                "restatement_version": item.restatement_version,
                "source_revision": item.source_revision,
            }
            for item in sorted(claims.causal_input_revisions, key=lambda item: item.product_id)
        ],
        "methodology_version": claims.methodology_version,
        "policy_version": claims.policy_version,
        "reconciliation_posture": claims.reconciliation_posture.value,
        "restatement_version": claims.restatement_version,
        "snapshot_id": claims.snapshot_id,
        "source_batch_id": claims.source_batch_id,
        "source_cut_id": claims.source_cut_id,
        "source_revision": claims.source_revision,
    }


def source_revision_vector_entry(source_ref: RevisionSourceRef) -> dict[str, object]:
    return {
        "as_of_date": source_ref.as_of_date.isoformat(),
        "claims": source_revision_claims_payload(source_ref.revision_claims),
        "content_hash": source_ref.content_hash,
        "product_id": source_ref.product_id,
        "product_version": source_ref.product_version,
        "source_system": source_ref.source_system.value,
    }


def source_revision_vector_digest(source_refs: tuple[RevisionSourceRef, ...]) -> str:
    _require_unique_sources(source_refs)
    payload = sorted(
        (source_revision_vector_entry(source_ref) for source_ref in source_refs),
        key=lambda item: (
            str(item["source_system"]),
            str(item["product_id"]),
            str(item["product_version"]),
        ),
    )
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def source_cut_posture(
    source_refs: tuple[RevisionSourceRef, ...],
    *,
    tolerance: SourceCutTolerance | None = None,
) -> SourceCutPosture:
    _require_unique_sources(source_refs)
    claims = tuple(source_ref.revision_claims for source_ref in source_refs)
    present_claims = tuple(item for item in claims if item is not None)
    if not present_claims:
        return SourceCutPosture.UNKNOWN
    if len(present_claims) != len(source_refs):
        return SourceCutPosture.PARTIAL
    if any(
        item.reconciliation_posture is SourceReconciliationPosture.PARTIAL
        for item in present_claims
    ):
        return SourceCutPosture.PARTIAL
    if any(
        item.reconciliation_posture is SourceReconciliationPosture.FAILED for item in present_claims
    ):
        return SourceCutPosture.MIXED
    if any(not item.has_primary_revision_identity for item in present_claims):
        return SourceCutPosture.PARTIAL
    if any(
        item.reconciliation_posture is SourceReconciliationPosture.UNKNOWN
        for item in present_claims
    ):
        return SourceCutPosture.PARTIAL
    if len(source_refs) == 1:
        return SourceCutPosture.COHERENT
    if len({source_ref.as_of_date for source_ref in source_refs}) != 1:
        return SourceCutPosture.MIXED

    cut_ids = tuple(item.source_cut_id for item in present_claims)
    if all(cut_ids):
        return SourceCutPosture.COHERENT if len(set(cut_ids)) == 1 else SourceCutPosture.MIXED
    if any(cut_ids):
        return SourceCutPosture.PARTIAL
    if tolerance is None:
        return SourceCutPosture.UNKNOWN
    generated_times = tuple(source_ref.generated_at_utc for source_ref in source_refs)
    observed_skew = (max(generated_times) - min(generated_times)).total_seconds()
    if observed_skew > tolerance.maximum_generated_time_skew_seconds:
        return SourceCutPosture.MIXED
    return SourceCutPosture.COHERENT_WITH_DECLARED_TOLERANCE


def _require_unique_sources(source_refs: tuple[RevisionSourceRef, ...]) -> None:
    if not source_refs:
        raise ValueError("source_refs is required")
    identities = tuple(
        (item.source_system.value, item.product_id, item.product_version) for item in source_refs
    )
    if len(identities) != len(set(identities)):
        raise ValueError("source revision vector contains duplicate source product identity")
