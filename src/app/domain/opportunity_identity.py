from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
import hashlib
import json
from typing import TypeAlias

from app.domain.access_scope import ReviewAccessScope
from app.domain.ideas import (
    CandidateChangeReason,
    CandidateIdentity,
    OpportunityFamily,
    SourceRef,
)
from app.domain.source_revision import source_revision_claims_payload


PREVIOUS_OPPORTUNITY_IDENTITY_POLICY_VERSION = "idea-opportunity-identity-v2"
OPPORTUNITY_IDENTITY_POLICY_VERSION = "idea-opportunity-identity-v3"
OBSERVATION_ONLY_MATERIAL_FACTS = frozenset({"as_of_date"})

IdentityMaterialValue: TypeAlias = str | int | bool | None


@dataclass(frozen=True)
class OpportunityIdentity:
    """Separate stable opportunity scope, material state, and evidence version."""

    policy_version: str
    opportunity_kind: str
    business_identity_id: str
    material_fingerprint: str
    evidence_fingerprint: str
    candidate_id: str
    signal_id: str
    evidence_packet_id: str
    lineage_id: str

    def initial_candidate_identity(self) -> CandidateIdentity:
        return CandidateIdentity(
            business_identity_id=self.business_identity_id,
            policy_version=self.policy_version,
            material_fingerprint=self.material_fingerprint,
            material_version=1,
            evidence_version=1,
            change_reason=CandidateChangeReason.INITIAL_DETECTION,
        )


@dataclass(frozen=True)
class OpportunityBusinessIdentity:
    """Stable identity for one opportunity kind inside its governed business scope."""

    business_identity_id: str
    candidate_id: str


def build_opportunity_business_identity(
    *,
    family: OpportunityFamily,
    opportunity_kind: str,
    as_of_date: date,
    access_scope: ReviewAccessScope | None,
) -> OpportunityBusinessIdentity:
    """Build identity without requiring evidence or a currently eligible material state."""
    identity, _ = _build_opportunity_business_identity(
        family=family,
        opportunity_kind=opportunity_kind,
        as_of_date=as_of_date,
        access_scope=access_scope,
    )
    return identity


def _build_opportunity_business_identity(
    *,
    family: OpportunityFamily,
    opportunity_kind: str,
    as_of_date: date,
    access_scope: ReviewAccessScope | None,
) -> tuple[OpportunityBusinessIdentity, str]:
    normalized_kind = opportunity_kind.strip()
    if not normalized_kind:
        raise ValueError("opportunity_kind is required")
    business_digest = _canonical_digest(
        {
            "family": family.value,
            "opportunity_kind": normalized_kind,
            "scope": _business_scope_payload(access_scope, as_of_date=as_of_date),
        }
    )
    identifier_kind = normalized_kind.replace("-", "_")
    candidate_token = business_digest[:16]
    return (
        OpportunityBusinessIdentity(
            business_identity_id=f"opportunity_{identifier_kind}_{business_digest[:24]}",
            candidate_id=f"idea_{identifier_kind}_{candidate_token}",
        ),
        business_digest,
    )


def build_opportunity_identity(
    *,
    family: OpportunityFamily,
    opportunity_kind: str,
    as_of_date: date,
    access_scope: ReviewAccessScope | None,
    material_facts: Mapping[str, IdentityMaterialValue],
    source_refs: tuple[SourceRef, ...],
) -> OpportunityIdentity:
    """Build deterministic identities without treating source bytes as business meaning."""
    normalized_kind = opportunity_kind.strip()
    if not material_facts:
        raise ValueError("material_facts is required")
    if not source_refs:
        raise ValueError("source_refs is required")
    _validate_material_facts(material_facts)

    business_identity, business_digest = _build_opportunity_business_identity(
        family=family,
        opportunity_kind=normalized_kind,
        as_of_date=as_of_date,
        access_scope=access_scope,
    )
    material_digest = _canonical_digest(
        {
            "business_identity_digest": business_digest,
            "identity_policy_version": OPPORTUNITY_IDENTITY_POLICY_VERSION,
            "material_facts": dict(material_facts),
        }
    )
    evidence_digest = _canonical_digest(
        {
            "business_identity_digest": business_digest,
            "material_identity_digest": material_digest,
            "source_refs": [_source_ref_identity_payload(ref) for ref in _sorted_refs(source_refs)],
        }
    )
    candidate_token = business_digest[:16]
    material_token = material_digest[:16]
    evidence_token = evidence_digest[:16]
    identifier_kind = normalized_kind.replace("-", "_")
    return OpportunityIdentity(
        policy_version=OPPORTUNITY_IDENTITY_POLICY_VERSION,
        opportunity_kind=normalized_kind,
        business_identity_id=business_identity.business_identity_id,
        material_fingerprint=f"sha256:{material_digest}",
        evidence_fingerprint=f"sha256:{evidence_digest}",
        candidate_id=business_identity.candidate_id,
        signal_id=(f"signal_{identifier_kind}_{candidate_token}_{material_token}_{evidence_token}"),
        evidence_packet_id=(
            f"iep_{identifier_kind}_{candidate_token}_{material_token}_{evidence_token}"
        ),
        lineage_id=(
            f"lineage:lotus-idea:{normalized_kind}:{candidate_token}:"
            f"{material_token}:{evidence_token}"
        ),
    )


def _validate_material_facts(material_facts: Mapping[str, IdentityMaterialValue]) -> None:
    for key, value in material_facts.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("material fact names must be non-blank strings")
        if value is not None and not isinstance(value, (str, int, bool)):
            raise TypeError(f"material fact {key} must be a canonical scalar")
    observation_only_facts = OBSERVATION_ONLY_MATERIAL_FACTS.intersection(material_facts)
    if observation_only_facts:
        names = ", ".join(sorted(observation_only_facts))
        raise ValueError(f"observation-only facts cannot define economic materiality: {names}")


def _business_scope_payload(
    access_scope: ReviewAccessScope | None,
    *,
    as_of_date: date,
) -> dict[str, str]:
    if access_scope is None:
        return {
            "scope_kind": "unscoped_evaluation_date",
            "as_of_date": as_of_date.isoformat(),
        }
    return {
        "scope_kind": "review_access_scope",
        "tenant_id": access_scope.tenant_id,
        "book_id": access_scope.book_id,
        "portfolio_id": access_scope.portfolio_id,
        "client_id": access_scope.client_id,
    }


def _sorted_refs(source_refs: tuple[SourceRef, ...]) -> tuple[SourceRef, ...]:
    return tuple(
        sorted(
            source_refs,
            key=lambda ref: (
                ref.source_system.value,
                ref.product_id,
                ref.product_version,
                ref.route,
                ref.as_of_date,
                ref.generated_at_utc,
                ref.content_hash,
            ),
        )
    )


def _source_ref_identity_payload(source_ref: SourceRef) -> dict[str, object]:
    return {
        "source_system": source_ref.source_system.value,
        "product_id": source_ref.product_id,
        "product_version": source_ref.product_version,
        "route": source_ref.route,
        "as_of_date": source_ref.as_of_date.isoformat(),
        "generated_at_utc": source_ref.generated_at_utc.isoformat(),
        "content_hash": source_ref.content_hash,
        "data_quality_status": source_ref.data_quality_status,
        "freshness": source_ref.freshness.value,
        "revision_claims": source_revision_claims_payload(source_ref.revision_claims),
    }


def _canonical_digest(payload: Mapping[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "PREVIOUS_OPPORTUNITY_IDENTITY_POLICY_VERSION",
    "OPPORTUNITY_IDENTITY_POLICY_VERSION",
    "IdentityMaterialValue",
    "OpportunityBusinessIdentity",
    "OpportunityIdentity",
    "build_opportunity_business_identity",
    "build_opportunity_identity",
]
