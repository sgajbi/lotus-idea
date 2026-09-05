from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime

import pytest

from app.domain.access_scope import ReviewAccessScope
from app.domain.ideas import EvidenceFreshness, OpportunityFamily, SourceRef, SourceSystem
from app.domain.source_revision import SourceReconciliationPosture, SourceRevisionClaims
from app.domain.opportunity_identity import (
    OPPORTUNITY_IDENTITY_POLICY_VERSION,
    OpportunityIdentity,
    build_opportunity_business_identity,
    build_opportunity_identity,
)


AS_OF_DATE = date(2026, 8, 30)
GENERATED_AT = datetime(2026, 8, 30, 9, 30, tzinfo=UTC)
SCOPE = ReviewAccessScope(
    tenant_id="tenant-private-bank-sg",
    book_id="book-advisor-001",
    portfolio_id="PB_SG_GLOBAL_BAL_001",
    client_id="client-001",
)


def _source_ref(
    product_id: str,
    content_hash: str,
    *,
    as_of_date: date = AS_OF_DATE,
) -> SourceRef:
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route=f"/source/{product_id}",
        as_of_date=as_of_date,
        generated_at_utc=GENERATED_AT,
        content_hash=content_hash,
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )


def _identity(
    *,
    cash_weight: str = "0.18",
    source_refs: tuple[SourceRef, ...] | None = None,
    scope: ReviewAccessScope | None = SCOPE,
    opportunity_kind: str = "high_cash",
    as_of_date: date = AS_OF_DATE,
) -> OpportunityIdentity:
    return build_opportunity_identity(
        family=OpportunityFamily.HIGH_CASH,
        opportunity_kind=opportunity_kind,
        as_of_date=as_of_date,
        access_scope=scope,
        material_facts={
            "cash_weight": cash_weight,
            "policy_version": "idle-liquidity-v1",
        },
        source_refs=source_refs
        or (
            _source_ref(
                "portfolio-state",
                "sha256:portfolio-state-v1",
                as_of_date=as_of_date,
            ),
            _source_ref("holdings", "sha256:holdings-v1", as_of_date=as_of_date),
        ),
    )


def test_source_correction_changes_evidence_version_without_changing_business_candidate() -> None:
    original_refs = (
        _source_ref("portfolio-state", "sha256:portfolio-state-v1"),
        _source_ref("holdings", "sha256:holdings-v1"),
    )
    corrected_refs = (
        replace(original_refs[0], content_hash="sha256:portfolio-state-corrected"),
        original_refs[1],
    )

    original = _identity(source_refs=original_refs)
    corrected = _identity(source_refs=corrected_refs)

    assert original.policy_version == OPPORTUNITY_IDENTITY_POLICY_VERSION
    assert corrected.business_identity_id == original.business_identity_id
    assert corrected.material_fingerprint == original.material_fingerprint
    assert corrected.candidate_id == original.candidate_id
    assert corrected.evidence_fingerprint != original.evidence_fingerprint
    assert corrected.signal_id != original.signal_id
    assert corrected.evidence_packet_id != original.evidence_packet_id
    assert corrected.lineage_id != original.lineage_id


def test_same_date_restatement_changes_evidence_identity_without_new_business_identity() -> None:
    source = _source_ref("portfolio-state", "sha256:portfolio-state-v1")
    original = replace(
        source,
        revision_claims=SourceRevisionClaims(
            snapshot_id="snapshot-1",
            restatement_version="restatement-1",
            reconciliation_posture=SourceReconciliationPosture.COMPLETE,
        ),
    )
    restated = replace(
        original,
        revision_claims=replace(
            original.revision_claims,
            restatement_version="restatement-2",
        ),
    )

    original_identity = _identity(source_refs=(original,))
    restated_identity = _identity(source_refs=(restated,))

    assert original.as_of_date == restated.as_of_date
    assert restated_identity.business_identity_id == original_identity.business_identity_id
    assert restated_identity.material_fingerprint == original_identity.material_fingerprint
    assert restated_identity.evidence_fingerprint != original_identity.evidence_fingerprint


def test_source_order_is_not_business_or_evidence_identity() -> None:
    refs = (
        _source_ref("portfolio-state", "sha256:portfolio-state-v1"),
        _source_ref("holdings", "sha256:holdings-v1"),
    )

    assert _identity(source_refs=refs) == _identity(source_refs=tuple(reversed(refs)))


def test_material_change_versions_candidate_under_the_same_business_identity() -> None:
    original = _identity(cash_weight="0.18")
    changed = _identity(cash_weight="0.23")

    assert changed.business_identity_id == original.business_identity_id
    assert changed.material_fingerprint != original.material_fingerprint
    assert changed.candidate_id == original.candidate_id
    assert changed.evidence_fingerprint != original.evidence_fingerprint
    assert changed.signal_id != original.signal_id
    assert changed.evidence_packet_id != original.evidence_packet_id
    assert changed.lineage_id != original.lineage_id


def test_business_identity_can_be_rebuilt_without_material_or_evidence_facts() -> None:
    complete = _identity()

    business = build_opportunity_business_identity(
        family=OpportunityFamily.HIGH_CASH,
        opportunity_kind="high_cash",
        as_of_date=AS_OF_DATE,
        access_scope=SCOPE,
    )

    assert business.business_identity_id == complete.business_identity_id
    assert business.candidate_id == complete.candidate_id


def test_observation_date_versions_evidence_not_scoped_candidate_materiality() -> None:
    next_date = date(2026, 8, 31)

    original = _identity()
    refreshed = _identity(as_of_date=next_date)

    assert refreshed.business_identity_id == original.business_identity_id
    assert refreshed.material_fingerprint == original.material_fingerprint
    assert refreshed.candidate_id == original.candidate_id
    assert refreshed.evidence_fingerprint != original.evidence_fingerprint


def test_initial_candidate_identity_carries_explicit_version_posture() -> None:
    identity = _identity().initial_candidate_identity()

    assert identity.business_identity_id == _identity().business_identity_id
    assert identity.policy_version == OPPORTUNITY_IDENTITY_POLICY_VERSION
    assert identity.material_fingerprint == _identity().material_fingerprint
    assert identity.material_version == 1
    assert identity.evidence_version == 1
    assert identity.change_reason.value == "initial_detection"
    assert identity.supersedes_material_version is None


def test_business_scope_and_opportunity_kind_are_identity_boundaries() -> None:
    other_scope = replace(SCOPE, portfolio_id="PB_SG_INCOME_002")

    assert _identity(scope=other_scope).business_identity_id != _identity().business_identity_id
    assert (
        _identity(opportunity_kind="drawdown_review").business_identity_id
        != _identity(opportunity_kind="high_volatility").business_identity_id
    )


def test_unscoped_diagnostics_are_bounded_by_evaluation_date() -> None:
    identity = _identity(scope=None)
    next_date_identity = _identity(scope=None, as_of_date=date(2026, 8, 31))

    assert identity.business_identity_id.startswith("opportunity_high_cash_")
    assert next_date_identity.business_identity_id != identity.business_identity_id


@pytest.mark.parametrize(
    ("field", "value", "expected_exception", "message"),
    (
        ("opportunity_kind", " ", ValueError, "opportunity_kind is required"),
        ("material_facts", {}, ValueError, "material_facts is required"),
        ("source_refs", (), ValueError, "source_refs is required"),
        (
            "material_facts",
            {1: "0.18"},
            ValueError,
            "material fact names must be non-blank strings",
        ),
        (
            "material_facts",
            {"as_of_date": AS_OF_DATE.isoformat(), "cash_weight": "0.18"},
            ValueError,
            "observation-only facts cannot define economic materiality: as_of_date",
        ),
        ("material_facts", {"cash_weight": 0.18}, TypeError, "canonical scalar"),
    ),
)
def test_identity_policy_rejects_ambiguous_or_noncanonical_inputs(
    field: str,
    value: object,
    expected_exception: type[Exception],
    message: str,
) -> None:
    arguments = {
        "family": OpportunityFamily.HIGH_CASH,
        "opportunity_kind": "high_cash",
        "as_of_date": AS_OF_DATE,
        "access_scope": SCOPE,
        "material_facts": {"cash_weight": "0.18"},
        "source_refs": (_source_ref("portfolio-state", "sha256:portfolio-state-v1"),),
    }
    arguments[field] = value

    with pytest.raises(expected_exception, match=message):
        build_opportunity_identity(**arguments)  # type: ignore[arg-type]
