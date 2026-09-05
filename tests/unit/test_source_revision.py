from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest

from app.domain.ideas import (
    EvidenceFreshness,
    EvidenceSupportability,
    IdeaEvidencePacket,
    LineageRef,
    ReasonCode,
    SourceRef,
    SourceSystem,
)
from app.domain.source_revision import (
    CausalInputRevision,
    SourceCutPosture,
    SourceCutTolerance,
    SourceReconciliationPosture,
    SourceRevisionClaims,
    source_cut_posture,
    source_revision_vector_digest,
)
from app.domain.evidence_hashing import evidence_hash_for_source_refs


def _claims(**changes: object) -> SourceRevisionClaims:
    values: dict[str, Any] = {
        "snapshot_id": "snapshot-101",
        "source_revision": "revision-7",
        "restatement_version": "restatement-2",
        "source_cut_id": "close-2026-09-04",
        "methodology_version": "methodology-4",
        "causal_input_revisions": (),
        "reconciliation_posture": SourceReconciliationPosture.COMPLETE,
    }
    values.update(changes)
    return SourceRevisionClaims(**values)


def _source(product_id: str, **changes: object) -> SourceRef:
    values: dict[str, Any] = {
        "product_id": product_id,
        "source_system": SourceSystem.LOTUS_CORE,
        "product_version": "v1",
        "route": "/integration/source",
        "as_of_date": date(2026, 9, 4),
        "generated_at_utc": datetime(2026, 9, 4, 20, 0, tzinfo=UTC),
        "content_hash": f"sha256:{product_id}",
        "data_quality_status": "complete",
        "freshness": EvidenceFreshness.CURRENT,
        "revision_claims": _claims(),
    }
    values.update(changes)
    return SourceRef(**values)


def test_revision_vector_digest_is_independent_of_input_order() -> None:
    first = _source("lotus-core:PortfolioStateSnapshot:v1")
    second = _source("lotus-core:HoldingsAsOf:v1")

    assert source_revision_vector_digest((first, second)) == source_revision_vector_digest(
        (second, first)
    )


@pytest.mark.parametrize(
    "changed_claims",
    [
        _claims(source_revision="revision-8"),
        _claims(restatement_version="restatement-3"),
        _claims(methodology_version="methodology-5"),
        _claims(
            causal_input_revisions=(
                CausalInputRevision(
                    product_id="lotus-core:HoldingsAsOf:v1",
                    source_revision="holdings-32",
                ),
            )
        ),
    ],
)
def test_revision_vector_digest_changes_with_owner_revision_identity(
    changed_claims: SourceRevisionClaims,
) -> None:
    source = _source("lotus-core:PortfolioStateSnapshot:v1")

    assert source_revision_vector_digest((source,)) != source_revision_vector_digest(
        (replace(source, revision_claims=changed_claims),)
    )


def test_cut_posture_requires_authoritative_claims() -> None:
    known = _source("lotus-core:PortfolioStateSnapshot:v1")
    unknown = replace(known, product_id="lotus-core:HoldingsAsOf:v1", revision_claims=None)

    assert source_cut_posture((replace(known, revision_claims=None),)) is SourceCutPosture.UNKNOWN
    assert source_cut_posture((known, unknown)) is SourceCutPosture.PARTIAL
    assert (
        source_cut_posture(
            (
                replace(
                    known,
                    revision_claims=_claims(
                        reconciliation_posture=SourceReconciliationPosture.FAILED
                    ),
                ),
            )
        )
        is SourceCutPosture.MIXED
    )
    assert (
        source_cut_posture(
            (replace(known, revision_claims=SourceRevisionClaims(methodology_version="risk.v1")),)
        )
        is SourceCutPosture.PARTIAL
    )


def test_shared_owner_cut_is_coherent_and_conflicting_cut_is_mixed() -> None:
    first = _source("lotus-core:PortfolioStateSnapshot:v1")
    second = _source("lotus-core:HoldingsAsOf:v1")

    assert source_cut_posture((first, second)) is SourceCutPosture.COHERENT
    assert (
        source_cut_posture(
            (first, replace(second, revision_claims=_claims(source_cut_id="different-cut")))
        )
        is SourceCutPosture.MIXED
    )


def test_declared_tolerance_is_explicit_and_versioned() -> None:
    first = _source(
        "lotus-core:PortfolioStateSnapshot:v1",
        revision_claims=_claims(source_cut_id=None),
    )
    second = _source(
        "lotus-risk:PortfolioRiskSummary:v1",
        source_system=SourceSystem.LOTUS_RISK,
        generated_at_utc=first.generated_at_utc + timedelta(seconds=30),
        revision_claims=_claims(source_cut_id=None),
    )

    assert source_cut_posture((first, second)) is SourceCutPosture.UNKNOWN
    assert (
        source_cut_posture(
            (first, second),
            tolerance=SourceCutTolerance(
                policy_version="source-cut-tolerance-v1",
                maximum_generated_time_skew_seconds=60,
            ),
        )
        is SourceCutPosture.COHERENT_WITH_DECLARED_TOLERANCE
    )


@pytest.mark.parametrize("reverse_order", [False, True])
@pytest.mark.parametrize(
    ("causal_revision", "causal_restatement"),
    [
        ("revision-1", "restatement-2"),
        ("revision-2", "restatement-1"),
    ],
)
def test_explicit_causal_contradiction_is_mixed_even_with_shared_cut(
    causal_revision: str,
    causal_restatement: str,
    reverse_order: bool,
) -> None:
    holdings = _source(
        "lotus-core:HoldingsAsOf:v1",
        revision_claims=_claims(
            source_revision="revision-2",
            restatement_version="restatement-2",
        ),
    )
    risk = _source(
        "lotus-risk:PortfolioRiskSummary:v1",
        source_system=SourceSystem.LOTUS_RISK,
        revision_claims=_claims(
            source_revision="risk-revision-5",
            restatement_version="risk-restatement-1",
            causal_input_revisions=(
                CausalInputRevision(
                    product_id=holdings.product_id,
                    source_revision=causal_revision,
                    restatement_version=causal_restatement,
                ),
            ),
        ),
    )
    sources = (risk, holdings) if reverse_order else (holdings, risk)

    assert source_cut_posture(sources) is SourceCutPosture.MIXED


def test_matching_causal_revision_and_restatement_preserve_coherent_cut() -> None:
    holdings = _source(
        "lotus-core:HoldingsAsOf:v1",
        revision_claims=_claims(
            source_revision="revision-2",
            restatement_version="restatement-2",
        ),
    )
    risk = _source(
        "lotus-risk:PortfolioRiskSummary:v1",
        source_system=SourceSystem.LOTUS_RISK,
        revision_claims=_claims(
            source_revision="risk-revision-5",
            causal_input_revisions=(
                CausalInputRevision(
                    product_id=holdings.product_id,
                    source_revision="revision-2",
                    restatement_version="restatement-2",
                ),
            ),
        ),
    )

    assert source_cut_posture((holdings, risk)) is SourceCutPosture.COHERENT


def test_tolerance_cannot_excuse_explicit_causal_revision_contradiction() -> None:
    holdings = _source(
        "lotus-core:HoldingsAsOf:v1",
        revision_claims=_claims(source_cut_id=None, source_revision="revision-2"),
    )
    risk = _source(
        "lotus-risk:PortfolioRiskSummary:v1",
        source_system=SourceSystem.LOTUS_RISK,
        generated_at_utc=holdings.generated_at_utc + timedelta(seconds=30),
        revision_claims=_claims(
            source_cut_id=None,
            source_revision="risk-revision-5",
            causal_input_revisions=(
                CausalInputRevision(
                    product_id=holdings.product_id,
                    source_revision="revision-1",
                ),
            ),
        ),
    )

    assert (
        source_cut_posture(
            (holdings, risk),
            tolerance=SourceCutTolerance(
                policy_version="source-cut-tolerance-v1",
                maximum_generated_time_skew_seconds=60,
            ),
        )
        is SourceCutPosture.MIXED
    )


def test_unverifiable_causal_revision_remains_partial() -> None:
    holdings = _source(
        "lotus-core:HoldingsAsOf:v1",
        revision_claims=_claims(source_revision=None),
    )
    risk = _source(
        "lotus-risk:PortfolioRiskSummary:v1",
        source_system=SourceSystem.LOTUS_RISK,
        revision_claims=_claims(
            source_revision="risk-revision-5",
            causal_input_revisions=(
                CausalInputRevision(
                    product_id=holdings.product_id,
                    source_revision="revision-2",
                ),
            ),
        ),
    )

    assert source_cut_posture((holdings, risk)) is SourceCutPosture.PARTIAL


def test_missing_causal_source_remains_partial_without_inventing_identity() -> None:
    risk = _source(
        "lotus-risk:PortfolioRiskSummary:v1",
        source_system=SourceSystem.LOTUS_RISK,
        revision_claims=_claims(
            source_revision="risk-revision-5",
            causal_input_revisions=(
                CausalInputRevision(
                    product_id="lotus-core:HoldingsAsOf:v1",
                    source_revision="revision-2",
                ),
            ),
        ),
    )

    assert source_cut_posture((risk,)) is SourceCutPosture.PARTIAL


def test_unstated_causal_restatement_remains_partial_when_source_is_restated() -> None:
    holdings = _source(
        "lotus-core:HoldingsAsOf:v1",
        revision_claims=_claims(
            source_revision="revision-2",
            restatement_version="restatement-2",
        ),
    )
    risk = _source(
        "lotus-risk:PortfolioRiskSummary:v1",
        source_system=SourceSystem.LOTUS_RISK,
        revision_claims=_claims(
            source_revision="risk-revision-5",
            causal_input_revisions=(
                CausalInputRevision(
                    product_id=holdings.product_id,
                    source_revision="revision-2",
                ),
            ),
        ),
    )

    assert source_cut_posture((holdings, risk)) is SourceCutPosture.PARTIAL


def test_revision_claims_reject_duplicate_causal_input_products() -> None:
    causal = CausalInputRevision(product_id="lotus-core:HoldingsAsOf:v1", source_revision="31")

    with pytest.raises(ValueError, match="unique product_id"):
        _claims(causal_input_revisions=(causal, causal))


def test_revision_claim_value_objects_reject_unusable_identity() -> None:
    with pytest.raises(ValueError, match="product_id is required"):
        CausalInputRevision(product_id="", source_revision="revision-1")
    with pytest.raises(ValueError, match="surrounding whitespace"):
        CausalInputRevision(product_id=" product-1", source_revision="revision-1")
    with pytest.raises(ValueError, match="owner-issued revision identity"):
        SourceRevisionClaims()
    with pytest.raises(ValueError, match="must be non-negative"):
        SourceCutTolerance(
            policy_version="source-cut-tolerance-v1",
            maximum_generated_time_skew_seconds=-1,
        )


def test_cut_posture_classifies_incomplete_and_incoherent_owner_cuts() -> None:
    first = _source("lotus-core:PortfolioStateSnapshot:v1")
    second = _source("lotus-core:HoldingsAsOf:v1")

    assert (
        source_cut_posture(
            (
                replace(
                    first,
                    revision_claims=_claims(
                        reconciliation_posture=SourceReconciliationPosture.PARTIAL
                    ),
                ),
            )
        )
        is SourceCutPosture.PARTIAL
    )
    assert (
        source_cut_posture(
            (
                replace(
                    first,
                    revision_claims=_claims(
                        reconciliation_posture=SourceReconciliationPosture.UNKNOWN
                    ),
                ),
            )
        )
        is SourceCutPosture.PARTIAL
    )
    assert (
        source_cut_posture((first, replace(second, as_of_date=date(2026, 9, 3))))
        is SourceCutPosture.MIXED
    )
    assert (
        source_cut_posture((first, replace(second, revision_claims=_claims(source_cut_id=None))))
        is SourceCutPosture.PARTIAL
    )
    assert (
        source_cut_posture(
            (
                replace(first, revision_claims=_claims(source_cut_id=None)),
                replace(
                    second,
                    generated_at_utc=first.generated_at_utc + timedelta(seconds=61),
                    revision_claims=_claims(source_cut_id=None),
                ),
            ),
            tolerance=SourceCutTolerance(
                policy_version="source-cut-tolerance-v1",
                maximum_generated_time_skew_seconds=60,
            ),
        )
        is SourceCutPosture.MIXED
    )
    with pytest.raises(ValueError, match="source_refs is required"):
        source_cut_posture(())


def test_revision_vector_rejects_duplicate_source_products() -> None:
    source = _source("lotus-core:PortfolioStateSnapshot:v1")

    with pytest.raises(ValueError, match="duplicate source product identity"):
        source_revision_vector_digest((source, source))


def test_evidence_packet_exposes_derived_revision_vector_and_cut_posture() -> None:
    source = _source("lotus-core:PortfolioStateSnapshot:v1")
    packet = IdeaEvidencePacket(
        evidence_packet_id="evidence-101",
        supportability=EvidenceSupportability.READY,
        source_refs=(source,),
        lineage_ref=LineageRef(
            lineage_id="lineage-101",
            source_refs=(source,),
            content_hash="sha256:lineage",
        ),
        reason_codes=(ReasonCode.REVIEW_REQUIRED,),
        created_at_utc=datetime(2026, 9, 4, 20, 1, tzinfo=UTC),
    )

    assert packet.source_cut_posture is SourceCutPosture.COHERENT
    assert packet.source_revision_vector_digest == source_revision_vector_digest((source,))


def test_evidence_hash_changes_for_same_date_restatement() -> None:
    source = _source("lotus-core:PortfolioStateSnapshot:v1")
    restated = replace(
        source,
        revision_claims=_claims(restatement_version="restatement-3"),
    )

    assert source.as_of_date == restated.as_of_date
    assert evidence_hash_for_source_refs((source,)) != evidence_hash_for_source_refs((restated,))
