from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from app.domain import (
    CausalInputRevision,
    EvidenceFreshness,
    SourceReconciliationPosture,
    SourceRef,
    SourceRevisionClaims,
    SourceSystem,
)
from app.domain.access_scope import ReviewAccessScope
from app.ports.evidence_payloads import (
    access_scope_payload,
    source_ref_payload,
    source_revision_claims_from_payload,
)


def test_source_ref_payload_preserves_source_authority_fields() -> None:
    source_ref = SourceRef(
        product_id="lotus-core:PortfolioStateSnapshot:v1",
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route="/api/v1/portfolios/p1/state",
        as_of_date=date(2026, 6, 21),
        generated_at_utc=datetime(2026, 6, 21, 10, 30, tzinfo=UTC),
        content_hash="sha256:portfolio-state",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )

    assert source_ref_payload(source_ref) == {
        "product_id": "lotus-core:PortfolioStateSnapshot:v1",
        "source_system": "lotus-core",
        "product_version": "v1",
        "route": "/api/v1/portfolios/p1/state",
        "as_of_date": "2026-06-21",
        "generated_at_utc": "2026-06-21T10:30:00+00:00",
        "content_hash": "sha256:portfolio-state",
        "data_quality_status": "complete",
        "freshness": "current",
        "revision_claims": {"claim_posture": "unknown"},
    }


def test_access_scope_payload_preserves_private_banking_scope() -> None:
    scope = ReviewAccessScope(
        tenant_id="tenant-1",
        book_id="book-1",
        portfolio_id="portfolio-1",
        client_id="client-1",
    )

    assert access_scope_payload(scope) == {
        "tenant_id": "tenant-1",
        "book_id": "book-1",
        "portfolio_id": "portfolio-1",
        "client_id": "client-1",
    }
    assert access_scope_payload(None) is None


def test_source_revision_claims_round_trip_without_losing_owner_identity() -> None:
    claims = SourceRevisionClaims(
        snapshot_id="snapshot-1",
        restatement_version="restatement-2",
        methodology_version="methodology-3",
        causal_input_revisions=(
            CausalInputRevision(
                product_id="lotus-core:HoldingsAsOf:v1",
                source_revision="holdings-4",
            ),
        ),
        reconciliation_posture=SourceReconciliationPosture.COMPLETE,
    )
    source = source_ref_payload(
        SourceRef(
            product_id="lotus-core:PortfolioStateSnapshot:v1",
            source_system=SourceSystem.LOTUS_CORE,
            product_version="v1",
            route="/integration/portfolios/{portfolio_id}/core-snapshot",
            as_of_date=date(2026, 6, 21),
            generated_at_utc=datetime(2026, 6, 21, 10, 30, tzinfo=UTC),
            content_hash="sha256:portfolio-state",
            data_quality_status="complete",
            freshness=EvidenceFreshness.CURRENT,
            revision_claims=claims,
        )
    )

    assert source_revision_claims_from_payload(source["revision_claims"]) == claims


def test_unknown_revision_claim_payload_fails_closed_when_claims_are_smuggled() -> None:
    with pytest.raises(ValueError, match="cannot carry owner claim fields"):
        source_revision_claims_from_payload(
            {"claim_posture": "unknown", "snapshot_id": "caller-invented"}
        )
